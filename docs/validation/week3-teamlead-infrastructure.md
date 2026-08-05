# Validation Hạ Tầng Nhóm Trưởng Tuần 3

## Phạm Vi

Kiểm tra resource limits, security contract và compatibility của hạ tầng MinIO
distributed sau khi tích hợp code Member 2.

## Resource Limits Đã Chọn

- `minio1`: `1.0 CPU`, `1 GiB RAM`
- `minio2`: `1.0 CPU`, `1 GiB RAM`
- `minio3`: `1.0 CPU`, `1 GiB RAM`
- `minio4`: `1.0 CPU`, `1 GiB RAM`
- `nginx`: `0.50 CPU`, `256 MiB RAM`

Các giới hạn được đặt dưới `deploy.resources.limits`. Đây là mức tối đa cho
lab Docker Desktop; không phải resource reservation và không phải cam kết
production readiness. Prometheus và Grafana chưa được giới hạn trong task này.

## Source Inspection

- Bốn MinIO vẫn dùng command `server http://minio{1...4}/data{1...2}`.
- Mỗi MinIO vẫn có hai named volume.
- MinIO và Nginx vẫn dùng network `minio-net`.
- Nginx vẫn publish endpoint `http://localhost:9000`.
- Root credential vẫn lấy từ `MINIO_ROOT_USER` và `MINIO_ROOT_PASSWORD`.
- `connect_test.py` đọc credential từ environment và không chứa secret literal.
- `.env` bị ignore và không được commit.
- `scripts/connect_test.py` không bị sửa trong task Team Lead.

## Runtime Validation

Trạng thái: `Not executed in coordinator environment` vì Docker daemon không
khả dụng tại thời điểm kiểm tra.

Chạy trên máy có Docker Desktop:

```powershell
docker compose --env-file .env.example -f infra/docker-compose.yml config --quiet
docker compose --env-file .env -f infra/docker-compose.yml down
docker compose --env-file .env -f infra/docker-compose.yml up -d
docker compose --env-file .env -f infra/docker-compose.yml ps
docker compose --env-file .env -f infra/docker-compose.yml logs --tail=100 minio1
docker compose --env-file .env -f infra/docker-compose.yml logs --tail=100 nginx
curl.exe -i http://localhost:9000/minio/health/live
```

Kết quả cần ghi lại:

- Compose config exit code `0`.
- Bốn MinIO và Nginx ở trạng thái `healthy` hoặc `Up` phù hợp healthcheck.
- Health endpoint trả HTTP `200 OK`.
- Không có container bị OOMKilled hoặc restart liên tục.

## Security Audit

- `MINIO_ROOT_USER` và `MINIO_ROOT_PASSWORD` chỉ được lấy từ `.env`.
- `.env.example` chỉ chứa placeholder.
- Credential ứng dụng của `connect_test.py` có thể dùng biến `AWS_*`; nếu không
  có thì lab hiện tại dùng credential root từ environment.
- Đây là fallback phục vụ lab, chưa phải mô hình IAM least privilege.

## Known Gaps

- Prometheus hiện chỉ self-scrape, chưa scrape MinIO metrics.
- Chưa có resource limits riêng cho Prometheus/Grafana.
- Runtime sau khi áp limits phải được kiểm tra trên Docker Desktop thực tế.
- Không tuyên bố production-ready từ resource limits của một máy lab.
