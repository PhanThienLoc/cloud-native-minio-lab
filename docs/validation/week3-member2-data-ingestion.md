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

Xóa dataset validation cũ để kết quả không phụ thuộc các lần chạy trước, sau đó
tạo đúng một file log, một file CSV và hai file binary:

```powershell
Remove-Item -Recurse -Force scripts/sample_data_validation `
  -ErrorAction SilentlyContinue

python scripts/generate_data.py `
  --output-dir scripts/sample_data_validation `
  --log-size-mb 1 `
  --csv-size-mb 1 `
  --binary-count 2 `
  --binary-size-kb 20
```

Dataset validation chỉ phục vụ runtime test và phải được xóa sau khi hoàn tất,
không commit vào Git.

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
  --source-dir scripts/sample_data_validation `
  --bucket raw-data `
  --partition-date 2026-08-16
```

Dùng MinIO Client trong container để alias luôn được tạo lại và không phụ thuộc
việc máy local đã cài hoặc cấu hình `mc`:

```powershell
docker run --rm `
  --network minio-net `
  --env-file .env `
  --entrypoint /bin/sh `
  minio/mc:latest `
  -c 'mc alias set myminio http://nginx:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc stat myminio/raw-data/csv/year=2026/month=08/day=16/user_data.csv'
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
  --source-dir scripts/sample_data_validation `
  --bucket raw-data `
  --partition-date 2026-08-16
```

Kết quả quan sát được:

- Exit code: `0`.
- Upload thành công: `4` file.
- Upload thất bại: `0` file.
- Tổng dữ liệu: `2,171,856` byte.
- Thời gian: `0.3827` giây.
- Throughput quan sát: `5.41 MB/s`.
- Object log: `logs/year=2026/month=08/day=16/system_logs.log`.
- Object CSV: `csv/year=2026/month=08/day=16/user_data.csv`.
- Object binary nằm dưới
  `binary/year=2026/month=08/day=16/dummy_images/`.

Lệnh `mc stat` chạy qua container xác nhận object CSV có kích thước khoảng
`1.0 MiB` và chứa các metadata sau:

- `source`: `sensor-01`;
- `data-type`: `csv`;
- `content-type-detected`: `application/vnd.ms-excel`;
- `ingested-at`: thời điểm upload theo UTC.

## Kiểm thử retry exhaust

Nginx được dừng trước khi chạy lại pipeline với cùng dataset validation:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml stop nginx

python scripts/data_ingestion.py `
  --source-dir scripts/sample_data_validation `
  --bucket raw-data `
  --partition-date 2026-08-16

$LASTEXITCODE
```

Kết quả runtime:

- Hai cảnh báo `Retrying __main__.check_bucket` xuất hiện trước lần thử thứ hai và
  thứ ba.
- Sau lần thử thứ ba, pipeline in `Ingestion preflight failed`.
- Exit code: `1`.
- Không có traceback không được xử lý.

Nginx được khởi động lại sau kiểm thử. Endpoint health trả HTTP `200 OK` và
container trở về trạng thái `healthy`:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml start nginx
curl.exe -i http://localhost:9000/minio/health/live
```

Xóa dataset validation cục bộ sau khi thu thập evidence:

```powershell
Remove-Item -Recurse -Force scripts/sample_data_validation
```

Không dùng số liệu của một lần chạy làm kết quả benchmark Tuần 4.
