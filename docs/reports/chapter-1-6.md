# Báo cáo: Cloud-Native MinIO Lab

## Chương 1: Tổng quan dự án

### 1.1 Bối cảnh và Bài toán

Sự phát triển bùng nổ của dữ liệu (Big Data) và nhu cầu lưu trữ, truy xuất ở quy mô lớn đặt ra nhiều thách thức cho kiến trúc lưu trữ truyền thống. Hệ thống lưu trữ tập trung (centralized file servers, NAS) thường vận hành theo mô hình scale-up: tăng sức mạnh phần cứng ở một máy chủ hoặc một thiết bị lưu trữ tập trung. Mô hình này giới hạn về:

- Hiệu năng I/O bị ràng buộc bởi phần cứng vật lý của máy chủ lưu trữ; khi khối lượng đọc/ghi tăng, nút đơn lẻ trở thành cổ chai (bottleneck).
- Rủi ro Single Point of Failure (SPOF): một lỗi phần cứng, lỗi hệ điều hành, hoặc sự cố hạ tầng có thể khiến toàn bộ dịch vụ lưu trữ ngưng trệ.
- Chi phí mở rộng (scale-up) cao: nâng cấp CPU, RAM, hoặc thay đĩa hiệu năng cao tốn kém và không mở rộng tuyến tính.
- Metadata và coordination thường tập trung, dẫn tới giới hạn scale và gia tăng độ phức tạp khi áp dụng replication hoặc sharding.

Khi dữ liệu đạt kích thước lớn (từ hàng chục terabyte đến petabyte), các yêu cầu về durability (độ bền), availability (tính sẵn sàng), và throughput buộc thiết kế chuyển sang mô hình phân tán (scale-out). Các hệ phân tán chia dữ liệu thành nhiều mảnh, phân phối mảnh lên nhiều node và sử dụng cơ chế bảo vệ dữ liệu (replication hoặc erasure coding) để chịu được mất mát node.

Mục tiêu bài toán của dự án này là xây dựng một môi trường mô phỏng Distributed Object Storage bằng MinIO, nhằm:

- Minh họa nguyên lý hoạt động của lưu trữ đối tượng phân tán.
- Đánh giá hành vi hệ thống khi mất node (chaos testing) và khi có tải cao (load testing).
- Thực hành thiết lập monitoring (Prometheus + Grafana) để thu thập metric hiệu năng.

### 1.2 Mục tiêu dự án

Các mục tiêu kỹ thuật cụ thể:

1. Thiết lập cụm MinIO ở chế độ distributed (4 node) trên môi trường container bằng Docker Compose.
2. Tạo bộ công cụ tự động (scripts) để sinh tải (upload/download) với khả năng cấu hình số lượng file, kích thước file, số thread và chế độ hoạt động (standalone/distributed).
3. Thu thập và hiển thị metric (throughput, latency, node health) trên Grafana thông qua Prometheus.
4. Thực hiện thử nghiệm fault-injection (tắt 1–2 node trong quá trình chạy) để quan sát hành vi degraded mode và phục hồi.
5. So sánh chi phí lưu trữ và trade-offs giữa replication và erasure coding (về lưu lượng mạng khi rebuild, overhead lưu trữ).

### 1.3 Phạm vi triển khai

Phạm vi kỹ thuật của lab giới hạn ở môi trường giả lập trên một hoặc nhiều host chạy Docker:

- Sử dụng `infra/docker-compose.yml` để dựng cụm gồm 4 container MinIO (`minio1`..`minio4`), `nginx` làm reverse-proxy/load balancer, `prometheus` và `grafana` để giám sát.
- Map volumes từ host vào container (ví dụ `D:/minio_data/minio1/data1`) để mô phỏng đĩa cục bộ.
- Sử dụng `scripts/load_generator.py` và `scripts/data_ingestion.py` để nạp và kiểm tra dữ liệu.
- Không triển khai Kubernetes hoặc môi trường production-scale trong phạm vi hiện tại; đề xuất mở rộng trong phần kết luận.


## Chương 2: Cơ sở lý thuyết nền tảng

### 2.1 Phân tích kiến trúc lưu trữ: File Storage vs Object Storage

File Storage (Hệ thống tập tin phân cấp)

