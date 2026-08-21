# Review Load Generator của Thành viên 2 - Tuần 4

## Phạm vi

- Branch: `feat/week4-load-generator`.
- Commit được review: `7d0dca9`.
- Chế độ: `Review only`; không sửa `/scripts`.

## Kết luận

Branch đã có multi-threading, CLI arguments, dữ liệu sinh trong RAM, latency
average/P95/P99, throughput, success rate và file JSON. Tuy nhiên chưa nên merge
vào `develop` vì còn blocker về bảo mật và dependency.

## Blocker

### 1. Credential fallback bị hardcode

`MINIO_ROOT_USER` và `MINIO_ROOT_PASSWORD` fallback về `minioadmin`. Script phải
dừng với lỗi rõ ràng nếu environment thiếu credential; không được dùng secret mặc
định trong source.

### 2. Thiếu dependency

Script import `numpy`, nhưng `scripts/requirements.txt` không khai báo thư viện
này. Môi trường mới cài từ requirements sẽ lỗi `ModuleNotFoundError`.

## High

### 3. Retry bắt mọi exception

Khối `except (ClientError, EndpointConnectionError, Exception)` tương đương bắt
mọi `Exception`. Lỗi lập trình, cấu hình hoặc quyền truy cập cũng bị retry như lỗi
tạm thời. Chỉ retry network timeout/connection và S3 5xx; lỗi 4xx hoặc bug phải
fail rõ ràng.

### 4. Evidence benchmark chưa đủ ngữ cảnh

`benchmark_results.json` có workload và kết quả nhưng thiếu branch/commit,
endpoint/topology, host CPU/RAM/storage và thời gian dạng ISO 8601. Vì vậy số
`45.29 MB/s` chỉ là output được commit, chưa đủ để so sánh hoặc tái lập.

## Medium

- Tạo một boto3 client mới cho từng object gây overhead không cần thiết; nên tái
  sử dụng client theo worker/thread.
- Chưa validate `num-files > 0`, `threads > 0` và giới hạn kích thước file phù hợp
  laptop.
- Endpoint dùng biến `MINIO_ENDPOINT`, không thống nhất contract `ENDPOINT_URL`
  hiện có trong `.env.example`.
- File log và output JSON luôn ghi ở repository root; nên có `--output` hoặc thư
  mục kết quả rõ ràng và bảo đảm output tạm được ignore khi cần.

## Tiêu chí trước merge

- Không còn fallback credential hardcode.
- Dependency cài được từ `scripts/requirements.txt`.
- Retry chỉ áp dụng cho lỗi transient và tối đa ba attempt.
- Chạy smoke test 100 object trước khi chạy 5.000 object.
- Evidence ghi đủ topology, commit và host resources.
- Quan sát Grafana trong lúc load để xác nhận Throughput và Request Rate thay đổi.
