"""Match original endoscopy images to the PDF report containing its thumbnail.

Source folders are read only. Results are written as CSVs to ``--output``.
"""
from __future__ import annotations

import argparse
import io
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import imagehash
import pandas as pd
from PIL import Image, UnidentifiedImageError
from tqdm.auto import tqdm

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
DATE_PATTERNS = (
    re.compile(r"(?<!\d)(20\d{2})[._/-]?(\d{2})[._/-]?(\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(\d{2})[._/-](\d{2})[._/-](20\d{2})(?!\d)"),
)
TIMESTAMP = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})\d{6,}(?!\d)")


@dataclass(frozen=True)
class ImageItem:
    path: Path
    record_id: str
    date: str | None
    phash: imagehash.ImageHash


@dataclass(frozen=True)
class ReportItem:
    path: Path
    date: str | None
    hashes: list[imagehash.ImageHash]
    searchable_text: str


def date_from_text(text: str) -> str | None:
    """Return YYYY-MM-DD from common Vietnamese folder/file date formats."""
    for index, pattern in enumerate(DATE_PATTERNS):
        match = pattern.search(text)
        if match:
            parts = match.groups()
            year, month, day = parts if index == 0 else (parts[2], parts[1], parts[0])
            try:
                return pd.Timestamp(f"{year}-{month}-{day}").strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def date_from_path(path: Path) -> str | None:
    """Search closest folder first; a report date normally is a folder name."""
    # The filename often contains an unrelated export timestamp.  The user
    # supplied date is the name of the folder that contains the report.
    parts = path.parts if path.is_dir() else path.parent.parts
    for part in reversed(parts):
        if found := date_from_text(part):
            return found
    return None


def image_date_and_record_id(path: Path) -> tuple[str | None, str]:
    """Split ``record-id_YYYYMMDDhhmmss.jpg`` while retaining other names."""
    timestamp = TIMESTAMP.search(path.stem)
    if timestamp:
        date = f"{timestamp.group(1)}-{timestamp.group(2)}-{timestamp.group(3)}"
        record_id = path.stem[: timestamp.start()].rstrip("._- ")
    else:
        date, record_id = date_from_path(path), path.stem
    return date, record_id


def normalise_id(value: str) -> str:
    """Compare identifiers independent of punctuation and letter case."""
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def has_exact_record_id(record_id: str, text: str) -> bool:
    """Find an ID, not a substring such as 123 inside 12345."""
    identifier = normalise_id(record_id)
    # Short values are usually image sequence numbers rather than patient IDs.
    if len(identifier) < 5:
        return False
    # Allow common separators to differ (``BN-123`` versus ``BN 123``), while
    # keeping boundaries so a shorter ID cannot match inside another ID.
    separated = r"[^A-Z0-9]*".join(map(re.escape, identifier))
    return bool(re.search(rf"(?<![A-Z0-9]){separated}(?![A-Z0-9])", text.upper()))


def load_hash(path: Path) -> imagehash.ImageHash:
    with Image.open(path) as image:
        return imagehash.phash(image.convert("RGB"))


