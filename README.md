# Ghép ảnh nội soi gốc với hồ sơ PDF

Script [map_images_to_reports.py](scripts/map_images_to_reports.py) ghép ảnh gốc
trong `ImageLocal/ImageLocal` vào PDF tương ứng trong `Hồ sơ bệnh/Hình nội soi
theo ngày`. Hai thư mục nguồn chỉ được đọc, không bị đổi tên, di chuyển hay ghi
thêm file.

Thuật toán dùng ba lớp bằng chứng, theo thứ tự:

1. Lấy ngày từ timestamp/tên ảnh và tên thư mục chứa PDF để chỉ so sánh các hồ sơ cùng ngày.
2. So khớp mã trong tên ảnh với mã xuất hiện trong tên/nội dung PDF (không phân biệt hoa thường và dấu phân cách).
3. Nếu không có mã, trích thumbnail nội soi từ PDF và so pHash với ảnh gốc. pHash chịu được việc PDF dùng bản thu nhỏ hoặc ảnh có độ phân giải khác.

Nếu không có bằng chứng đủ mạnh, ảnh được ghi là `unmatched`, **không** gán bừa vào PDF gần nhất. Những trường hợp có nhiều kết quả ngang nhau hoặc phải dò sang ngày khác được ghi là `review`.

## Chạy local qua Google Drive for desktop (tuỳ chọn)

Cài Google Drive for desktop, đăng nhập, rồi đặt hai thư mục dữ liệu là **Available offline**. Cài các thư viện một lần:

```bash
python3 -m pip install pymupdf imagehash pillow pandas tqdm
```

Mở [image_report_mapping_local.ipynb](image_report_mapping_local.ipynb) trong VS Code và chạy lần lượt các cell. Notebook tự tìm Google Drive trên macOS và dùng đúng hai đường dẫn:

```text
Drive của tôi/ImageLocal/ImageLocal
Drive của tôi/Hồ sơ bệnh/Hình nội soi theo ngày
```

Hoặc chạy trực tiếp từ Terminal (thay `GoogleDrive-.../My Drive` bằng đường dẫn Drive thực tế của máy):

```bash
python3 scripts/map_images_to_reports.py \
  --images "$HOME/Library/CloudStorage/GoogleDrive-.../My Drive/ImageLocal/ImageLocal" \
  --reports "$HOME/Library/CloudStorage/GoogleDrive-.../My Drive/Hồ sơ bệnh/Hình nội soi theo ngày" \
  --output mapping_output
```

## Kết quả

Thư mục output có các CSV sau:

- `image_report_mapping.csv`: toàn bộ kết quả, một dòng cho mỗi ảnh gốc.
- `matched.csv`: ghép chắc chắn; cột `method` cho biết `record_id` hay `phash`.
- `needs_manual_review.csv`: cần kiểm tra, chẳng hạn nhiều PDF cùng điểm hoặc phải fallback sang ngày khác.
- `unmatched.csv`: chưa có đủ bằng chứng để ghép.
- `read_errors.csv`: ảnh/PDF không đọc được để xử lý riêng.

Có thể điều chỉnh `--threshold` (mặc định `10`, trong khoảng 0–64). Giảm ngưỡng nếu thấy ghép nhầm; tăng rất từ từ nếu nhiều ảnh cùng hồ sơ nhưng không nhận ra thumbnail.

## Chạy từ VS Code, không dùng Google Drive for desktop

Script [map_drive_folders.py](scripts/map_drive_folders.py) đọc hai folder trực tiếp
qua Google Drive API. Nó chỉ có quyền đọc Drive, tải các file vào `.drive_cache/`
trong lúc xử lý, và giữ cache để lần chạy sau không phải tải lại file không đổi.

1. Tạo một Google Cloud project, bật **Google Drive API**, cấu hình OAuth consent screen, rồi tạo OAuth client có loại **Desktop app**. Tải JSON client về project này với tên `credentials.json`. Hướng dẫn chính thức của Google: [Python Drive API quickstart](https://developers.google.com/workspace/drive/api/quickstart/python).
2. Cài thư viện:

```bash
python3 -m pip install pymupdf imagehash pillow pandas tqdm google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

3. Chạy từ Terminal tích hợp của VS Code:

```bash
python3 scripts/map_drive_folders.py --output mapping_output
```

Lần đầu, trình duyệt sẽ mở để bạn chọn đúng tài khoản Google và cấp quyền chỉ đọc. Token được lưu cục bộ trong `token.json`; `credentials.json`, `token.json`, cache và CSV output đều đã được bỏ qua bởi Git.
