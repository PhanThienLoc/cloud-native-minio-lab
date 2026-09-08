# Validation `mc_setup.sh` và checksum

## Phạm vi

`mc_setup.sh` tự cấu hình MinIO Client và tạo ba bucket logic bắt buộc:
`raw-data`, `processed-data`, `system-logs`.

`verify_checksum.py` tải các object tương ứng từ MinIO về rồi so sánh SHA256
với file nguồn. Đây là kiểm thử tự động hóa và toàn vẹn dữ liệu của TV3, không
phải Chaos Engineering.

## Chuẩn bị credential

Chạy từ thư mục gốc repository. Tạo `.env` cục bộ từ `.env.example`, sau đó đặt
credential thật trong `.env`. Không commit hoặc push `.env`.

```powershell
Copy-Item .env.example .env
```

Script ưu tiên `AWS_ACCESS_KEY_ID` và `AWS_SECRET_ACCESS_KEY`; nếu không có,
script dùng `MINIO_ROOT_USER` và `MINIO_ROOT_PASSWORD`. Giá trị `change-me` bị
từ chối.

## Chạy `mc_setup.sh`

Nếu đã cài `mc` và Bash trên máy:

```powershell
& bash scripts/mc_setup.sh
```

Trên Windows chưa có Bash hoặc MinIO Client, chạy qua container:

```powershell
docker run --rm `
  --network minio-net `
  --env-file .env `
  --entrypoint /bin/sh `
  minio/mc:latest `
  -c 'mc alias set myminio http://nginx:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && for b in raw-data processed-data system-logs; do mc mb --ignore-existing "myminio/$b"; done && mc ls myminio'
```

Lệnh trên giữ alias bên trong container tạm và tạo đủ ba bucket một cách
idempotent.

## Kiểm tra checksum

Tạo hoặc dùng một thư mục dataset sạch. Các object trên MinIO phải có cùng
đường dẫn tương đối với file nguồn.

```powershell
python scripts/verify_checksum.py `
  --source-dir scripts/sample_data_validation `
  --bucket raw-data `
  --endpoint-url http://localhost:9000 `
  --prefix validation
```

Ví dụ kết quả thành công:

```text
PASS user_data.csv: <sha256>
SUMMARY checked=1 passed=1 failed=0 integrity=100.00%
Downloaded files were removed after verification.
```

Object tương ứng phải tồn tại, ví dụ
`raw-data/validation/user_data.csv`. Có thể dùng `data_ingestion.py` hoặc
`mc cp` để upload dataset test; không commit dataset vào Git.

## Trạng thái evidence

- `Source inspected`: kiểm tra source và command đã tồn tại.
- `Runtime verified`: command đã chạy, có output và exit code ghi nhận.
- `Not executed`: chưa chạy được do thiếu Docker, `mc`, dependency hoặc credential.

Không dùng kết quả `Source inspected` để kết luận checksum runtime đạt. Kiểm
thử dừng node/recovery, nếu có, phải ghi ở tài liệu Chaos Engineering riêng.
Không đưa credential thật, file download hoặc dataset lớn vào commit.
