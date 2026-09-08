# Validation Load Generator của Member 2 - Tuần 4

## Trạng thái

- Branch sửa: `fix/member2-week4-load-generator`.
- Baseline Member 2: `7d0dca9`.
- Baseline `develop` đã merge vào branch fix: `ae47ee6`.
- Source commit được kiểm thử: `490cbe1805dc8017210d7547900d575a34cc9e91`.
- Ngày chạy runtime cuối: 22/08/2026 theo giờ Việt Nam.
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
- CLI chặn workload có payload đồng thời vượt `512 MiB`, được tính bằng
  `min(threads, num_files) * file_size`. Guard này ngăn trường hợp hợp lệ theo
  tổng dung lượng nhưng có nguy cơ làm laptop hết RAM.
- `latency_ms` chỉ đo S3 upload, bao gồm retry/backoff nếu có nhưng không bao
  gồm thời gian tạo payload bằng `os.urandom()`.
- JSON report có timestamp ISO 8601 UTC, branch, commit, dirty state, endpoint,
  bucket, topology, workload, latency, throughput, success/failure rate, tổng
  RAM và dung lượng đĩa của host.

## Static verified

Các lệnh kiểm tra:

~~~powershell
python -m py_compile scripts/load_generator.py
python scripts/load_generator.py --help
python scripts/load_generator.py `
  --num-files 0 `
  --threads 4 `
  --file-size 1KB
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/load_generator.py `
  --num-files 10 `
  --threads 10 `
  --file-size 1GB
~~~

Kết quả:

- `py_compile`: pass.
- `--help`: pass và hiển thị đầy đủ CLI.
- `--num-files 0`: bị argparse từ chối.
- Workload `10 x 1 GiB` với 10 thread bị từ chối vì payload đồng thời vượt
  `512 MiB`; script chưa cấp phát payload.
- `git diff --check`: pass sau khi sửa trailing whitespace.
- `12/12` unit test pass.
- Unit test xác nhận HTTP 500/429 là transient, HTTP 403/404 không retry,
  HTTP 500 exhaust đúng ba attempt và HTTP 403 dừng sau attempt đầu.
- CI đã được bổ sung `py_compile` và `unittest` bên cạnh Compose validation.

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
  --output "$env:TEMP\week4-smoke-results.json"
~~~

Kết quả:

- Tổng thời gian: `1,2548 giây`.
- Throughput ứng dụng: `79,6930 MiB/s`.
- Thành công: `100/100`.
- Thất bại: `0`.
- Average S3 upload latency: `97,3589 ms`.
- P95: `173,6487 ms`.
- P99: `199,3936 ms`.
- Report ghi commit `490cbe1` và `working_tree_dirty: false`.
- Prefix 100 object đã được xóa; kiểm tra lại không còn object trong prefix.

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
- Tổng thời gian: `25,6774 giây`.
- Throughput ứng dụng: `19,0160 MiB/s`.
- Thành công: `5.000/5.000`.
- Thất bại: `0`.
- Success rate: `100%`.
- Average S3 upload latency: `40,8964 ms`.
- P95: `75,5691 ms`.
- P99: `102,8179 ms`.
- Không request nào phải retry.
- Payload đồng thời theo cấu hình chỉ là `819.200 byte`, dưới guard `512 MiB`.

Resource snapshot trong lúc tải:

- MinIO CPU cao nhất khoảng `101,18%`, phù hợp limit 1 CPU/node.
- MinIO RAM cao nhất khoảng `484,6 MiB/1 GiB`, tương đương `47,33%`.
- Nginx cao nhất khoảng `10,00% CPU`, `4,332 MiB/256 MiB`.
- Prometheus cao nhất trong các snapshot khoảng `53,07 MiB/512 MiB`.
- Grafana cao nhất trong các snapshot khoảng `49,14 MiB/512 MiB`.

Observability:

- Query range đúng khoảng chạy ghi nhận inbound traffic cao nhất khoảng
  `6.811.067 byte/second`.
- `PutObject` request rate cao nhất trong cùng query range khoảng
  `68,65 request/second`.
- Bốn series `up{job="minio-node"}` đều bằng `1`.
- Nginx, Prometheus và Grafana đều trả HTTP `200` sau full load.
- Prefix được đếm đủ `5.000` object trước cleanup và `0` object sau cleanup.

## JSON evidence

`benchmark_results.json` chứa kết quả full load. Report ghi:

- branch `fix/member2-week4-load-generator`;
- commit source `490cbe1805dc8017210d7547900d575a34cc9e91`;
- `working_tree_dirty: false` tại thời điểm đo;
- endpoint, bucket, topology, workload và payload đồng thời;
- host Windows 11, 20 logical CPU, `15,64 GiB` RAM, đĩa `250 GiB` và
  `23,91 GiB` trống tại thời điểm chạy.

Dirty state được lấy trước khi ghi đè file report. Vì vậy giá trị `false` chứng
minh source được benchmark khớp commit trên, còn file JSON trở thành thay đổi
working tree sau khi phép đo hoàn tất là hành vi dự kiến.

## Not executed

- Không chạy 5.000 object × 1 MiB vì sẽ tạo 5 GiB logical payload và tăng thêm
  dung lượng vật lý do Erasure Coding. Workload 5.000 × 100 KiB đủ để xác minh
  concurrency, metrics và giới hạn tài nguyên của Tuần 4.
- Không coi kết quả này là benchmark so sánh standalone và distributed; nội dung
  so sánh thuộc Tuần 5.
- Không kiểm tra checksum; đó là nhiệm vụ Member 3.

## Kết luận

Load generator đã đạt yêu cầu source và runtime Tuần 4 trên branch fix. Không còn
blocker hardcode credential, dependency, retry quá rộng, memory guard hoặc
evidence từ source dirty. Branch fix đã tồn tại trên remote; source final đã
được commit, nhưng chưa merge vào `develop` tại thời điểm cập nhật tài liệu.
