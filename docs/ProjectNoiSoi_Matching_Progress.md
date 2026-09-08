# ProjectNoiSoi — Matching Progress

## Mục tiêu
Map ảnh nội soi gốc trên Google Drive với đúng PDF bệnh nhân trước khi xây model.

## Dữ liệu
- 21,257 PDF hồ sơ.
- 81,786 ảnh gốc.
- 8,150 folder/case ảnh.
- 21,241/21,257 PDF đã lấy được ngày từ cấu trúc thư mục.
- Còn 16 PDF chưa parse được ngày.

## Đã làm
1. Tạo `image_index.csv` cho 81,786 ảnh.
2. Parse `record_id`, datetime và date từ tên ảnh.
3. Phân tích cấu trúc folder: 8,150 case.
4. Lọc PDF candidate theo ngày.
5. Kiểm tra record ID trong text PDF: chưa tìm thấy ID hữu ích trong pilot.
6. Thử pHash giữa thumbnail trong PDF và ảnh gốc.
7. Visual audit xác nhận:
   - pHash distance = 0 → cùng frame.
   - distance ≈ 2 → vẫn có thể là cùng frame sau resize/compression.
   - distance lớn + margin thấp → có thể là false nearest-neighbor.
8. Pilot: 25 cases, 330 candidate-PDF rows.
   - 24/25 winning candidates có `mean_distance <= 2`.
   - 24/25 có `max_distance <= 2`.
   - Case `10971.10971.0.10986` là outlier rõ ràng và visual audit xác nhận match sai.

## Kết luận
`date filtering + pHash + margin` là hướng khả thi cho bước mapping. Không nên dùng nearest-neighbor một cách mù quáng; case khó phải đưa vào review.

## Bước tiếp theo
Xây production pipeline có checkpoint/resume và cache pHash:
- `pdf_index.csv`
- `case_candidates.csv`
- `original_image_phash.csv`
- `pdf_thumbnail_phash.csv`
- `matching_results.csv`
- `review_cases.csv`
- `progress.json`

Không đưa ảnh/PDF bệnh nhân lên GitHub; dữ liệu tiếp tục nằm trên Google Drive.
