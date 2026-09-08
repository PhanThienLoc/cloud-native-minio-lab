# Cloud-Native MinIO Lab

Mô phỏng một Data Lake trên Docker bằng MinIO distributed, S3 API, Nginx,
Prometheus và Grafana. Dự án tập trung vào lưu trữ object phân tán, ingestion,
kiểm tra tính toàn vẹn, quan sát hệ thống, benchmark và resilience cơ bản trong
môi trường lab một máy.

> Kết quả hiệu năng và chaos chỉ đại diện cho Docker Desktop trên một host; chúng
> không phải bằng chứng về production high availability hay multi-host scale.

## Kiến trúc

![Sơ đồ kiến trúc MinIO distributed](docs/architecture/week1-minio-architecture.png)

Luồng chính: client hoặc script Python gọi S3 API qua Nginx tại
`http://localhost:9000`. Nginx chuyển request vào cụm 4 node MinIO trong
`minio-net`; Prometheus scrape metric và Grafana hiển thị dashboard.

## Thành phần đã tích hợp

| Thành phần | Vai trò |
|---|---|
| MinIO `minio1` - `minio4` | Cụm distributed với 8 drive và Erasure Coding |
| Nginx | Điểm vào S3 chuẩn cho client tại `localhost:9000` |
| Prometheus | Thu thập cluster, node và API metrics của MinIO |
| Grafana | Dashboard `MinIO Cluster Overview` |
| `data_ingestion.py` | Upload dữ liệu theo partition qua S3 API |
| `connect_test.py` | Upload/download và kiểm tra SHA256 cơ bản |
| `load_generator.py` | Tạo tải upload đa luồng, throughput và latency P95/P99 |
| `mc_setup.sh` | Tạo bucket idempotent bằng MinIO Client |
| `verify_checksum.py` | Download object và so sánh SHA256 với dữ liệu nguồn |

## Cấu trúc repository

```text
cloud-native-minio-lab/
├── .env.example                 # Mẫu biến môi trường; không chứa secret thật
├── .github/workflows/ci.yml     # CI validation
├── benchmark-results/           # Hướng dẫn và evidence benchmark đã lưu
├── docs/                        # Tài liệu, validation, báo cáo và demo flow
│   ├── architecture/            # Sơ đồ PNG/PUML và mô tả kiến trúc
│   ├── governance/              # Quy tắc freeze và scope
│   ├── meeting_logs/            # Handoff và ghi nhận phối hợp nhóm
│   ├── reports/                 # Báo cáo, bảng tổng hợp và biểu đồ
│   ├── research/                # Nghiên cứu Erasure Coding/Sharding
│   ├── validation/              # Runtime evidence theo tuần
│   ├── demo-flow.md             # Kịch bản demo ngắn
│   └── project-runbook.md       # Runbook đầy đủ theo tuần
├── infra/                       # Docker Compose, Nginx, Prometheus, Grafana
│   ├── docker-compose.yml       # Topology distributed 4 node
│   ├── docker-compose.standalone.yml
│   ├── nginx/
│   ├── prometheus/
│   └── grafana/
├── scripts/                     # Ingestion, load test, checksum và setup
└── tests/                       # Unit test cho load generator
```

Xem [mục lục tài liệu](docs/README.md) để tìm tài liệu theo mục đích.

## Khởi chạy nhanh

Yêu cầu: Docker Desktop đang chạy, Python 3 nếu dùng script Python, Git và
PowerShell trên Windows.

```powershell
git clone https://github.com/PhanThienLoc/cloud-native-minio-lab.git
Set-Location cloud-native-minio-lab
git switch main

if (!(Test-Path .env)) { Copy-Item .env.example .env }
# Mở .env, thay các giá trị change-me bằng credential local. Không commit .env.

docker compose --env-file .env -f infra/docker-compose.yml config --quiet
docker compose --env-file .env -f infra/docker-compose.yml up -d
docker compose --env-file .env -f infra/docker-compose.yml ps
curl.exe -i http://localhost:9000/minio/health/ready
```

Kết quả mong đợi: các service là `healthy` và endpoint trả `HTTP 200`.

Mở monitoring:

```powershell
Start-Process http://localhost:9090/targets
Start-Process http://localhost:3000
```

Trong Prometheus, target MinIO phải là `UP`. Trong Grafana, đăng nhập bằng
credential `GF_SECURITY_ADMIN_USER` và `GF_SECURITY_ADMIN_PASSWORD` trong
`.env`, rồi mở dashboard **MinIO Cluster Overview**.

Không chạy standalone và distributed cùng lúc: hai topology cùng dùng host port
`9001`. Nếu `infra-minio-standalone-1` đang chạy, dừng nó trước khi khởi động
distributed:

```powershell
docker stop infra-minio-standalone-1
```

## Tài liệu theo nhu cầu

- [Demo Flow](docs/demo-flow.md): checklist demo 5-7 phút, gồm health,
  monitoring, smoke load, security test và resilience.
- [Project Runbook](docs/project-runbook.md): cài đặt, vận hành và validation
  theo tuần.
- [Benchmark Guide](benchmark-results/README.md): quy trình benchmark
  standalone/distributed, 3 lần chạy và provenance.
- [Architecture](docs/architecture/week1-minio-architecture.md): thành phần,
  network và flow request.
- [Validation Week 6](docs/validation/week6-basic-chaos-and-resilience.md):
  evidence node offline, credential sai và smoke load.

## An toàn dữ liệu

- Không commit `.env`, secret, dataset tạm hoặc output benchmark sinh cục bộ.
- Không chạy `docker compose down -v`, `docker volume prune` hoặc `docker system
  prune --volumes` trừ khi chủ động reset toàn bộ lab.
- Đọc [Project Runbook](docs/project-runbook.md) trước khi chạy benchmark lớn
  hoặc chaos test.
