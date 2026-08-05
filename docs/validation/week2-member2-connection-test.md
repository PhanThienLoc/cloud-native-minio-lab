# Kiểm Thử Kết Nối Tuần 2 Của Thành Viên 2

## Phạm Vi

Tài liệu ghi lại quy trình kiểm tra `scripts/connect_test.py`. Script upload và
download một file qua Nginx, đồng thời ghi nhận latency và bằng chứng toàn vẹn
dữ liệu bằng SHA256.

## Kiểm Tra Source

- Script: `scripts/connect_test.py`
- Endpoint: `http://localhost:9000`
- Credential: `.env`, không commit vào Git
- Dữ liệu sinh ra: `scripts/sample_data/`, đã được ignore bởi Git

## Bằng Chứng Sinh Dataset

Lệnh đã chạy:

```powershell
python scripts/generate_data.py --log-size-mb 1 --csv-size-mb 1 --binary-count 1 --binary-size-kb 20
```

Kết quả: exit code `0`.

- `system_logs.log`: `1066621` bytes
- `user_data.csv`: `1064184` bytes
- `dummy_images/image_dummy_1.bin`: `20480` bytes
- File kiểm tra sau download: `1064184` bytes

## Quy Trình Kiểm Thử Có Thể Tái Lập

Chạy từ thư mục gốc repository:

```powershell
Copy-Item .env.example .env
python -m pip install -r scripts/requirements.txt
python scripts/generate_data.py --log-size-mb 1 --csv-size-mb 1 --binary-count 1 --binary-size-kb 20
docker compose --env-file .env -f infra/docker-compose.yml up -d
curl.exe -i http://localhost:9000/minio/health/live
python scripts/connect_test.py --file scripts/sample_data/user_data.csv --bucket demo-bucket
```

Các giá trị trong `.env` phải khớp với credential của cụm MinIO đang chạy.
Script ưu tiên `AWS_ACCESS_KEY_ID` và `AWS_SECRET_ACCESS_KEY`; nếu không có,
script dùng `MINIO_ROOT_USER` và `MINIO_ROOT_PASSWORD` cho lab hiện tại.

## Bằng Chứng Runtime

Trạng thái: `Runtime verified` trên Docker Desktop.

Các lệnh đã chạy:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d --force-recreate nginx
curl.exe -i http://localhost:9000/minio/health/live
python scripts/connect_test.py --file scripts/sample_data/user_data.csv --bucket demo-bucket
```

Kết quả thực tế:

- Health endpoint của Nginx: HTTP `200 OK`
- Tạo bucket: PASS
- Upload: PASS
- Upload latency: `0.0666` giây
- Download: PASS
- Download latency: `0.0218` giây
- Kích thước file nguồn: `1064184` bytes
- Kích thước file download: `1064184` bytes
- SHA256 của file nguồn và file download:
  `1a991f5ce8f8df3657a61ebded83074c4d8f0cf8207dd32275df6767a2c69f20`
- Exit code của script: `0`

Đường dẫn trong lệnh là đường dẫn tương đối; tài liệu không chứa đường dẫn cá
nhân hoặc credential.

## Giới Hạn

- Một file và một lần chạy chỉ là baseline, chưa phải benchmark.
- Không commit dataset hoặc file download.
- Bằng chứng Docker trên một máy không chứng minh hệ thống đã production-ready.