def extract_pdf_hashes_and_text(pdf_path: Path) -> tuple[list[imagehash.ImageHash], str]:
    """Extract usable embedded images and selectable PDF text exactly once."""
    hashes: list[imagehash.ImageHash] = []
    document = fitz.open(pdf_path)
    try:
        text = "\n".join(page.get_text() for page in document)
        seen_xrefs: set[int] = set()
        for page in document:
            for item in page.get_images(full=True):
                xref = item[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                try:
                    payload = document.extract_image(xref)["image"]
                    with Image.open(io.BytesIO(payload)) as image:
                        # Ignore logos, QR codes and tiny decorative assets.
                        if image.width >= 120 and image.height >= 90:
                            hashes.append(imagehash.phash(image.convert("RGB")))
                except (UnidentifiedImageError, ValueError, KeyError):
                    continue
    finally:
        document.close()
    return hashes, text


def visual_score(image_hashes: list[imagehash.ImageHash], pdf_hashes: list[imagehash.ImageHash], threshold: int) -> tuple[int, float]:
    """Return close-thumbnail count and median nearest pHash distance."""
    if not image_hashes or not pdf_hashes:
        return 0, float("inf")
    nearest = [min(source - thumbnail for thumbnail in pdf_hashes) for source in image_hashes]
    close = [distance for distance in nearest if distance <= threshold]
    return len(close), float(pd.Series(close if close else nearest).median())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", required=True, help="Root: ImageLocal/ImageLocal")
    parser.add_argument("--reports", required=True, help="Root: Hồ sơ bệnh/Hình nội soi theo ngày")
    parser.add_argument("--output", default="mapping_output", help="Folder for result CSVs")
    parser.add_argument("--threshold", type=int, default=10, help="Maximum pHash distance, 0–64 (default 10)")
    args = parser.parse_args()
    if not 0 <= args.threshold <= 64:
        raise SystemExit("--threshold phải nằm trong khoảng 0 đến 64.")

    images_root, reports_root, output = Path(args.images), Path(args.reports), Path(args.output)
    if not images_root.is_dir() or not reports_root.is_dir():
        raise SystemExit("Không tìm thấy thư mục ảnh hoặc hồ sơ. Hãy kiểm tra lại đường dẫn Drive.")
    output.mkdir(parents=True, exist_ok=True)
    image_files = [path for path in images_root.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS]
    pdf_files = list(reports_root.rglob("*.pdf"))
    if not image_files or not pdf_files:
        raise SystemExit("Không tìm thấy ảnh hoặc PDF trong hai thư mục đã chọn.")

    # Same patient can return on another day, so date is part of the group key.
    grouped_images: dict[tuple[str, str | None], list[ImageItem]] = defaultdict(list)
    errors: list[dict[str, str]] = []
    for path in tqdm(image_files, desc="Hash ảnh gốc"):
        try:
            date, record_id = image_date_and_record_id(path)
            grouped_images[(record_id, date)].append(ImageItem(path, record_id, date, load_hash(path)))
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})

    reports_by_date: dict[str | None, list[ReportItem]] = defaultdict(list)
    for path in tqdm(pdf_files, desc="Đọc thumbnail và text trong PDF"):
        try:
            hashes, pdf_text = extract_pdf_hashes_and_text(path)
            searchable = f"{path.stem}\n{pdf_text}"
            report = ReportItem(path, date_from_path(path), hashes, searchable)
            reports_by_date[report.date].append(report)
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})
    all_reports = [report for reports in reports_by_date.values() for report in reports]

    rows: list[dict[str, object]] = []
    for (record_id, date), items in tqdm(grouped_images.items(), desc="Ghép vào hồ sơ"):
        candidates = reports_by_date.get(date, []) if date else all_reports
        used_date_fallback = bool(date and not candidates)
        if used_date_fallback:
            candidates = all_reports

        scored = []
        for report in candidates:
            direct_id = has_exact_record_id(record_id, report.searchable_text)
            count, median = visual_score([item.phash for item in items], report.hashes, args.threshold)
            scored.append((report, direct_id, count, median))
        scored.sort(key=lambda item: (item[1], item[2], -item[3]), reverse=True)
        best = scored[0] if scored else None
        tied = bool(best and len(scored) > 1 and best[1:] == scored[1][1:])

        if best is None:
            report, direct_id, count, median = None, False, 0, float("inf")
            status, method = "unmatched", "none"
        else:
            report, direct_id, count, median = best
            if direct_id:
                status, method = ("review", "record_id_ambiguous") if tied else ("matched", "record_id")
            elif count and median <= args.threshold:
                status, method = ("review", "phash_ambiguous") if tied else ("matched", "phash")
            else:
                status, method = "unmatched", "none"
            if used_date_fallback and status == "matched":
                status, method = "review", f"{method}_date_fallback"

        for image in items:
            rows.append({
                "record_id": record_id, "image_path": str(image.path), "image_date": image.date,
                "pdf_path": str(report.path) if report and status != "unmatched" else "",
                "pdf_date": report.date if report and status != "unmatched" else "",
                "method": method, "thumbnail_matches": count,
                "median_phash_distance": median if median != float("inf") else "",
                "candidate_count": len(candidates), "status": status,
            })

    columns = ["record_id", "image_path", "image_date", "pdf_path", "pdf_date", "method", "thumbnail_matches", "median_phash_distance", "candidate_count", "status"]
    mapping = pd.DataFrame(rows, columns=columns)
    mapping.to_csv(output / "image_report_mapping.csv", index=False)
    mapping[mapping.status == "matched"].to_csv(output / "matched.csv", index=False)
    mapping[mapping.status == "review"].to_csv(output / "needs_manual_review.csv", index=False)
    mapping[mapping.status == "unmatched"].to_csv(output / "unmatched.csv", index=False)
    pd.DataFrame(errors, columns=["path", "error"]).to_csv(output / "read_errors.csv", index=False)
    print(f"Đã tạo: {output / 'image_report_mapping.csv'}")
    print(mapping.status.value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
