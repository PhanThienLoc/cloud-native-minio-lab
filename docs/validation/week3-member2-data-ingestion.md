# Kiểm thử Data Ingestion của Thành viên 2 - Tuần 3

## Phạm vi

Tài liệu này mô tả cách kiểm tra `scripts/data_ingestion.py` sau khi sửa. Pipeline
quét đệ quy dataset cục bộ, upload qua Nginx vào bucket `raw-data`, gắn custom
metadata và tạo object key theo Hive-style partitioning.

## Cấu hình

Tạo `.env` từ file mẫu và thay các placeholder bằng credential của lab:

```powershell
Copy-Item .env.example .env
```

Pipeline ưu tiên `AWS_ACCESS_KEY_ID` và `AWS_SECRET_ACCESS_KEY`. Nếu hai biến này
không có, pipeline dùng `MINIO_ROOT_USER` và `MINIO_ROOT_PASSWORD` làm fallback
cho lab. Không commit `.env` hoặc credential thật.

## Chuẩn bị dataset

```powershell
python scripts/generate_data.py `
  --log-size-mb 1 `
  --csv-size-mb 1 `
  --binary-count 2 `
  --binary-size-kb 20
```

Dataset được tạo trong `scripts/sample_data/` và bị Git ignore.

## Kiểm tra source

Trạng thái: `Source inspected`.

- Endpoint mặc định: `http://localhost:9000`.
- Bucket mặc định: `raw-data`.
- Credential chỉ đọc từ environment.
- Source directory được quét đệ quy.
- Thư mục `downloads` và file ẩn không được ingestion lại.
- Object key có dạng:
  `data_type/year=YYYY/month=MM/day=DD/relative/path/filename.ext`.
- Metadata gồm `source`, `ingested-at`, `data-type` và
  `content-type-detected`.
- Upload và `head_object` dùng tối đa ba lần thử với exponential backoff cho lỗi
  network hoặc S3 5xx.
- Pipeline trả exit code khác `0` nếu preflight hoặc bất kỳ file upload nào thất
  bại.

## Chạy pipeline

Bucket `raw-data` phải tồn tại trước khi chạy. Khởi động hạ tầng và kiểm tra
health endpoint:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d
curl.exe -i http://localhost:9000/minio/health/live
```

Nếu bootstrap của Member 3 chưa được merge, tạo riêng bucket phục vụ kiểm thử:

```powershell
docker run --rm --network minio-net --env-file .env `
  --entrypoint /bin/sh minio/mc:latest `
  -c 'mc alias set myminio http://nginx:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc mb --ignore-existing myminio/raw-data'
```

Pipeline không tự tạo bucket. Quyết định này giữ quyền quản trị bucket ở bước
bootstrap và cho phép application user chỉ nhận quyền cần thiết để đọc/ghi object.

Chạy với ngày cố định để kết quả có thể tái lập:

```powershell
python scripts/data_ingestion.py `
  --source-dir scripts/sample_data `
  --bucket raw-data `
  --partition-date 2026-08-05
```

Dùng object key được in trong log để kiểm tra metadata, ví dụ:

```powershell
mc stat myminio/raw-data/csv/year=2026/month=08/day=05/user_data.csv
```

## Kết quả runtime

Trạng thái: `Runtime verified` ngày 16/08/2026 trên branch
`feat/data-ingestion-pipeline-update`.

Hạ tầng được xác nhận có bốn node MinIO và Nginx ở trạng thái healthy. Endpoint
`http://localhost:9000/minio/health/live` trả về HTTP `200 OK`. Bucket `raw-data`
được tạo qua Nginx bằng MinIO Client trước khi chạy pipeline.

Lệnh kiểm thử:

```powershell
python scripts/data_ingestion.py `
  --source-dir scripts/sample_data `
  --bucket raw-data `
  --partition-date 2026-08-05
```

Kết quả quan sát được:

- Exit code: `0`.
- Upload thành công: `102` file.
- Upload thất bại: `0` file.
- Tổng dữ liệu: `22,242,053` byte.
- Thời gian: `2.8116` giây.
- Throughput quan sát: `7.54 MB/s`.
- Object log: `logs/year=2026/month=08/day=05/system_logs.log`.
- Object CSV: `csv/year=2026/month=08/day=05/user_data.csv`.
- Object binary nằm dưới
  `binary/year=2026/month=08/day=05/dummy_images/`.

Thư mục nguồn đã chứa dataset được tạo từ các lần kiểm thử trước, vì vậy pipeline
quét và upload `102` file thay vì chỉ các file mới của lệnh tạo dataset nhỏ. Đây
là bằng chứng cho chức năng quét đệ quy, không phải kết quả benchmark chuẩn hóa.

Lệnh `mc stat` xác nhận object CSV có kích thước khoảng `1.0 MiB` và chứa các
metadata sau:

- `source`: `sensor-01`;
- `data-type`: `csv`;
- `content-type-detected`: `application/vnd.ms-excel`;
- `ingested-at`: thời điểm upload theo UTC.

Preflight thiếu bucket cũng đã được kiểm tra: `HeadBucket` trả `404` và pipeline
kết thúc với exit code `1` thay vì tiếp tục upload. Khi dừng Nginx, log runtime ghi
nhận hai cảnh báo `Retrying __main__.check_bucket`, tương ứng với việc chuyển sang
lần thử thứ hai và thứ ba. Lần kiểm thử được dừng thủ công bằng `Ctrl+C` trong lần
thử cuối nên không dùng traceback đó làm bằng chứng xử lý lỗi cuối cùng. Sau khi
khởi động lại Nginx, endpoint health trả HTTP `200 OK` và container trở về trạng
thái `healthy`. Việc phục hồi ngay trong lúc một tiến trình ingestion còn chạy chưa
được kiểm thử.

Không dùng số liệu của một lần chạy làm kết quả benchmark Tuần 4.
