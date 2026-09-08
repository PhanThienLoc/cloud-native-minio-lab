# Demo Flow: Cloud-Native MinIO Lab

Tài liệu này là kịch bản demo ngắn cho stack MinIO distributed. Chạy các
lệnh từ thư mục gốc repository trong PowerShell. Nó điều phối demo, không
thay thế các tài liệu validation hoặc benchmark chi tiết.

## 1. Mục tiêu demo

Demo chứng minh các điểm sau:

- Cụm MinIO distributed gồm 4 node và 8 drive hoạt động qua Nginx.
- Prometheus scrape metric và Grafana hiển thị dashboard.
- Load generator upload đồng thời qua endpoint distributed.
- Credential sai bị từ chối.
- Một node có thể offline; sau khi start lại, cụm có thể quay về `4/4 OK`.

Không trình bày benchmark cũ như evidence của commit hiện tại nếu chưa chạy
lại benchmark theo [benchmark-results/README.md](../benchmark-results/README.md).

## 2. Chuẩn bị

Kiểm tra branch và môi trường. Không in hoặc commit nội dung `.env`.

```powershell
git status
docker compose --env-file .env -f infra/docker-compose.yml config --quiet
```

Nếu container standalone đang chạy, dừng nó trước khi demo distributed. Cả
standalone và `minio1` đều dùng host port `9001`, nên không thể chạy đồng thời.

```powershell
docker ps --filter "name=infra-minio-standalone-1"
docker stop infra-minio-standalone-1
```

Nếu lệnh `docker ps` không trả về container nào, bỏ qua lệnh `docker stop`.
Không dùng `docker compose down -v` hoặc `--remove-orphans` trong demo vì có
thể xóa dữ liệu hoặc dừng container thuộc topology còn lại.

## 3. Khởi động và kiểm tra cụm

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d
docker compose --env-file .env -f infra/docker-compose.yml ps
curl.exe -i http://localhost:9000/minio/health/ready
```

Kết quả mong đợi: 4 MinIO node, Nginx, Prometheus và Grafana có trạng thái
`healthy`; health endpoint trả `HTTP/1.1 200 OK`.

Kiểm tra trạng thái distributed bằng MinIO Client container:

```powershell
docker run --rm `
  --network minio-net `
  --env-file .env `
  --entrypoint /bin/sh `
  minio/mc:latest `
  -c 'mc alias set myminio http://nginx:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc admin info myminio'
```

Kết quả mong đợi: mỗi node có `Network: 4/4 OK`, `Drives: 2/2 OK`; phần tổng
kết có `8 drives online` và `EC:4`.

## 4. Quan sát monitoring

Mở các giao diện:

```powershell
Start-Process http://localhost:9090/targets
Start-Process http://localhost:3000
```

Trong Prometheus, các target MinIO của job `minio-cluster`, `minio-node` và
`minio-api` cần là `UP`. Tại trang Graph, chạy truy vấn:

```promql
up{job=~"minio-cluster|minio-node|minio-api"}
```

Giá trị `1` nghĩa là Prometheus scrape target thành công. Trong Grafana, đăng
nhập bằng credential Grafana trong `.env`, sau đó mở dashboard **MinIO Cluster
Overview** và chọn time range **Last 15 minutes**.

## 5. Tạo bucket benchmark và chạy smoke load

Tạo bucket theo cách idempotent:

```powershell
docker run --rm `
  --network minio-net `
  --env-file .env `
  --entrypoint /bin/sh `
  minio/mc:latest `
  -c 'mc alias set myminio http://nginx:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc mb --ignore-existing myminio/benchmark-bucket && mc ls myminio'
```

Chạy smoke test. JSON và CSV được lưu ngoài repository để không làm working
tree dirty.

```powershell
python scripts/load_generator.py `
  --num-files 100 `
  --threads 8 `
  --file-size 1MB `
  --mode distributed `
  --output "$env:TEMP\minio-demo-smoke"
```

Kết quả mong đợi: `Success: 100 (100.00%)`, `Failure: 0`, cùng duration,
throughput, average latency, P95 và P99. Refresh Grafana sau khi chạy để thấy
metric request và throughput.

## 6. Security và resilience (tùy thời gian)

### Credential sai

```powershell
docker run --rm `
  --network minio-net `
  --entrypoint /bin/sh `
  minio/mc:latest `
  -c 'mc alias set bad http://nginx:9000 wrong-user wrong-password && mc ls bad/raw-data'
```

Kết quả mong đợi: request bị từ chối với lỗi access key không tồn tại. Đây là
negative test, không phải lỗi hệ thống.

### Một node offline

Chỉ chạy phần này khi cần demo chaos live. Không dùng `rm -f`.

```powershell
docker compose --env-file .env -f infra/docker-compose.yml stop minio3
# Chạy lại lệnh mc admin info ở phần 3; kết quả phải thể hiện 3/4 node online.

docker compose --env-file .env -f infra/docker-compose.yml start minio3
Start-Sleep -Seconds 15
# Chạy lại lệnh mc admin info ở phần 3; kết quả cần quay về 4/4 OK.
```

Sau live chaos, không kết luận production high availability: bốn node hiện
chạy trên cùng Docker host nên không phải các failure domain độc lập.

## 7. Kết thúc demo

Thông điệp kết luận:

> Client upload qua Nginx vào cụm MinIO 4 node. Prometheus thu metric từ MinIO
> và Grafana trực quan hóa trạng thái. Smoke test xác nhận upload đồng thời,
> credential sai bị chặn, và thử nghiệm một node offline cho thấy cụm có thể
> tiếp tục hoạt động trong giới hạn EC:4 của lab.

Tài liệu liên quan:

- [Project runbook](project-runbook.md): cài đặt và flow đầy đủ theo tuần.
- [Benchmark guide](../benchmark-results/README.md): benchmark 5.000 object,
  ba lần chạy cho mỗi topology và provenance.
- [Basic chaos validation](validation/week6-basic-chaos-and-resilience.md):
  evidence và giới hạn của ba kịch bản chaos/resilience.
- [Checksum and bucket setup validation](validation/member3-checksum-and-mc.md):
  `mc_setup.sh` và kiểm tra SHA256.
