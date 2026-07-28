# Cloud-Native MinIO Lab: Project Runbook

Runbook này mô tả flow học tập, chạy thử và bàn giao của dự án trong 6 tuần. Mỗi kết luận cần phân biệt rõ giữa kiểm tra source và bằng chứng runtime.

## 1. Kiến trúc và vai trò

~~~text
Client / mc / Python -> Nginx :9000 -> MinIO minio1..minio4
                                      -> Prometheus / Grafana
~~~

- Nhóm trưởng: /infra, Docker Compose, Nginx, network, monitoring và review.
- Member 2: Python data generation, S3 connection, ingestion và load generation.
- Member 3: mc, IAM, chaos engineering, validation và báo cáo.

Nginx chỉ là client entrypoint. Distributed storage, erasure coding, quorum và healing do MinIO đảm nhiệm.

## 2. Chuẩn bị môi trường

Yêu cầu:

- Docker Desktop đang chạy.
- Git.
- Python 3 và pip cho script Python.
- PowerShell trên Windows hoặc Bash trên Linux/macOS.

Từ repository root:

~~~powershell
cd D:\Cloud\cloud-native-minio-lab
git switch develop
git pull origin develop
~~~

Tạo credential local một lần:

~~~powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
~~~

Không commit .env, credential thật hoặc dataset sinh ra.

## 3. Flow Git

Mọi task bắt đầu từ develop:

~~~powershell
git switch develop
git pull origin develop
git switch -c feat/<ten-task>
~~~

Kiểm tra và commit:

~~~powershell
git status
git diff --check
git add <file-duoc-phep>
git diff --cached --name-only
git commit -m "feat: <mo-ta-ngan>"
git push -u origin feat/<ten-task>
~~~

Tạo PR vào develop và yêu cầu ít nhất một thành viên review. Chỉ merge develop vào main khi milestone hoặc final demo đã ổn định.

Các file Codex local (AGENTS.md, .agents/, .codex/, project-brain.md, docs/codex-usage.md) không phải deliverable GitHub của nhóm.

## 4. Tuần 1: nền tảng và evidence

Sau khi PR tuần 1 được merge, kiểm tra artifact:

~~~powershell
rg --files docs/architecture docs/research docs/validation
~~~

Cần có sơ đồ .puml, ảnh .png, Markdown kiến trúc, nghiên cứu Erasure Coding/Sharding và validation note cho data generator.

Tạo môi trường Python:

~~~powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r scripts\requirements.txt
~~~

Chạy test nhỏ:

~~~powershell
python scripts\generate_data.py --output-dir .\scripts\sample_data_validation --log-size-mb 1 --csv-size-mb 1 --binary-count 5 --binary-size-kb 20
~~~

Ghi lại file, kích thước và exit code. Không commit dataset:

~~~powershell
Remove-Item -Recurse -Force .\scripts\sample_data_validation
~~~

## 5. Tuần 2: MinIO distributed và Nginx

Kiểm tra Compose:

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml config --quiet
~~~

Khởi động:

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml pull
docker compose --env-file .env -f infra/docker-compose.yml up -d
docker compose --env-file .env -f infra/docker-compose.yml ps
~~~

Health check qua Nginx:

~~~powershell
curl.exe -i http://localhost:9000/minio/health/live
~~~

Kết quả cần là HTTP 200.

### 5.1. Kiểm tra cluster bằng MinIO Client

Nếu chưa cài mc local, dùng image minio/mc:

~~~powershell
docker run --rm --network minio-net --env-file .env --entrypoint /bin/sh minio/mc:latest -c 'mc alias set myminio http://nginx:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc admin info myminio'
~~~

Runtime evidence cần ghi lại:

- 4 node được liệt kê.
- Network: 4/4 OK.
- Mỗi node có Drives: 2/2 OK.
- Một pool với 8 drive online.
- Giá trị EC quan sát được, ví dụ EC:4.

Kiểm tra bucket qua Nginx:

~~~powershell
docker run --rm --network minio-net --env-file .env --entrypoint /bin/sh minio/mc:latest -c 'mc alias set myminio http://nginx:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc ls myminio'
~~~

Smoke test tạo bucket:

~~~powershell
docker run --rm --network minio-net --env-file .env --entrypoint /bin/sh minio/mc:latest -c 'mc alias set myminio http://nginx:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc mb --ignore-existing myminio/test-bucket && mc ls myminio'
~~~

Trạng thái hiện tại đã runtime-verified: 4 node, 8 drive, một pool, EC:4, health HTTP 200 và bucket smoke test thành công.

## 6. Tuần 3: data ingestion và IAM

Source hiện tại:

- scripts/data_ingestion.py mới tạo file partition mẫu, chưa upload S3.
- connect_test.py chưa có trong branch tích hợp hiện tại.
- scripts/mc_setup.sh mới tạo một bucket mặc định và cần Member 3 review trước khi dùng như deliverable 3 bucket.

Sau khi script được hoàn thiện, flow dự kiến là:

~~~powershell
python scripts\connect_test.py
bash scripts/mc_setup.sh
~~~

Endpoint và credential phải lấy từ environment; không thêm secret vào script hoặc README.

## 7. Tuần 4: observability và load testing

Endpoint monitoring hiện có:

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

Khởi động:

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d prometheus grafana
~~~

Gap hiện tại: infra/prometheus/prometheus.yml chỉ self-scrape Prometheus, chưa scrape MinIO metrics. Trước load test cần bổ sung và kiểm chứng request rate, latency, throughput, object/storage usage và node availability.

## 8. Tuần 5: benchmark

Mỗi benchmark cần ghi topology 1 node hoặc 4 node, workload, object size, concurrency, latency, throughput, success/error rate, host resource và commit cấu hình. Không so sánh hai kết quả nếu workload hoặc tài nguyên host khác nhau.

## 9. Tuần 6: chaos engineering

Flow tối thiểu:

~~~powershell
docker stop infra-minio3-1
# kiểm tra upload/download và mc admin info
docker start infra-minio3-1
# chờ cluster heal rồi ghi thời gian phục hồi
~~~

Sau mỗi failure scenario ghi node bị dừng, thao tác đọc/ghi, health, mc admin info, thời gian healing và checksum. Docker nhiều node trên một host không mô phỏng failure domain độc lập.

## 10. Troubleshooting

### Cổng 9000 bị chiếm

~~~powershell
docker ps --format "table {{.Names}}\t{{.Ports}}"
netstat -ano | findstr ":9000"
~~~

Sau khi dừng đúng process/container đang chiếm cổng, recreate riêng Nginx:

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d --force-recreate nginx
~~~

### Nginx không publish port

~~~powershell
docker port infra-nginx-1
docker compose --env-file .env -f infra/docker-compose.yml up -d --force-recreate nginx
~~~

### Xem log

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml logs --tail 100 minio1 nginx
~~~

### Dừng hệ thống an toàn

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml stop
~~~

docker compose down -v và target make down có thể xóa volume dữ liệu. Chỉ dùng khi cố ý reset toàn bộ lab.

## 11. Evidence template

~~~~markdown
## <Tên kiểm thử>

- Date/time:
- Branch:
- Commit:
- Environment:
- Command:

Output thực tế:
<output thực tế>

- Conclusion: Runtime verified / Source inspected / Not executed / Planned
- Limitations:
~~~~

Không ghi Passed nếu command chưa được chạy hoặc output không được lưu.
