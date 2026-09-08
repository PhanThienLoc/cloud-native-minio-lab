# Validation Observability của Nhóm trưởng - Tuần 4

## Phạm vi

Validation cho Prometheus, Grafana provisioning và ảnh hưởng tới hạ tầng MinIO.
Không kiểm thử hoặc sửa logic `scripts/load_generator.py` trong tài liệu này.

## Source inspected

- Bốn MinIO node bật `MINIO_PROMETHEUS_AUTH_TYPE=public`.
- Port `9000` của từng MinIO node không publish ra host; metrics public chỉ phục
  vụ lab trong `minio-net`.
- Prometheus dùng image pin `prom/prometheus:v2.55.1`.
- Prometheus lưu TSDB trong named volume `prometheus-data` với retention 7 ngày.
- Job `minio-cluster` scrape `/minio/v2/metrics/cluster` trên bốn node.
- Job `minio-node` scrape `/minio/v2/metrics/node` trên bốn node.
- Job `minio-api` scrape `/minio/metrics/v3/api/requests` trên bốn node để lấy
  request counter theo API operation.
- Grafana lấy admin user/password từ `.env` và không cho anonymous access hoặc
  self-signup.
- Prometheus datasource và dashboard được provision từ file trong repository.
- Dashboard có năm panel: Throughput, S3 Request Rate, Storage Usage, Object Count
  và Node Health.
- Prometheus và Grafana có giới hạn tối đa `0.50 CPU`, `512 MiB RAM` mỗi service.

## Runtime verified ngày 21/08/2026

- Bốn MinIO container: `healthy`.
- Nginx: `healthy`; `/minio/health/live` trả HTTP `200`.
- Prometheus: `healthy`; `/-/healthy` trả HTTP `200`.
- Grafana `/api/health` trả HTTP `200`, database `ok`, version `11.2.0`.
- `promtool check config` xác nhận `prometheus.yml` hợp lệ.
- Job `minio-cluster`: bốn target `minio1:9000` đến `minio4:9000` đều `UP`.
- Job `minio-node`: bốn target `minio1:9000` đến `minio4:9000` đều `UP`.
- Job `minio-api`: bốn target `minio1:9000` đến `minio4:9000` đều `UP`.
- Prometheus thu được 77 metric có prefix `minio_` từ cluster endpoint.
- Query storage usage, object count, throughput và bốn series node health trả dữ
  liệu hợp lệ.
- Năm panel dashboard đều có query trả dữ liệu: Throughput, S3 Request Rate,
  Storage Usage, Object Count và Node Health.
- Ba file datasource, dashboard provider và dashboard JSON đã được mount vào
  Grafana. Log xác nhận quá trình provision dashboard bắt đầu và kết thúc.
- MinIO image đang pin không cung cấp `minio_s3_requests_total` trên metrics v2.
  Endpoint v3 cung cấp `minio_api_requests_total` với nhãn `name` và `type`; panel
  Request Rate dùng metric này để phân tách API operation.
- Smoke test qua Nginx đã tạo bucket tạm, upload, đọc, xóa object và xóa bucket;
  exit code `0` và không để lại bucket test.
- Query request rate trả 12 API operation series. `PutObject`, `GetObject`,
  `DeleteMultipleObjects` và `DeleteBucket` đều có rate khác `0`, khoảng
  `0.0222 request/second` trong cửa sổ một phút của smoke test.
- Sau 20 S3 GET request khác qua Nginx, query outbound throughput trả một series với giá trị khoảng
  `95.58 byte/second`; inbound throughput trả một series với giá trị `0` vì các
  request thử không upload payload.
- `docker stats --no-stream` khi idle ghi nhận mỗi MinIO dùng khoảng
  `90-113 MiB/1 GiB`, Prometheus `34.59 MiB/512 MiB`, Grafana
  `47.95 MiB/512 MiB` và Nginx `2.80 MiB/256 MiB`. Đây chỉ là số liệu idle,
  không đại diện mức dùng tài nguyên khi load test.

## Chưa thực hiện

- Chưa chạy load generator 5.000 object vì code Member 2 trên branch riêng còn
  blocker trước khi merge. Validation Tuần 4 chỉ tạo request và object tạm kích
  thước rất nhỏ để kiểm tra pipeline metrics.
- Chưa dùng kết quả quan sát ngắn này làm benchmark; benchmark thuộc Tuần 5.

## Lưu ý runtime

Docker Desktop tự khởi động container Hadoop `namenode` trên máy kiểm thử và chiếm
cổng `9000`. Container này phải được dừng trước khi Nginx có thể publish cổng.
Không dùng `docker compose down -v`; named volume đã được giữ nguyên trong toàn bộ
validation.

File `.env` local được tạo trước Tuần 4 nên chưa có hai biến Grafana. Phiên
validation truyền credential Grafana tạm thời cho Compose và không ghi giá trị
vào tài liệu. Trước lần khởi động thông thường tiếp theo, mỗi thành viên phải tự
đặt `GF_SECURITY_ADMIN_USER` và `GF_SECURITY_ADMIN_PASSWORD` trong `.env` theo
contract của `.env.example`.

Grafana `11.2.0` có log duplicate registration cho plugin built-in `xychart`.
Trong lần kiểm tra này lỗi đó không ngăn Grafana trả HTTP `200` hoặc hoàn tất
dashboard provisioning, nhưng cần tiếp tục theo dõi nếu dashboard UI gặp lỗi.
