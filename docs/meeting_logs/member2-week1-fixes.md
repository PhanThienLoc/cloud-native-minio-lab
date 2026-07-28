# Member 2 Week 1 Fix Notes

## Mục tiêu sửa
Branch `feat/data-ingestion-pipeline` đã có đúng hướng cho nhiệm vụ tuần 1: tạo script sinh dataset mẫu cho MinIO Lab. Tuy nhiên branch đang commit trực tiếp dữ liệu sinh ra vào Git và thiếu dependency cần thiết để người khác chạy lại script.

## Các lỗi đã sửa

### 1. Không commit dataset sinh sẵn
Trước đó branch thêm toàn bộ `scripts/sample_data/`, gồm nhiều file nhị phân, log và CSV. Đây là output của script, không phải source code.

Đã sửa:
- xóa `scripts/sample_data/` khỏi Git
- thêm `scripts/sample_data/` vào `.gitignore`

Lý do:
- repo nhẹ hơn
- review dễ hơn
- thành viên khác vẫn có thể tự sinh dữ liệu bằng script
- tránh đưa dữ liệu lớn không cần thiết vào lịch sử Git

### 2. Cập nhật dependency thật
`scripts/generate_data.py` dùng `faker` và `tqdm`, nhưng `scripts/requirements.txt` trước đó chỉ có `boto3`.

Đã sửa:
- thêm `faker`
- thêm `tqdm`
- thêm `python-dotenv` theo yêu cầu môi trường tuần 1
- giữ `boto3` để chuẩn bị cho task upload qua S3 API ở tuần sau

### 3. Làm script dễ chạy lại
Script ban đầu sinh dữ liệu với kích thước cố định. Khi cần demo nhanh hoặc test nhẹ, cách này chưa linh hoạt.

Đã sửa:
- thêm tham số dòng lệnh bằng `argparse`
- cho phép đổi output directory
- cho phép đổi kích thước log, CSV, số lượng file binary và kích thước từng file

Ví dụ chạy mặc định:

```bash
python scripts/generate_data.py
```

Ví dụ chạy nhẹ để test nhanh:

```bash
python scripts/generate_data.py --log-size-mb 1 --csv-size-mb 1 --binary-count 5 --binary-size-kb 20
```

## Kết quả sau khi sửa
- Branch giữ lại source code cần thiết.
- Dataset vẫn sinh lại được khi cần.
- Dependency khớp với script.
- Scope tuần 1 rõ hơn: chuẩn bị môi trường Python và dataset generator.

## Ghi chú trước khi merge
Branch này vẫn nên được review qua PR vào `develop`. Nếu muốn chứng minh phần nghiên cứu Erasure Coding/Sharding của Member 2, nên bổ sung thêm một file tài liệu ngắn trong `docs/`.
