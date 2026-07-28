# Week 2 Team Handoff

## Trạng thái hiện tại

Hạ tầng tuần 2 của Nhóm trưởng nằm trên branch `feat/week2-distributed-minio-infra` và đã được kiểm thử runtime, chờ review/merge vào `develop`.

Đã có:

- 4 service MinIO: `minio1`, `minio2`, `minio3`, `minio4`.
- Distributed command: `server http://minio{1...4}/data{1...2}`.
- 2 volume/node, tổng cộng 8 data volume.
- Docker network `minio-net`.
- Nginx S3 endpoint: `http://localhost:9000`.
- Prometheus: `http://localhost:9090`.
- Grafana: `http://localhost:3000`.
- Credential bắt buộc lấy từ `.env`.
- MinIO image đã pin bằng digest.
- MinIO và Nginx có healthcheck.

## Runtime evidence đã đạt

- `docker compose config`: PASS.
- 4 MinIO node và Nginx: `healthy`.
- Health live/ready qua `localhost:9000`: HTTP 200.
- Docker DNS phân giải được cả `minio1`, `minio2`, `minio3`, `minio4`.
- `mc admin info`: 4 node, `Network: 4/4 OK`.
- Mỗi node: `Drives: 2/2 OK`.
- Tổng cộng 8 drive online, một pool, `EC:4`.
- Tạo/list bucket qua Nginx: PASS.
- Upload/download object qua Nginx: PASS.
- SHA-256 file gốc và file download giống nhau.
- Object còn tồn tại sau `docker compose down` rồi `up`.
- Khi dừng `minio4`, cluster nhận biết node offline và upload test vẫn thành công.
- Khi start lại `minio4`, cluster trở lại `4/4`, 8 drive online.

Evidence chi tiết: `docs/validation/week2-infrastructure.md`.

## Cách lấy code nền

Sau khi PR hạ tầng được merge vào `develop`, mỗi member cập nhật branch riêng:

    git switch develop
    git pull origin develop
    git switch -c feat/week2-<ten-task>

Nếu branch đã tồn tại:

    git switch feat/week2-<ten-task>
    git fetch origin
    git rebase origin/develop

Không merge branch của Nhóm trưởng trực tiếp vào branch member nếu hạ tầng đã có trong `develop`.

## Thông tin kết nối

Client endpoint: `http://localhost:9000`.

Trong Docker network: `http://nginx:9000`.

Credential đọc từ `.env`:

    MINIO_ROOT_USER
    MINIO_ROOT_PASSWORD

Không commit `.env`, secret hoặc dataset.

## Nhiệm vụ Member 2

File dự kiến: `scripts/connect_test.py`.

Member 2 cần:

- Dùng boto3 hoặc minio-py.
- Dùng endpoint `http://localhost:9000`.
- Đọc endpoint và credential từ environment hoặc `.env`.
- Upload và download file qua Nginx.
- So sánh checksum hoặc kích thước.
- Ghi log thành công/lỗi.
- Đo latency upload/download.
- Có timeout và xử lý lỗi kết nối.

Acceptance criteria:

- Upload PASS.
- Download PASS.
- Checksum giống nhau.
- Có latency upload/download.
- Không hardcode secret.
- Có output test trong PR.
- Chỉ thay đổi file thuộc scope Member 2.

## Nhiệm vụ Member 3

File chính: `scripts/mc_setup.sh` và `docs/reports/`.

Member 3 cần:

- Đọc endpoint và credential từ environment.
- Set alias tới `http://localhost:9000`.
- Tạo đủ 3 bucket: `raw-data`, `processed-data`, `system-logs`.
- Có thể bật versioning cho `raw-data` nếu nhóm thống nhất.
- Dùng `set -euo pipefail`.
- Không hardcode credential thật.
- Hoàn thiện Chương 1 và Chương 2 trong `docs/reports/`.

Acceptance criteria:

- Alias set PASS.
- Ba bucket tồn tại.
- Script không chứa secret thật.
- Báo cáo giải thích File Storage/NFS, Object Storage/MinIO, metadata, flat namespace, Erasure Coding và Sharding.
- Có output kiểm thử trong PR.
- Không sửa code Member 2 hoặc `/infra`.

## Gap hiện tại

- Prometheus mới self-scrape Prometheus, chưa scrape MinIO metrics.
- Dashboard Grafana chưa hoàn thiện cho tuần 4.
- `connect_test.py` chưa có trong branch tích hợp.
- `mc_setup.sh` chưa đáp ứng yêu cầu 3 bucket tuần 2.
- Docker nhiều node trên một host không tương đương 4 máy vật lý độc lập.
- Artifact tuần 1 cần được merge từ `fix/week1-finalization` vào `develop`.

## Quy tắc PR

Mỗi member chỉ stage file thuộc phần mình:

    git status
    git diff --name-only
    git diff --check
    git add <file-duoc-phep>
    git diff --cached --name-only
    git commit -m "feat: <mo-ta-task>"
    git push -u origin feat/<ten-task>

PR target là `develop`, không phải branch của Nhóm trưởng.

PR phải có summary, files changed, commands tested, runtime output và known limitations.

## Checklist trước PR

- [ ] Branch cập nhật từ `develop` mới nhất.
- [ ] Endpoint dùng đúng `localhost:9000`.
- [ ] Không sửa ngoài scope member.
- [ ] Không có `.env`, secret hoặc dataset trong Git.
- [ ] Có command test và output thực tế.
- [ ] `git diff --check` PASS.
- [ ] PR target là `develop`.
- [ ] Tài liệu phân biệt `Runtime verified`, `Source inspected`, `Not executed` và `Planned`.
