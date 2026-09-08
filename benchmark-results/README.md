# Benchmark Standalone và Distributed

Tài liệu này điều phối benchmark; Docker Compose tạo topology, còn
`scripts/load_generator.py` chỉ tạo workload và đo kết quả.

## Nguyên tắc so sánh

- Standalone và distributed dùng cùng MinIO image đã pin bằng digest.
- Standalone có tổng giới hạn `4 CPU` và `4 GiB RAM`.
- Bốn node distributed có tổng giới hạn `4 CPU` và `4 GiB RAM`.
- Standalone dùng endpoint `http://localhost:9001`.
- Distributed dùng endpoint Nginx `http://localhost:9000`.
- Mỗi mode phải dùng cùng số object, thread và kích thước object.
- Kết quả chỉ đại diện cho Docker lab trên một máy, không phải production.

Các file trong `benchmark-results/raw/` là evidence cũ trước khi bổ sung
provenance schema v2. Không dùng chúng làm evidence cuối cho source mới.

## Chuẩn bị

Chạy từ thư mục gốc repository:

```powershell
Copy-Item .env.example .env
# Thay các giá trị change-me trong .env bằng credential local của nhóm.

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r scripts\requirements.txt

$EvidenceRoot = Join-Path (Split-Path (Get-Location) -Parent) "minio-benchmark-evidence"
New-Item -ItemType Directory -Force $EvidenceRoot | Out-Null
```

`load_generator.py` ưu tiên cặp `AWS_ACCESS_KEY_ID` và
`AWS_SECRET_ACCESS_KEY`. Nếu không khai báo, cả `MINIO_ROOT_USER` và
`MINIO_ROOT_PASSWORD` phải tồn tại. Script không có credential mặc định.

## Mode Standalone

Khởi động deployment riêng:

```powershell
docker compose --env-file .env -f infra/docker-compose.standalone.yml config --quiet
docker compose --env-file .env -f infra/docker-compose.standalone.yml up -d
docker compose --env-file .env -f infra/docker-compose.standalone.yml ps
curl.exe -i http://localhost:9001/minio/health/live
```

Tạo bucket bằng MinIO Client container:

```powershell
docker run --rm `
  --network minio-standalone-net `
  --env-file .env `
  --entrypoint /bin/sh `
  minio/mc:latest `
  -c 'mc alias set standalone http://minio-standalone:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc mb --ignore-existing standalone/benchmark-bucket'
```

Smoke test trước, sau đó mới chạy ba lần workload chính:

```powershell
python scripts/load_generator.py --num-files 100 --threads 8 --file-size 1MB --mode standalone --output "$EvidenceRoot\standalone_smoke"

python scripts/load_generator.py --num-files 5000 --threads 8 --file-size 1MB --mode standalone --output "$EvidenceRoot\standalone_run1"
python scripts/load_generator.py --num-files 5000 --threads 8 --file-size 1MB --mode standalone --output "$EvidenceRoot\standalone_run2"
python scripts/load_generator.py --num-files 5000 --threads 8 --file-size 1MB --mode standalone --output "$EvidenceRoot\standalone_run3"
```

Dừng an toàn và giữ volume:

```powershell
docker compose --env-file .env -f infra/docker-compose.standalone.yml down
```

## Mode Distributed

Khởi động frozen distributed baseline:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml config --quiet
docker compose --env-file .env -f infra/docker-compose.yml up -d
docker compose --env-file .env -f infra/docker-compose.yml ps
curl.exe -i http://localhost:9000/minio/health/live
```

Tạo bucket qua Nginx:

```powershell
docker run --rm `
  --network minio-net `
  --env-file .env `
  --entrypoint /bin/sh `
  minio/mc:latest `
  -c 'mc alias set distributed http://nginx:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc mb --ignore-existing distributed/benchmark-bucket'
```

Smoke test và ba lần workload chính:

```powershell
python scripts/load_generator.py --num-files 100 --threads 8 --file-size 1MB --mode distributed --output "$EvidenceRoot\distributed_smoke"

python scripts/load_generator.py --num-files 5000 --threads 8 --file-size 1MB --mode distributed --output "$EvidenceRoot\distributed_run1"
python scripts/load_generator.py --num-files 5000 --threads 8 --file-size 1MB --mode distributed --output "$EvidenceRoot\distributed_run2"
python scripts/load_generator.py --num-files 5000 --threads 8 --file-size 1MB --mode distributed --output "$EvidenceRoot\distributed_run3"
```

Không dùng `docker compose down -v`, vì tùy chọn `-v` xóa named volume.

## Điều kiện evidence chính thức

Trước khi chạy workload chính:

```powershell
git status --short
git rev-parse HEAD
```

`git status --short` phải không có output. Mỗi JSON schema v2 phải ghi:

- mode và endpoint đúng;
- branch, commit và `working_tree_dirty=false`;
- CPU, RAM và disk context của host;
- MinIO image, Compose file và tổng resource limit;
- workload, throughput, latency, retry và failure.

Chỉ đưa evidence vào repository sau khi cả sáu lần chạy hoàn tất và được review.
