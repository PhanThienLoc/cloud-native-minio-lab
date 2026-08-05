# Ghi Chú Sửa Lỗi Thành Viên 2 Tuần 2

## Phạm Vi Review

- Branch: `feature/week2-member2`
- Người phụ trách: Thành viên 2, Data và Backend Engineer
- Flow review: `reviewer` sau đó `project-validation`
- Trong phiên sửa này chưa commit, push hoặc merge.

## Các Lỗi Đã Phát Hiện

1. `connect_test.py` dùng `minioadmin` làm credential fallback hardcode.
2. Script không ánh xạ đúng tên biến credential của Compose.
3. `list_buckets()` yêu cầu quyền rộng hơn phạm vi kiểm thử.
4. Tài liệu validation chứa đường dẫn Windows cá nhân và latency chưa xác minh.
5. Validation chỉ kiểm tra kích thước, chưa kiểm tra checksum nội dung.
6. `generate_data.py` có các comment hướng dẫn chạy không thuộc task hiện tại.
7. Chương 1 có lỗi format khiến `git diff --check` báo dòng trắng cuối file.

## Các Thay Đổi Đã Thực Hiện

- Credential hiện được đọc từ biến môi trường, không có secret cụ thể trong code.
- Credential ứng dụng được ưu tiên; credential root của lab hiện tại là fallback
  rõ ràng.
- Nếu không có credential, script trả về lỗi cụ thể.
- Đã xóa lời gọi `list_buckets()` không cần thiết.
- Đã tính SHA256 cho file nguồn và file download, sau đó so sánh hai giá trị.
- `.env.example` chỉ chứa placeholder, không chứa secret thật.
- Tài liệu validation dùng đường dẫn tương đối và tách source inspection khỏi
  runtime evidence.
- Đã xóa comment thừa trong `generate_data.py`.
- Đã sửa lỗi dòng trắng cuối file Chương 1.

## Cách Ánh Xạ Credential

1. `AWS_ACCESS_KEY_ID` và `AWS_SECRET_ACCESS_KEY` dành cho application user có
   quyền tối thiểu trong tương lai.
2. `MINIO_ROOT_USER` và `MINIO_ROOT_PASSWORD` dùng cho lab hiện tại.

File `.env` thật tiếp tục bị ignore. Chỉ `.env.example` được phép đưa vào Git.

## Ghi Chú Để Thành Viên 2 Thuyết Trình

- Client kết nối tới Nginx, không kết nối trực tiếp tới một node MinIO.
- S3 client dùng path-style addressing cho endpoint Nginx trong lab.
- Bucket chỉ được tạo khi bucket được yêu cầu chưa tồn tại.
- `time.perf_counter()` dùng để đo latency upload và download.
- Kiểm tra kích thước xác nhận số byte truyền tải; SHA256 xác nhận nội dung
  thực tế giống nhau.
- Dataset và file download là artifact sinh ra trong lúc chạy, nên tiếp tục bị
  ignore và không commit.

## Trạng Thái Validation

- `Source inspected`: đã kiểm tra flow credential, upload/download và checksum.
- `Source inspected`: `.env` bị ignore và dataset không được Git track.
- `Runtime verified`: sinh dataset với exit code `0`.
- `Runtime verified`: health endpoint của Nginx trả về HTTP `200 OK`.
- `Runtime verified`: upload/download qua Nginx thành công.
- `Runtime verified`: kích thước file nguồn và file download đều là `1064184`
  bytes.
- `Runtime verified`: SHA256 khớp:
  `1a991f5ce8f8df3657a61ebded83074c4d8f0cf8207dd32275df6767a2c69f20`.
- `Runtime verified`: upload latency `0.0666` giây và download latency `0.0218`
  giây.
- `Not executed`: chưa chạy benchmark nhiều lần hoặc failure test trong phạm
  vi evidence của connect test này.

## Fix Bổ Sung: Mất Kết Nối Nginx

Review bổ sung phát hiện `get_s3_client()` chỉ khởi tạo boto3 client, chưa gửi
request tới Nginx. Request đầu tiên thực sự xảy ra ở `head_bucket()` trong
`ensure_bucket_exists()`.

Trước khi sửa, `ensure_bucket_exists()` nằm ngoài `try` của `upload_file()`. Nếu
Nginx tắt, `EndpointConnectionError` có thể thoát ra ngoài và in traceback.

Đã sửa:

- Đưa `get_s3_client()` và `ensure_bucket_exists()` vào cùng khối `try` của
  `upload_file()`.
- Bắt `BotoCoreError`, `ClientError`, `EndpointConnectionError` và
  `RuntimeError`.
- Khi không kết nối được, script trả về `False` và in:
  `[ERROR] Upload failed: ...`.
- Đưa khởi tạo client của `download_file()` vào khối `try` tương tự để xử lý
  lỗi nhất quán.

Test lỗi cần chạy sau khi bật môi trường:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml stop nginx
python scripts/connect_test.py --file scripts/sample_data/user_data.csv --bucket demo-bucket
docker compose --env-file .env -f infra/docker-compose.yml start nginx
```

Kết quả mong đợi là script trả exit code `1` và in thông báo lỗi rõ ràng,
không in traceback. Không tuyên bố test này là `Runtime verified` cho đến khi
đã chạy thật.

## Lệnh Cần Chạy Sau Khi Chuẩn Bị Môi Trường

```powershell
git diff --check
python -m py_compile scripts/connect_test.py
python scripts/connect_test.py --help
python scripts/generate_data.py --log-size-mb 1 --csv-size-mb 1 --binary-count 1 --binary-size-kb 20
python scripts/connect_test.py --file scripts/sample_data/user_data.csv --bucket demo-bucket
```

Hãy ghi exit code, latency, kích thước và SHA256 thực tế vào tài liệu
validation. Không ghi kết quả nếu chưa quan sát được từ lần chạy thật.