- Cấu trúc: tổ chức theo cây thư mục (hierarchical namespace).
- Giao diện: POSIX/SMB/NFS; hỗ trợ thao tác file-level và block-level.
- Metadata: lưu trữ metadata hệ thống tập tin như quyền truy cập, timestamps, inode.
- Ưu điểm:
  - Tương thích với nhiều ứng dụng legacy.
  - Hỗ trợ thao tác file ngẫu nhiên (random reads/writes) tốt.
- Nhược điểm:
  - Khó scale-out theo chiều ngang; metadata server có thể là giới hạn.
  - Thiết kế không tối ưu cho object-level scaling với hàng triệu tệp nhỏ.

Object Storage (Lưu trữ đối tượng)

- Cấu trúc: namespace phẳng (flat namespace) theo cặp `bucket/object-key`.
- Giao diện: RESTful API (S3-compatible) cho các thao tác PUT/GET/DELETE/HEAD.
- Metadata: mỗi object kèm metadata tuỳ ý (key-value), cho phép indexing, lifecycle policy, tagging.
- Ưu điểm:
  - Dễ dàng scale-out bằng cách thêm node và cân bằng phân phối đối tượng.
  - Phù hợp cho workloads lưu trữ dung lượng lớn (cold/warm data) và object-based applications.
  - Hỗ trợ features như multipart upload (cho file lớn), presigned URLs.
- Nhược điểm:
  - Không cung cấp POSIX semantics (khó cho workloads cần random write/lock).
  - Latency cho hàng loạt small objects có thể cao nếu thiết kế không tối ưu.

So sánh tóm tắt

- Namespace: Tree vs Flat — object storage mạnh khi cần scale lớn.
- Metadata: hạn chế vs phong phú — object storage cho phép metadata tùy biến.
- Semantics: POSIX vs RESTful — lựa chọn tùy theo ứng dụng.
- Scale & durability: Object storage được thiết kế để tối ưu durability và availability bằng replication/erasure coding.

### 2.2 Cơ chế cốt lõi của Object Storage

Metadata và Global Namespace

- Global Namespace là cách mà hệ thống cung cấp một không gian tên duy nhất cho client mặc dù dữ liệu được phân tán. Metadata service hoặc metadata store theo dạng phân tán (metadata shards, gossip, consistent hashing) ánh xạ mỗi `object` tới vị trí vật lý (shard, disk, node).
- Metadata trong object storage thường đa dạng và có thể dùng để lập chỉ mục, quy tắc lifecycle, phân quyền.

RESTful S3-compatible API

- Các thao tác chính: PUT (upload object), GET (tải object), DELETE, LIST, multipart upload, HEAD.
- Multipart upload cho phép chia file lớn thành parts, upload song song; server sau đó ghép parts lại.
- Pre-signed URL cho phép ủy quyền tạm thời để upload/download.

Consistency model

- Nhiều object stores chấp nhận các trade-off giữa consistency và availability (theo CAP theorem) — MinIO đảm bảo strongly consistent semantics cho S3 API trong cluster, nhưng các hệ khác có thể cung cấp eventual consistency cho các operation cụ thể.

### 2.3 Thuật toán phân tán và Erasure Coding

Nguyên lý Erasure Coding

- Erasure coding (ví dụ Reed–Solomon) chia dữ liệu thành `k` blocks dữ liệu và tạo `m` parity blocks, tổng `n = k + m` blocks. Hệ thống có thể recover dữ liệu nếu tối đa `m` blocks bị mất.
- So với replication (ví dụ 3x), erasure coding giảm overhead lưu trữ: ví dụ RS(6,3) có overhead 1.5x so với 3x replication.

Quá trình ghi và đọc

- Ghi: dữ liệu được cắt thành stripes/blocks, tính parity, sau đó lưu shards lên nodes khác nhau theo policy phân phối (spread across drives/nodes).
- Đọc: nếu tất cả shards cần thiết có sẵn, server ghép lại và trả object; nếu một số shards bị mất, decode từ shards còn lại.

Repair và Rebuild

- Khi phát hiện disk/node bị mất, hệ thống sẽ thực hiện rebuild background để tái tạo shards thiếu lên các vị trí mới.
- Chi phí rebuild lớn về network I/O và CPU (decode/encode parity). Thiết kế repair policy (eager vs lazy) ảnh hưởng tới thời gian phục hồi và overhead hệ thống.

Trade-offs và thiết kế hệ thống

- Erasure coding tiết kiệm lưu trữ nhưng tăng chi phí repair. Ứng dụng nên cân nhắc: latency đọc degraded, bandwidth rebuild, và độ phức tạp triển khai.


