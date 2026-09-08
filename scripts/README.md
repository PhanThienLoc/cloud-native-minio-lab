# Hướng dẫn chạy các script benchmark

Chạy tất cả lệnh từ thư mục gốc repository:

```powershell
Set-Location <REPO_ROOT>
```

## 1. Chuẩn bị môi trường

Tạo môi trường ảo và cài dependency:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r scripts\requirements.txt
```

Kiểm tra dependency chính:

```powershell
python -c "import boto3, dotenv; print('Python environment is ready')"
```

Tạo file cấu hình local:

```powershell
Copy-Item .env.example .env
```

Mở `.env` và thay credential mẫu bằng credential local thật:

```dotenv
MINIO_ROOT_USER=<LOCAL_USER>
MINIO_ROOT_PASSWORD=<LOCAL_PASSWORD>
```

Không commit hoặc push `.env`.

## 2. Khởi động Distributed MinIO

Kiểm tra cấu hình:

```powershell
docker compose --env-file .env `
  -f infra/docker-compose.yml `
  config --quiet
```

Khởi động cụm:

```powershell
docker compose --env-file .env `
  -f infra/docker-compose.yml `
  up -d
```

Kiểm tra container:

```powershell
docker compose --env-file .env `
  -f infra/docker-compose.yml `
  ps
```

Kiểm tra endpoint:

```powershell
curl.exe -i http://localhost:9000/minio/health/live
```

Endpoint benchmark distributed:

```text
http://localhost:9000
```

Tạo bucket benchmark:

```powershell
docker run --rm `
  --network minio-net `
  --env-file .env `
  --entrypoint /bin/sh `
  minio/mc:latest `
  -c 'mc alias set distributed http://nginx:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc mb --ignore-existing distributed/benchmark-bucket'
```

## 3. Khởi động Standalone MinIO

Standalone dùng Compose riêng, không dùng lệnh `docker run` thủ công:

```powershell
docker compose --env-file .env `
  -f infra/docker-compose.standalone.yml `
  config --quiet

docker compose --env-file .env `
  -f infra/docker-compose.standalone.yml `
  up -d

docker compose --env-file .env `
  -f infra/docker-compose.standalone.yml `
  ps
```

Kiểm tra endpoint:

```powershell
curl.exe -i http://localhost:9001/minio/health/live
```

Endpoint benchmark standalone:

```text
http://localhost:9001
```

Tạo bucket benchmark:

```powershell
docker run --rm `
  --network minio-standalone-net `
  --env-file .env `
  --entrypoint /bin/sh `
  minio/mc:latest `
  -c 'mc alias set standalone http://minio-standalone:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc mb --ignore-existing standalone/benchmark-bucket'
```

## 4. Chạy benchmark

Chạy smoke test trước:

```powershell
$EvidenceRoot = Join-Path (Split-Path (Get-Location) -Parent) "minio-benchmark-evidence"
New-Item -ItemType Directory -Force $EvidenceRoot | Out-Null
```

### Distributed smoke test

```powershell
python scripts/load_generator.py `
  --num-files 100 `
  --threads 8 `
  --file-size 1MB `
  --mode distributed `
  --output "$EvidenceRoot\distributed_smoke"
```

### Standalone smoke test

```powershell
python scripts/load_generator.py `
  --num-files 100 `
  --threads 8 `
  --file-size 1MB `
  --mode standalone `
  --output "$EvidenceRoot\standalone_smoke"
```

Chỉ chạy workload 5.000 object sau khi smoke test có:

```text
Success: 100
Failure: 0
```

### Distributed workload chính

```powershell
python scripts/load_generator.py `
  --num-files 5000 `
  --threads 8 `
  --file-size 1MB `
  --mode distributed `
  --output "$EvidenceRoot\distributed_run1"
```

### Standalone workload chính

```powershell
python scripts/load_generator.py `
  --num-files 5000 `
  --threads 8 `
  --file-size 1MB `
  --mode standalone `
  --output "$EvidenceRoot\standalone_run1"
```

Mỗi mode nên chạy ba lần:

```text
run1
run2
run3
```

Kết quả JSON và CSV nên lưu ngoài repository để provenance ghi:

```text
working_tree_dirty=false
```

## 5. Kết quả benchmark

Mỗi kết quả cần ghi:

- Mode: `standalone` hoặc `distributed`.
- Endpoint.
- Số object.
- Kích thước object.
- Số thread.
- Total duration.
- Throughput.
- Average latency.
- P95/P99 latency.
- Success/failure.
- Git branch và commit.
- CPU/RAM host.
- MinIO image và resource limit.

Các kết quả đã được review có thể lưu tại:

```text
benchmark-results/raw/
docs/reports/
```

Không lưu CSV/JSON benchmark sinh tự động trong `scripts/`.

## 6. Tắt dịch vụ

Tắt standalone nhưng giữ volume:

```powershell
docker compose --env-file .env `
  -f infra/docker-compose.standalone.yml `
  down
```

Tắt distributed nhưng giữ volume:

```powershell
docker compose --env-file .env `
  -f infra/docker-compose.yml `
  down
```

Không dùng:

```powershell
docker compose down -v
```

vì `-v` sẽ xóa volume dữ liệu MinIO, Prometheus và Grafana.

## 7. Theo dõi tài nguyên

Trong lúc chạy benchmark, mở terminal khác:

```powershell
docker stats
```

Theo dõi:

- CPU.
- Memory.
- Network I/O.
- Block I/O.
- Số process.

Không kết luận benchmark production chỉ từ kết quả Docker trên một máy.

## 8. Lưu ý bảo mật

Không hardcode credential trong:

- Script Python.
- Script Bash.
- README.
- Compose.
- Tài liệu validation.

Credential phải lấy từ:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

hoặc:

```text
MINIO_ROOT_USER
MINIO_ROOT_PASSWORD
```

Không commit:

```text
.env
dataset
file download
benchmark output chưa review
```

## 9. Trạng thái kiểm thử

Dùng các nhãn sau trong tài liệu:

- `Source inspected`: chỉ mới kiểm tra source.
- `Runtime verified`: đã chạy command và có output thực tế.
- `Not executed`: chưa chạy được.
- `Not verified`: chưa đủ bằng chứng.
- `Planned`: dự kiến thực hiện sau.
