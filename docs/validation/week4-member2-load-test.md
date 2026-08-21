# Validation Load Generator của Member 2 - Tuần 4

## Trạng thái

- Branch sửa: `fix/member2-week4-load-generator`.
- Baseline Member 2: `7d0dca9`.
- Baseline `develop` đã merge vào branch fix: `ae47ee6`.
- Ngày chạy runtime: 21/08/2026.
- Evidence phân biệt rõ `Source inspected`, `Runtime verified` và
  `Not executed`.

## Source inspected

`scripts/load_generator.py` đã được sửa theo các nguyên tắc sau:

- Endpoint dùng `ENDPOINT_URL`.
- Ưu tiên cặp `AWS_ACCESS_KEY_ID` và `AWS_SECRET_ACCESS_KEY`; nếu không có
  thì dùng cặp MinIO root từ `.env` cho local lab.
- Không còn fallback credential hardcode.
- Đã loại bỏ `numpy`; percentile được tính bằng nội suy tuyến tính bằng Python
  standard library.
- Preflight kiểm tra endpoint, credential và bucket trước khi tạo futures.
- SDK retry bị tắt; script kiểm soát chính xác tối đa ba attempt.
- Chỉ retry lỗi kết nối, timeout, HTTP 408/429, S3 5xx hoặc mã lỗi transient.
- S3 4xx và lỗi lập trình không bị retry.
- Mỗi worker thread tái sử dụng một boto3 client.
- CLI giới hạn tối đa 20.000 object, 128 thread, 1 GiB/object và 10 GiB tổng
  workload cho laptop lab.
- JSON report có timestamp ISO 8601 UTC, branch, commit, dirty state, endpoint,
  bucket, topology, workload, latency, throughput và success/failure rate.

## Static verified

Các lệnh kiểm tra:

~~~powershell
python -m py_compile scripts/load_generator.py
python scripts/load_generator.py --help
python scripts/load_generator.py `
  --num-files 0 `
  --threads 4 `
  --file-size 1KB
~~~

Kết quả:

- `py_compile`: pass.
- `--help`: pass và hiển thị đầy đủ CLI.
- `--num-files 0`: bị argparse từ chối.
- `git diff --check`: pass sau khi sửa trailing whitespace.
- Unit check xác nhận HTTP 500/429 được retry, HTTP 403/404 không retry.
- Unit check percentile P95: pass.

## Runtime verified: failure handling

### Nginx không truy cập được

Nginx được dừng tạm thời, sau đó chạy một object 1 KiB.

Kết quả:

- Attempt 1 thất bại, chờ 0,5 giây.
- Attempt 2 thất bại, chờ 1 giây.
- Attempt 3 thất bại và dừng.
- Exit code: `1`.
- Không có traceback không được xử lý.
- Nginx được khởi động lại trong khối `finally`.
- Health endpoint sau phục hồi: HTTP `200`.

### Credential không hợp lệ

Chạy preflight bằng credential ứng dụng giả.

Kết quả:

- MinIO trả HTTP `403 Forbidden`.
- Log ghi `failed without retry`.
- Exit code: `1`.
- Không có retry warning hoặc traceback.

## Runtime verified: smoke test

Lệnh:

~~~powershell
python scripts/load_generator.py `
  --num-files 100 `
  --threads 8 `
  --file-size 1MB `
  --bucket raw-data `
  --topology distributed-4-node `
  --output benchmark_results.json
~~~

Kết quả:

- Tổng thời gian: `1,0899 giây`.
- Throughput ứng dụng: `91,7519 MiB/s`.
- Thành công: `100/100`.
- Thất bại: `0`.
- Average latency: `84,8074 ms`.
- P95: `126,7907 ms`.
- P99: `135,4518 ms`.
- Prometheus ghi nhận `PutObject` rate khác 0 và bốn node `UP`.
- RAM cao nhất trong snapshot khoảng 17,2% limit của một MinIO node.
- Prefix 100 object đã được xóa sau kiểm thử.

## Runtime verified: full load

Để giới hạn dung lượng trên laptop, full load dùng 100 KiB/object thay vì 1 MiB:

~~~powershell
python scripts/load_generator.py `
  --num-files 5000 `
  --threads 8 `
  --file-size 100KB `
  --bucket raw-data `
  --topology distributed-4-node `
  --output benchmark_results.json
~~~

Kết quả:

- Tổng logical payload: khoảng `488,28 MiB`.
- Tổng thời gian: `25,7703 giây`.
- Throughput ứng dụng: `18,9475 MiB/s`.
- Thành công: `5.000/5.000`.
- Thất bại: `0`.
- Success rate: `100%`.
- Average latency: `41,1419 ms`.
- P95: `84,5289 ms`.
- P99: `110,9209 ms`.
- Không request nào phải retry.

Resource snapshot trong lúc tải:

- MinIO CPU cao nhất khoảng `102%`, phù hợp limit 1 CPU/node.
- MinIO RAM cao nhất khoảng `450,9 MiB/1 GiB`, tương đương `44,03%`.
- Nginx cao nhất khoảng `12,16% CPU`, `4,14 MiB/256 MiB`.
- Prometheus khoảng `49,5 MiB/512 MiB`.
- Grafana khoảng `48,4 MiB/512 MiB`.

Observability:

- Prometheus inbound traffic query: khoảng `10.873.984 byte/second` tại thời
  điểm lấy mẫu.
- `PutObject` request rate: khoảng `100,31 request/second`.
- Bốn series `up{job="minio-node"}` đều bằng `1`.
- Nginx, Prometheus và Grafana đều trả HTTP `200` sau full load.
- Prefix 5.000 object đã được xóa sau kiểm thử.

## JSON evidence

`benchmark_results.json` chứa kết quả full load. Report ghi:

- branch `fix/member2-week4-load-generator`;
- commit baseline `a45938d1cd4449fd06f6f7a304e4e68a8e6ca37d`;
- `working_tree_dirty: true`;
- endpoint, bucket, topology, workload và host context.

`working_tree_dirty: true` là chính xác vì người dùng yêu cầu chưa commit. Sau
khi commit code fix, cần chạy lại workload cuối nếu muốn report gắn với commit
sạch dùng cho benchmark chính thức.

## Not executed

- Không chạy 5.000 object × 1 MiB vì sẽ tạo 5 GiB logical payload và tăng thêm
  dung lượng vật lý do Erasure Coding. Workload 5.000 × 100 KiB đủ để xác minh
  concurrency, metrics và giới hạn tài nguyên của Tuần 4.
- Không coi kết quả này là benchmark so sánh standalone và distributed; nội dung
  so sánh thuộc Tuần 5.
- Không kiểm tra checksum; đó là nhiệm vụ Member 3.

## Kết luận

Load generator đã đạt yêu cầu source và runtime Tuần 4 trên branch fix. Không còn
blocker hardcode credential, dependency hoặc retry quá rộng. Branch chưa được
commit, push hoặc merge trong phiên validation này.
