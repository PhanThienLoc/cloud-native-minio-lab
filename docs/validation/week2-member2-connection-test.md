# Week 2 Member 2 Connection Test

## Phạm vi

Tài liệu này ghi lại kết quả chạy `scripts/connect_test.py` để kiểm thử luồng upload/download qua Nginx Load Balancer và lấy số liệu latency cơ bản làm mốc so sánh cho Tuần 4.

## Môi trường kiểm thử

- Endpoint: `http://localhost:9000`
- Bucket kiểm thử: `demo-bucket`
- File nguồn: `scripts/sample_data/user_data.csv`
- File tải về: `scripts/sample_data/downloads/user_data.csv`
- Cấu hình kết nối lấy từ `.env`

## Lệnh đã chạy

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d
curl.exe -i http://localhost:9000/minio/health/live
python scripts/connect_test.py
```

## Kết quả runtime

Kết quả health check:

```text
HTTP/1.1 200 OK
```

Kết quả chạy script:

```text
[INFO] Cấu hình kết nối:
[INFO]   endpoint_url = http://localhost:9000
[INFO]   bucket       = demo-bucket
[INFO]   source_file  = C:\Users\Admin\Desktop\New folder (9)\cloud-native-minio-lab\scripts\sample_data\user_data.csv
[INFO]   object_name  = user_data.csv
[INFO]   download_path = C:\Users\Admin\Desktop\New folder (9)\cloud-native-minio-lab\scripts\sample_data\downloads\user_data.csv
[INFO] Bucket 'demo-bucket' chưa tồn tại, đang tạo mới...
[SUCCESS] Đã tạo bucket 'demo-bucket'.

--- BẮT ĐẦU UPLOAD: user_data.csv -> s3://demo-bucket/user_data.csv (1.01 MB) ---
[SUCCESS] Upload thành công.
[METRIC] Upload latency: 0.0668 giây

--- BẮT ĐẦU DOWNLOAD: s3://demo-bucket/user_data.csv -> ...\scripts\sample_data\downloads\user_data.csv (1.01 MB) ---
[SUCCESS] Download thành công về: ...\scripts\sample_data\downloads\user_data.csv
[METRIC] Download latency: 0.0235 giây
[VERIFY] Kích thước khớp: 1064178 bytes
```

## Số liệu latency cơ bản

- Upload latency: `0.0668` giây
- Download latency: `0.0235` giây
- Kích thước file: `1064178` bytes

## Kết luận

- Upload PASS.
- Download PASS.
- Kích thước file sau download khớp với file nguồn.
- Script đã ghi nhận được latency cơ bản cho upload/download để dùng làm dữ liệu đối chiếu ở Tuần 4.

## Hạn chế

- Đây là benchmark nền với một file mẫu và một lần chạy.
- Khi so sánh với Tuần 4 cần giữ nguyên endpoint, file nguồn và điều kiện môi trường càng nhiều càng tốt.