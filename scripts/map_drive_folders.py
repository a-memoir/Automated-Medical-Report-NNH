"""Run the image/PDF matcher directly against Google Drive, without Drive Desktop.

The program uses the Google Drive API to cache the two requested Drive folders
locally, then runs ``map_images_to_reports.py`` over that cache.
"""
from __future__ import annotations

import argparse
import json
import random
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import google_auth_httplib2
import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from tqdm.auto import tqdm

FOLDER_MIME = "application/vnd.google-apps.folder"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def drive_service(credentials_path: Path, token_path: Path, http_timeout: int) -> Resource:
    """Open browser OAuth on first run and reuse the refresh token later."""
    if not credentials_path.is_file():
        raise SystemExit(f"Không thấy {credentials_path}. Hãy tạo OAuth Desktop credentials rồi tải JSON về tên này.")
    credentials: Credentials | None = None
    if token_path.is_file():
        credentials = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            credentials = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES).run_local_server(port=0)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
    # Drive can take a while to enumerate/download a large medical archive.
    # The default socket timeout is too short for an unstable connection.
    http = google_auth_httplib2.AuthorizedHttp(credentials, http=httplib2.Http(timeout=http_timeout))
    return build("drive", "v3", http=http, cache_discovery=False)


def execute_with_retry(request: Any, operation: str, attempts: int = 6) -> Any:
    """Retry transient Drive/network failures with bounded exponential backoff."""
    retryable_statuses = {408, 429, 500, 502, 503, 504}
    for attempt in range(attempts):
        try:
            return request.execute()
        except HttpError as exc:
            if exc.resp.status not in retryable_statuses or attempt == attempts - 1:
                raise
        except (TimeoutError, socket.timeout, ConnectionError, OSError):
            if attempt == attempts - 1:
                raise
        delay = min(30, 2 ** attempt) + random.uniform(0, 1)
        print(f"{operation} gặp lỗi tạm thời; thử lại sau {delay:.1f}s ({attempt + 1}/{attempts - 1})")
        time.sleep(delay)


def list_children(service: Resource, parent_id: str) -> list[dict[str, Any]]:
    """Get every direct child; Drive returns results in pages."""
    children: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        request = service.files().list(
            q=f"'{parent_id}' in parents and trashed = false", spaces="drive",
            fields="nextPageToken, files(id,name,mimeType,md5Checksum,size,modifiedTime)",
            pageToken=page_token, pageSize=1000, orderBy="folder,name",
        )
        response = execute_with_retry(request, "Đọc danh sách folder Drive")
        children.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return children


def find_child_folder(service: Resource, parent_id: str, name: str) -> str:
    matches = [item for item in list_children(service, parent_id) if item["name"] == name and item["mimeType"] == FOLDER_MIME]
    if len(matches) != 1:
        raise SystemExit(f"Cần đúng một folder '{name}' trong Drive (tìm thấy {len(matches)}).")
    return matches[0]["id"]


def resolve_folder(service: Resource, drive_path: str) -> str:
    """Resolve a path relative to My Drive, e.g. ``ImageLocal/ImageLocal``."""
    folder_id = "root"
    for part in (part for part in drive_path.split("/") if part):
        folder_id = find_child_folder(service, folder_id, part)
    return folder_id


def load_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def download_file(service: Resource, item: dict[str, Any], target: Path, attempts: int = 6) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(attempts):
        try:
            request = service.files().get_media(fileId=item["id"])
            with target.open("wb") as output:
                downloader = MediaIoBaseDownload(output, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            return
        except HttpError as exc:
            if exc.resp.status not in {408, 429, 500, 502, 503, 504} or attempt == attempts - 1:
                raise
        except (TimeoutError, socket.timeout, ConnectionError, OSError):
            if attempt == attempts - 1:
                raise
        delay = min(30, 2 ** attempt) + random.uniform(0, 1)
        print(f"Tải lại {item['name']} sau {delay:.1f}s ({attempt + 1}/{attempts - 1})")
        time.sleep(delay)


def cache_tree(service: Resource, root_id: str, destination: Path, label: str) -> Path:
    """Recursively cache a Drive tree, reusing files with unchanged MD5 hashes."""
    manifest_path = destination / ".drive_manifest.json"
    old_manifest = load_manifest(manifest_path)
    new_manifest: dict[str, dict[str, str]] = {}
    queue: list[tuple[str, Path]] = [(root_id, destination)]
    files: list[tuple[dict[str, Any], Path]] = []
    while queue:
        folder_id, local_dir = queue.pop()
        for item in list_children(service, folder_id):
            local_path = local_dir / item["name"]
            if item["mimeType"] == FOLDER_MIME:
                queue.append((item["id"], local_path))
            else:
                files.append((item, local_path))

    try:
        for index, (item, target) in enumerate(tqdm(files, desc=f"Tải {label}"), start=1):
            fingerprint = item.get("md5Checksum") or item.get("modifiedTime", "")
            cached = old_manifest.get(item["id"], {})
            if not (target.is_file() and cached.get("fingerprint") == fingerprint):
                download_file(service, item, target)
            new_manifest[item["id"]] = {"path": str(target.relative_to(destination)), "fingerprint": fingerprint}
            # Preserve progress without rewriting the manifest for every file.
            if index % 100 == 0:
                manifest_path.parent.mkdir(parents=True, exist_ok=True)
                manifest_path.write_text(json.dumps(new_manifest, ensure_ascii=False), encoding="utf-8")
    finally:
        # An interruption will at worst repeat the last incomplete batch.
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(new_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", default="credentials.json", help="OAuth Desktop-client JSON from Google Cloud")
    parser.add_argument("--token", default="token.json", help="Local OAuth token path")
    parser.add_argument("--images-drive-path", default="ImageLocal/ImageLocal")
    parser.add_argument("--reports-drive-path", default="Hồ sơ bệnh/Hình nội soi theo ngày")
    parser.add_argument("--cache", default=".drive_cache", help="Reusable local download cache")
    parser.add_argument("--output", default="mapping_output", help="Folder for mapping CSVs")
    parser.add_argument("--threshold", type=int, default=10)
    parser.add_argument("--http-timeout", type=int, default=180, help="Seconds before one Drive request times out")
    args = parser.parse_args()

    service = drive_service(Path(args.credentials), Path(args.token), args.http_timeout)
    images_id = resolve_folder(service, args.images_drive_path)
    reports_id = resolve_folder(service, args.reports_drive_path)
    cache = Path(args.cache)
    images = cache_tree(service, images_id, cache / "images", "ảnh gốc")
    reports = cache_tree(service, reports_id, cache / "reports", "hồ sơ PDF")
    matcher = Path(__file__).with_name("map_images_to_reports.py")
    subprocess.run([
        sys.executable, str(matcher), "--images", str(images), "--reports", str(reports),
        "--output", args.output, "--threshold", str(args.threshold),
    ], check=True)


if __name__ == "__main__":
    main()
