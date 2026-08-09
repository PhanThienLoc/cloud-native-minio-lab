# Member 3 – Week 2 Validation

## 1. Kiểm tra MinIO Client

```bash
mc --version
```

Kết quả:

```text
mc version RELEASE.2025-08-13T08-35-41Z (commit-id=7394ce0dd2a80935aded936b09fa12cbb3cb8096)
Runtime: go1.24.6 windows/amd64
Copyright (c) 2015-2025 MinIO, Inc.
License GNU AGPLv3
```

---

## 2. Cấu hình alias

```bash
mc alias list
```

Kết quả:

```text
myminio
URL       : http://localhost:9000
AccessKey : minioadmin
SecretKey : minioadmin123
API       : s3v4
Path      : auto
```

Alias `myminio` đã được cấu hình thành công và kết nối tới MinIO tại `http://localhost:9000`.

---

## 3. Danh sách bucket

```bash
mc ls myminio
```

Kết quả:

```text
[2026-08-09 17:21:00 +07]     0B processed-data/
[2026-08-09 17:20:56 +07]     0B raw-data/
[2026-08-09 17:21:04 +07]     0B system-logs/
```

Đã xác nhận 3 bucket tồn tại:

* `raw-data`
* `processed-data`
* `system-logs`

---

## 4. Kiểm tra versioning

```bash
mc version info myminio/raw-data
```

Kết quả:

```text
myminio/raw-data versioning is enabled
```

Versioning của bucket `raw-data` đã được bật và kiểm tra thành công.

---

## 5. Kiểm tra chạy lại script

```bash
./scripts/mc_setup.sh
./scripts/mc_setup.sh
```

### Lần chạy thứ nhất

Kết quả:

```text
MinIO setup completed successfully!
Buckets:

- raw-data
- processed-data
- system-logs
  Versioning enabled for: raw-data
  =====================================

Available buckets:
[2026-08-09 17:21:00 +07]     0B processed-data/
[2026-08-09 17:20:56 +07]     0B raw-data/
[2026-08-09 17:21:04 +07]     0B system-logs/
```

### Lần chạy thứ hai

Kết quả:

```text
MinIO setup completed successfully!
Buckets:

- raw-data
- processed-data
- system-logs
  Versioning enabled for: raw-data
  =====================================

Available buckets:
[2026-08-09 17:21:00 +07]     0B processed-data/
[2026-08-09 17:20:56 +07]     0B raw-data/
[2026-08-09 17:21:04 +07]     0B system-logs/
```

### Kết luận

Script `mc_setup.sh` đã được chạy thực tế 2 lần liên tiếp. Cả hai lần đều hoàn thành thành công, không phát sinh lỗi và trạng thái cuối vẫn duy trì đầy đủ 3 bucket cùng versioning cho `raw-data`.

Điều này cung cấp bằng chứng runtime cho khả năng chạy lại script (idempotent) trong môi trường lab hiện tại.