## Chương 3: Thiết kế Kiến trúc Hệ thống

### 3.1 Sơ đồ hạ tầng

Mô tả thành phần trong `infra/docker-compose.yml`:

- `minio1`..`minio4`: bốn service chạy image `minio/minio` ở chế độ distributed. Mỗi node khai báo command `server http://minio{1...4}/data{1...2}` để MinIO biết endpoints của các nodes và paths dữ liệu.
- `nginx`: proxy/lb nhận traffic trên cổng 9000 và chuyển tiếp tới cụm MinIO. Giúp client truy cập một điểm duy nhất.
- `prometheus`: scrape metrics từ MinIO (MinIO export Prometheus metrics khi biến `MINIO_PROMETHEUS_AUTH_TYPE` được bật).
- `grafana`: hiển thị dashboard đã cấu hình (dashboards có sẵn trong `infra/grafana/dashboards`).

Kiến trúc đề xuất (minh hoạ):

Client --> Nginx (9000) --> MinIO Cluster (minio1..minio4)
                                 |--> Prometheus (scrape)
                                 |--> Grafana (visualize)

Giao tiếp nội bộ giữa MinIO nodes: HTTP API trên mạng `minio-net`, cluster dùng quorum và cơ chế coordination của MinIO để đảm bảo metadata consistent.

### 3.2 Cấu trúc lưu trữ vật lý

- Mỗi `minioX` mount hai volumes host tương ứng `data1`, `data2`. Mục đích: tăng số path lưu trữ trên node để MinIO phân phối objects sang nhiều disk logical, tăng băng thông I/O song song.
- Trong file compose có các mapping ví dụ: `D:/minio_data/minio1/data1:/data1` — lưu ý: trên môi trường Windows, cần đảm bảo quyền và đường dẫn tồn tại trước khi khởi container.
- Trên môi trường production, nên dùng dedicated disks hoặc block storage; tránh dùng cùng một disk vật lý cho nhiều node giả lập trên cùng host (khi chỉ mô phỏng, host I/O vẫn là điểm giới hạn).

### 3.3 Thiết kế luồng dữ liệu (Data Flow)

Upload (multipart / large objects):

1. Client gọi `PUT /bucket/object?uploads` để khởi multipart upload.
2. Client upload các `part` song song bằng `PUT /bucket/object?partNumber=X&uploadId=...`.
3. MinIO nhận mỗi part, chia part thành shards theo erasure coding scheme (n shards) và ghi shards lên các node/disks tương ứng.
4. Sau khi hoàn tất, client gọi `CompleteMultipartUpload`; MinIO cập nhật metadata object và object trở nên có thể đọc.

Read:

1. Client `GET` object.
2. MinIO xác định nơi lưu shards bằng metadata và trả stream object; nếu thiếu shards, MinIO decode từ shards còn lại để trả kết quả.

Failure handling:

- Trong trường hợp một node mất, requests có thể vẫn hoàn thành nếu số shards còn đủ để decode. Một số request có thể bị chậm hoặc bị retry tùy vào timing của failure và repair progress.


## Chương 4: Quy trình Thực thi và Cấu hình

### 4.1 Cài đặt hạ tầng (chi tiết)

Tập trung vào `infra/docker-compose.yml` và `.env`:

- Biến môi trường bắt buộc (ví dụ trong `.env.example`):
  - `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` — credentials root cho MinIO.
  - `GF_SECURITY_ADMIN_USER`, `GF_SECURITY_ADMIN_PASSWORD` — admin cho Grafana.

- Mạng: `minio-net` (driver: bridge) để các containers giao tiếp qua tên dịch vụ (DNS nội bộ của Docker Compose).

Lệnh khởi chạy mẫu (PowerShell):

```powershell
cd "C:\Users\Admin\Desktop\New folder (9)\cloud-native-minio-lab"
Copy-Item .env.example .env
docker compose --env-file .env -f infra/docker-compose.yml up -d
docker compose --env-file .env -f infra/docker-compose.yml ps
```

Ghi chú:
- Trước khi chạy, đảm bảo các host paths cho volumes tồn tại (ví dụ `D:/minio_data/minio1/data1`).
- Nếu chạy trên Windows, quyền truy cập và anti-virus có thể ảnh hưởng tới hiệu năng I/O.

### 4.2 Thiết lập hệ thống: bucket và credentials

