# Validation Nhóm trưởng Tuần 5

## Phạm vi

- Branch: `docs/week5-code-freeze-readiness`.
- Baseline source: `develop` tại `2245087`.
- Ngày kiểm tra: 22/08/2026.
- Agent: `architect`, `sre`, `reviewer`, `reporter`.
- Skill: `benchmark`, `observability`, `project-validation`.
- Freeze state: `INFRASTRUCTURE_FREEZE`; Final Code Freeze chưa kích hoạt.

Không chạy `docker compose down -v` trên stack chính. Fresh bootstrap dùng project
cô lập `week5fresh`; chỉ volume có label/prefix của project này được xóa.

## Source inspected

- Compose định nghĩa 4 MinIO node, mỗi node 2 volume, Nginx, Prometheus và Grafana.
- MinIO image pin cùng digest; Prometheus/Grafana pin version.
- Root/Grafana credential lấy từ environment, không hardcode trong Compose.
- `.env` và `.env.*` bị ignore; `.env.example` là mẫu được track.
- CI chạy Python compile, 12 unit test load generator và Compose config trên PR.

## Environment validation

`.env` local ban đầu thiếu `GF_SECURITY_ADMIN_USER` và
`GF_SECURITY_ADMIN_PASSWORD`. Hai biến được bổ sung local bằng giá trị validation
không in ra terminal; file vẫn bị Git ignore. Sau đó:

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml config --quiet
~~~

Kết quả: exit code `0`, không còn biến bắt buộc bị thiếu.

## Fresh bootstrap cô lập

Stack chính được dừng bằng `down` không `-v`; đủ 10 volume `infra_*` vẫn tồn tại.
Project cô lập được khởi tạo bằng:

~~~powershell
docker compose -p week5fresh --env-file .env.week5-validation `
  -f infra/docker-compose.yml up -d
~~~

Runtime verified:

- bốn MinIO node healthy;
- Nginx live/ready, Prometheus và Grafana trả HTTP `200`;
- `mc admin info`: `Network 4/4 OK`, mỗi node `Drives 2/2 OK`;
- 8 drive online, 0 offline, một pool, `EC:4`;
- bucket list rỗng, chứng minh dùng volume mới nhưng đồng thời xác nhận logical
  state chưa được tự provision;
- Grafana tạo database mới và provision datasource/dashboard.

Sau validation, đúng 10 volume `week5fresh_*` được xóa; kiểm tra còn `0` volume
của project cô lập và vẫn còn đủ 10 volume `infra_*`.

## Restart và persistence stack chính

Trước restart đã tạo object marker 25 byte tại
`week5-readiness/persistence.txt`. Stack chính được khởi động lại bằng một lệnh:

~~~powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d
~~~

Kết quả:

- bốn MinIO node và Nginx/Prometheus healthy;
- live, ready, Prometheus health, Grafana health đều HTTP `200`;
- 12/12 MinIO Prometheus target `UP`;
- `mc admin info`: 4 node, 8 drive online, một pool, `EC:4`;
- marker vẫn đọc đúng `week5-persistence-marker` sau restart;
- object và bucket marker đã được xóa sau kiểm tra.

Kết luận: `one-command infrastructure bootstrap verified on one-host lab`.
Kết quả này chỉ bao gồm container, network, volume, distributed MinIO và monitoring.
Nó không chứng minh one-command complete-system bootstrap, production readiness
hoặc multi-host HA.

## Logical provisioning chưa được xác minh

Fresh bootstrap chưa tự tạo hoặc chứng minh các thành phần sau:

- bucket `raw-data`, `processed-data`, `system-logs`;
- application user, IAM policy và policy attachment;
- versioning hoặc lifecycle rule;
- checksum workflow trên object đã upload rồi download.

Vì vậy tài liệu và slide chỉ được dùng cụm từ `one-command infrastructure
bootstrap`. Chỉ đổi thành `complete-system bootstrap` sau khi các thành phần trên
được provision tự động bằng cùng flow và có runtime evidence.

## Điểm cần theo dõi

### Cập nhật sau khi các PR đã merge

- Benchmark mode/harness của Member 2 đã được merge vào `develop`.
- `mc_setup.sh` và `verify_checksum.py` của Member 3 đã được merge vào `develop`;
  không còn là blocker source. Evidence checksum runtime cần xem tại tài liệu
  validation tương ứng.
- Kiểm thử node offline, credential sai và load smoke được ghi tại
  [`validation/week6-basic-chaos-and-resilience.md`](week6-basic-chaos-and-resilience.md).

- Grafana 11.2.0 vẫn log duplicate registration cho plugin built-in `xychart`;
  lỗi không chặn HTTP `200` hoặc dashboard provisioning trong lần kiểm tra này.
- Screenshot Grafana và video startup chưa được coordinator thu vì không có
  browser/video recorder; phải quay/chụp thủ công và không được ghi là đã có.
- IAM, lifecycle và recovery sau restart cần tiếp tục ghi evidence nếu muốn đưa
  thành kết luận hoàn chỉnh trong báo cáo.
