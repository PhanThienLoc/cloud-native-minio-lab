# Validation Chaos cơ bản và Resilience

## Phạm vi

Tài liệu ghi nhận ba kiểm thử cơ bản trên distributed MinIO qua Nginx:

1. Dừng một node MinIO trong khi hệ thống đang chạy.
2. Gửi request bằng credential không hợp lệ.
3. Chạy tải smoke test và quan sát kết quả.

Đây là bằng chứng lab trên một máy Docker, không phải bằng chứng về failure
domain độc lập hoặc production high availability.

## 1. Dừng một node

### Command

```powershell
docker compose --env-file .env -f infra/docker-compose.yml stop minio3
```

Khi `minio3` offline, `mc admin info` ghi nhận:

```text
Network: 3/4 OK
minio3: Uptime: offline
Drives: 0/2 OK
1 node offline, 6 drives online, 2 drives offline, EC:4
```

Trong trạng thái này, upload test qua Nginx thành công:

```text
/work/.chaos-test.txt -> myminio/raw-data/.chaos-test.txt
Total: 12 B
```

Khởi động lại node:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml start minio3
```

### Kết luận

- `Runtime verified`: hệ thống vẫn nhận upload khi một node offline.
- `Runtime verified`: lệnh start lại `minio3` đã thực thi thành công.
- `Not verified`: chưa có output `mc admin info` sau recovery để xác nhận lại
  `Network: 4/4 OK` và thời gian healing.
- Không kết luận rằng hệ thống chịu được mọi lỗi node hoặc có HA production.

## 2. Credential không hợp lệ

### Command

Request dùng access key và secret key giả:

```powershell
docker run --rm `
  --network minio-net `
  --entrypoint /bin/sh `
  minio/mc:latest `
  -c 'mc alias set bad http://nginx:9000 wrong-user wrong-password && mc ls bad/raw-data'
```

### Kết quả

```text
Unable to initialize new alias from the provided credentials.
The Access Key Id you provided does not exist in our records.
```

`Runtime verified`: request bị từ chối trước khi có thể đọc bucket. Đây là
security negative test, không phải chaos failure injection.

## 3. Tải smoke test

### Command

```powershell
python scripts/load_generator.py `
  --num-files 100 `
  --threads 8 `
  --file-size 1MB `
  --mode distributed `
  --output "$env:TEMP\minio-load-smoke"
```

### Kết quả

```text
Success        : 100 (100.00%)
Failure        : 0 (0.00%)
Duration       : 1.1632 seconds
Throughput     : 85.9687 MiB/s
Average Latency: 88.8549 ms
P95 / P99      : 126.6617 / 137.9133 ms
```

JSON và CSV được lưu ngoài repository trong thư mục Temp. `Runtime verified`:
smoke workload 100 object hoàn tất không lỗi.

## Tóm tắt trạng thái

| Scenario | Trạng thái | Bằng chứng |
|---|---|---|
| Một node offline | Đạt một phần | Upload thành công; recovery chưa xác nhận lại bằng `mc admin info` |
| Credential sai | Đạt | Request bị MinIO từ chối |
| Tải smoke | Đạt | 100/100, failure 0 |

Không commit file test, dataset, credential hoặc output benchmark trong thư mục
Temp vào repository.