Tạo alias và bucket bằng MinIO Client (`mc`) hoặc dùng `boto3`:

Với `mc`:

```powershell
mc alias set local http://localhost:9000 $env:MINIO_ROOT_USER $env:MINIO_ROOT_PASSWORD
mc mb local/benchmark-bucket --ignore-existing
```

Với `boto3` (Python):

```python
import boto3
s3 = boto3.resource('s3', endpoint_url='http://localhost:9000', aws_access_key_id='minioadmin', aws_secret_access_key='minioadmin')
s3.create_bucket(Bucket='benchmark-bucket')
```

Bảo mật:
- Không dùng root credentials cho ứng dụng benchmark; nên tạo user riêng với policy giới hạn.
- Nếu cần public access (ví dụ chia sẻ), áp dụng bucket policy cụ thể.

### 4.3 Phát triển Script tương tác

Thư mục `scripts/` chứa các script chính:

- `load_generator.py` — sinh tải: hỗ trợ tham số `--num-files`, `--threads`, `--file-size`, `--mode` (standalone/distributed) và `--output` để lưu kết quả.
- `data_ingestion.py` — tạo dữ liệu mẫu theo partition hoặc theo kích thước.
- `verify_checksum.py` — kiểm tra tính toàn vẹn file sau upload/download.

Các điểm quan trọng trong `load_generator.py`:
- `parse_size()` — parse các đơn vị `KB`, `MB`, `GB` và giới hạn kích thước object (ví dụ không vượt quá 1GB trong lab).
- `validate_workload()` — guard để đảm bảo tổng payload in-flight giữa threads không vượt quá threshold (ví dụ 512MiB) nhằm tránh làm ngẹt bộ nhớ hoặc saturate network.
- `run_with_retry()` — retry strategy dựa trên phân loại lỗi S3 (transient vs permanent) với số lần thử giới hạn (ví dụ 3 attempts).

Mẫu chạy benchmark distributed:

```powershell
cd scripts
python load_generator.py --num-files 5000 --threads 8 --file-size 1MB --mode distributed --output ..\benchmark-results\raw\distributed_run1
```

Kết quả sẽ được lưu trong thư mục `benchmark-results/raw/` (ví dụ
`benchmark-results/raw/distributed_run1.json`).


## Chương 5: Kết quả Kiểm thử và Đánh giá Hiệu năng

> Phần này sử dụng kết quả đã lưu trong `benchmark-results/raw/` —
> `standalone_run1.json`, `standalone_run2.json`, `standalone_run3.json`,
> `distributed_run1.json`, `distributed_run2.json`, `distributed_run3.json`.

### 5.1 Tóm tắt workload

- Mỗi run: upload 5.000 files × 1 MiB = 5.000 MiB.
- Tham số chung: `--threads 8`, `--file-size 1MB`.

### 5.2 Kết quả chi tiết

Stand-alone runs:

- `standalone_run1.json`: duration 26.2858 s — throughput 190.22 MiB/s — avg latency 41.41 ms — p95 78.70 ms — p99 90.20 ms
- `standalone_run2.json`: duration 36.6154 s — throughput 136.55 MiB/s — avg latency 57.80 ms — p95 103.65 ms — p99 131.17 ms
- `standalone_run3.json`: duration 55.2215 s — throughput 90.54 MiB/s — avg latency 87.61 ms — p95 134.69 ms — p99 204.85 ms

Distributed runs:

- `distributed_run1.json`: duration 377.7877 s — throughput 13.23 MiB/s — avg latency 603.56 ms — p95 850.16 ms — p99 1103.60 ms
- `distributed_run2.json`: duration 324.3346 s — throughput 15.42 MiB/s — avg latency 518.15 ms — p95 615.33 ms — p99 691.10 ms
- `distributed_run3.json`: duration 321.5615 s — throughput 15.55 MiB/s — avg latency 513.76 ms — p95 599.01 ms — p99 649.37 ms

Aggregate (mean) across runs:

- Standalone average throughput ≈ 139.78 MiB/s
- Distributed average throughput ≈ 14.07 MiB/s
- Standalone average latency ≈ 62.94 ms
- Distributed average latency ≈ 545.82 ms
- Success rate: 100% for all runs (total failures = 0)

### 5.3 Phân tích

