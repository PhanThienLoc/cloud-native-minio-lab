# Handoff nguyên liệu slide Tuần 5

## Baseline

- `develop`: `2245087` sau PR #13.
- Trạng thái: Code Freeze, chỉ nhận `fix:` và `docs:`.
- Kiến trúc: 4 MinIO node x 2 volume, Nginx, Prometheus, Grafana trên
  `minio-net`.

## File cung cấp cho Thành viên 3

- Sơ đồ PNG: [`../architecture/week1-minio-architecture.png`](../architecture/week1-minio-architecture.png).
- Sơ đồ nguồn: [`../architecture/week1-minio-architecture.puml`](../architecture/week1-minio-architecture.puml).
- Docker Compose: [`../../infra/docker-compose.yml`](../../infra/docker-compose.yml).
- Prometheus: [`../../infra/prometheus/prometheus.yml`](../../infra/prometheus/prometheus.yml).
- Dashboard JSON: [`../../infra/grafana/dashboards/minio-cluster-overview.json`](../../infra/grafana/dashboards/minio-cluster-overview.json).
- Evidence observability: [`../validation/week4-observability.md`](../validation/week4-observability.md).
- Evidence load test: [`../validation/week4-member2-load-test.md`](../validation/week4-member2-load-test.md).
- Phân tích CAP/hướng phát triển: [`../reports/week5-cap-cloud-native-and-future.md`](../reports/week5-cap-cloud-native-and-future.md).

## Nội dung ngắn dùng cho slide

### CAP Theorem

CAP chỉ tạo trade-off khi network partition xảy ra. MinIO dùng quorum để bảo vệ
tính nhất quán của object và có thể từ chối ghi khi không đủ write quorum thay vì
tạo trạng thái mâu thuẫn. Availability phụ thuộc parity, số drive khỏe và loại
thao tác. Nginx chỉ cân bằng request, không tạo redundancy.

### Luồng kiến trúc

~~~text
Python / mc / S3 Client
          -> Nginx :9000
          -> MinIO distributed pool: minio1..minio4, 8 drive
          -> Prometheus scrape metrics
          -> Grafana dashboard
~~~

### Số liệu đã xác minh

- 4 node, `Network: 4/4 OK` trên mỗi node.
- 8 drive online, một pool, `EC:4`.
- 12/12 MinIO Prometheus target `UP`.
- Load test 5.000 x 100 KiB: 5.000/5.000 thành công.
- Throughput ứng dụng: `19,0160 MiB/s`.
- Average/P95/P99 S3 upload latency: `40,8964/75,5691/102,8179 ms`.
- Host benchmark: Windows 11, 20 logical CPU, 15,64 GiB RAM, disk 250 GiB.

## Ảnh và video

- Sơ đồ kiến trúc PNG: `Ready`.
- Screenshot Grafana: `Not captured` trong phiên coordinator vì không có browser
  khả dụng. Nhóm trưởng cần chụp UI thật khi chạy smoke/full load.
- Video startup bằng Compose: `Not recorded`; cần quay thủ công.

Checklist chụp Grafana:

1. Mở `http://localhost:3000` và dashboard `MinIO Cluster Overview`.
2. Chạy smoke test 100 object trước, sau đó full load khi cần.
3. Chụp đủ năm panel và timestamp; không cắt mất legend/node.
4. Không để credential, `.env` hoặc terminal chứa secret xuất hiện trong ảnh.
5. Lưu vào `docs/screenshots/week5/` trên branch của Thành viên 3 nếu nhóm quyết
   định theo dõi screenshot bằng Git.

## Điểm cần review trên slide

- Không gọi lab một host là production hoặc multi-host HA.
- Không tuyên bố benchmark 1 node vs 4 node trước khi Member 2 chạy cùng workload
  tối thiểu ba lần cho mỗi topology.
- IAM, Lifecycle và Chaos chỉ đưa vào phần “đã hoàn thành” khi branch tương ứng
  đã merge và có runtime evidence.
- Dùng “4 node x 2 volume = 8 drive endpoint”, không nói Nginx tạo Erasure Coding.
