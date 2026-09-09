# ProjectNoiSoi — Matching Progress

## Mục tiêu
Map ảnh nội soi gốc trên Google Drive với đúng PDF bệnh nhân trước khi xây model. Mapping được ưu tiên hoàn tất và kiểm tra trước khi bắt đầu medical report generation.

## Dữ liệu
- 21,257 PDF hồ sơ.
- 81,786 ảnh gốc.
- 8,150 folder/case ảnh.
- 21,241/21,257 PDF đã lấy được ngày từ cấu trúc thư mục.
- 16 PDF không lấy được ngày bằng parser hiện tại.
- 81,784 ảnh gốc có pHash hợp lệ; 2 file có binary không phải JPEG hợp lệ.

## Đã làm
1. Tạo `image_index.csv` cho 81,786 ảnh.
2. Parse datetime/date từ tên ảnh và phân tích cấu trúc folder.
3. Xác định 8,150 folder/case ảnh.
4. Tạo candidate PDF theo ngày: 133,309 case × candidate-PDF pairs cho 8,150 cases; 8,127 cases có candidate PDF và 23 cases không có candidate.
5. Kiểm tra record ID trong text PDF: chưa tìm thấy ID hữu ích trong pilot.
6. Trích xuất embedded images từ toàn bộ 21,257 PDF.
   - 111,476 usable PDF thumbnails.
   - 6 PDF không có usable images.
   - 0 image extraction errors.
   - 0 PDF-level errors.
7. Tính pHash cho toàn bộ 81,786 ảnh gốc.
8. Tính pHash cho 111,476 PDF thumbnails.
9. Matching production hoàn tất cho toàn bộ 8,150 cases.
   - 133,309 matching rows.
   - 133,286 scored candidate-PDF rows.
   - 23 rows tương ứng với 23 cases không có candidate PDF.
10. Visual audit cho các nhóm strong / ambiguous / weak xác nhận:
   - pHash distance = 0 thường là cùng frame.
   - distance khoảng 1–2 vẫn có thể là cùng frame sau resize/compression/rendering.
   - distance cao kết hợp unique-match ratio thấp thường là false nearest-neighbor.
   - candidate gap thấp không tự động có nghĩa mapping sai vì có thể có duplicate/shared images.
11. Xây `best_candidate_per_case.csv` và confidence classification v1.

## Matching results v1
Trong 8,127 cases có candidate PDF:

| Confidence | Cases | Tỷ lệ |
|---|---:|---:|
| HIGH | 7,610 | 93.64% |
| MEDIUM | 394 | 4.85% |
| REVIEW | 123 | 1.51% |

- HIGH + MEDIUM: 8,004 / 8,127 cases (98.49%).
- REVIEW: 123 cases.
- Không được diễn giải các tỷ lệ trên như accuracy; chưa có ground-truth độc lập cho toàn bộ mapping.
- HIGH group có mean pHash distance trung bình 0.247 và median 0; unique-match ratio trung bình 0.993.
- Một số case yếu cho thấy nearest-neighbor có thể vẫn trả về một original dù PDF không thực sự thuộc case đó, vì vậy confidence phải dùng nhiều tín hiệu thay vì chỉ dùng argmin pHash.

## Confidence v1
Rule v1 hiện tại dùng kết hợp:
- `best_mean_distance`
- `best_max_distance`
- `best_unique_match_ratio`
- số lượng thumbnail
- và trạng thái candidate.

HIGH hiện được dùng cho các mapping có mean distance ≤ 2, unique-match ratio ≥ 0.75 và max distance ≤ 6 (hoặc mean distance = 0). MEDIUM là các mapping chưa đạt HIGH nhưng mean distance ≤ 6 và unique-match ratio ≥ 0.50. Các trường hợp còn lại là REVIEW.

Đây là operational confidence, chưa phải calibrated probability hay accuracy estimate.

## Checkpoints / artifacts trên Google Drive
Các artifact dữ liệu và checkpoint không được commit vào repository:
- `image_index.csv`
- `pdf_index.csv`
- `case_candidates.csv`
- `original_image_phash.csv`
- `pdf_thumbnail_phash.csv`
- `matching_results.csv`
- `best_candidate_per_case.csv`
- `final_mapping_v1.csv`
- `boundary_audit/`
- `progress.json`

## Kết luận hiện tại
`date filtering + PDF thumbnail extraction + pHash + multi-signal confidence` là hướng khả thi cho mapping ảnh → hồ sơ. Pipeline đã hoàn thành phần matching production; bước tiếp theo là kiểm soát các mapping REVIEW/MEDIUM và sau đó xây dataset structured từ PDF/report.

Không đưa ảnh/PDF bệnh nhân hoặc checkpoint chứa dữ liệu clinical lên GitHub; dữ liệu tiếp tục nằm trên Google Drive.