- Hiệu năng: `standalone` nhanh hơn `distributed` ~9–10× về throughput trong môi trường thử nghiệm này. Nguyên nhân:
  - `distributed` chịu overhead mạng nội bộ, phân tán shards/erasure coding, và coordination giữa node.
  - Trên single-host Docker, I/O vật lý bị chia sẻ; standalone ghi trực tiếp trên một node nên ít overhead.

- Độ trễ: latency trung bình `distributed` ~0.5s; `standalone` ~0.06s — phản ánh chi phí phân mảnh/encode và truyền nội bộ.

- Ổn định: tất cả run hoàn tất với success rate 100% — script và cấu hình bucket hoạt động ổn định.

- Biến thiên: sự khác nhau giữa các run (ví dụ `standalone_run1` nhanh hơn `standalone_run3`) cho thấy host load/background I/O ảnh hưởng tới kết quả; cần nhiều lần chạy để tính confidence.

### 5.4 Kịch bản hỗn loạn (tóm tắt phương pháp và mong đợi)

- Quy trình khuyến nghị (thực hiện khi muốn đo mức chịu lỗi):
  1. Khởi một run `distributed` đang upload.
  2. Trong khi chạy, kill một node (`docker rm -f minio3`) và quan sát latency/throughput: mong thấy spike latency và một số retry nhưng cluster vẫn phục vụ nếu shards đủ.
  3. Khởi lại node, theo dõi Grafana/Prometheus cho spike I/O do heal/rebuild.

- Kết quả mong đợi: hệ thống chịu được mất 1 node (tùy cấu hình erasure); mất 2 node có thể vượt quá khả năng khôi phục tùy profile erasure coding.

### 5.5 Kết luận & khuyến nghị

- Trong môi trường lab (single-host Docker), distributed MinIO thể hiện rõ lợi thế về durability/availability nhưng có chi phí hiệu năng đáng kể so với standalone.
- Để có số liệu sản xuất chính xác, cần chạy trên multi-host với storage riêng biệt, lặp lại nhiều run và thu log/dashboard để phân tích.
- Hành động tiếp theo: đính kèm các JSON run và ảnh Grafana vào báo cáo, chạy các biến thể (thay đổi threads, kích thước file, profile erasure) và tự động hoá chaos tests.


## Chương 6: Tổng kết và Bảng phân công

### 6.1 Bài học kinh nghiệm

- Erasure coding là một giải pháp rất hiệu quả về mặt lưu trữ so với replication, nhưng cần cân nhắc trade-off về rebuild cost và degraded read overhead.
- Containerization (Docker Compose) giúp dựng môi trường reproducible nhanh chóng, nhưng để đo đạc chính xác network/distributed behavior cần chạy trên multi-host hoặc Kubernetes với PVs.
- Giám sát (Prometheus + Grafana) là công cụ không thể thiếu để hiểu hành vi hệ thống trong thời gian thực khi test load và khi inject failure.
- Việc tách credentials và không dùng root trong workloads là thực hành bảo mật quan trọng.

### 6.2 Hướng phát triển tương lai

- Nâng cấp lab lên Kubernetes (StatefulSets + PV + StorageClass) để kiểm tra behavior thật sự của cluster cross-node.
- Tự động hóa chaos tests và thu thập báo cáo (script kill/recreate nodes, xác nhận file integrity, đo thời gian rebuild).
- Mở rộng đo lường: so sánh nhiều profiles erasure (k/m) và replication, phân tích chi phí storage vs rebuild time.
- Tích hợp ELK/Opensearch để phân tích logs chi tiết và correlation với metrics.

### Bảng phân công (mẫu)

- Project Lead: Phan viên chức (quản lý schedule, review report)
- Infra Engineer: chuẩn bị `infra/docker-compose.yml`, mapping volumes, cấu hình Prometheus/Grafana
- Devs: viết `load_generator.py`, `verify_checksum.py`, unit tests
- QA: thực thi benchmark, chaos tests, thu và biên tập logs vào báo cáo


---

*Ghi chú:* file này là bản thảo báo cáo tổng hợp dựa trên cấu trúc và nội dung hiện có trong workspace. Để hoàn thiện báo cáo in/submit, cần thu thập và đính kèm:

- Kết quả thực tế từ runs (`distributed_run1.json`, `distributed_run2.json`, ...)
- Ảnh chụp màn hình terminal cho lệnh `docker compose up -d` và `docker compose ps`
- Dashboard Grafana screenshots
- Log rebuild/repair từ MinIO (`docker logs`)


