# Freeze Gates Tuần 5

## Trạng thái

- Infrastructure Freeze: `ACTIVE`.
- Final Code Freeze: `NOT_ACTIVE`.
- Ngày hiệu lực: 22/08/2026.
- Baseline: `develop` tại `2245087` sau PR #13.
- Người quyết định ngoại lệ: Nhóm trưởng.

Infrastructure Freeze khóa distributed baseline đang dùng để đo: bốn MinIO node,
Nginx, Prometheus, Grafana, endpoint, resource limits và cấu hình monitoring. Final
Code Freeze chỉ được kích hoạt sau khi các deliverable bắt buộc còn thiếu đã được
merge và có runtime evidence.

## Phạm vi đã freeze

- Không đổi topology distributed, port, service name, volume hoặc network hiện tại.
- Không đổi resource limits hoặc dashboard/query dùng để đối chiếu benchmark.
- Không thay workload giữa các lần đo được dùng trong cùng một phép so sánh.

## Ngoại lệ roadmap trước Final Freeze

- `fix:` sửa lỗi có thể tái hiện và có bằng chứng kiểm thử.
- `docs:` cập nhật runbook, báo cáo, validation và tài liệu thuyết trình.
- `feat:` chỉ cho deliverable đã tồn tại trong roadmap nhưng chưa được triển khai:
  - Member 2: benchmark tooling có `--mode` và một standalone harness/endpoint thật;
  - Member 3: checksum upload-download, IAM/policy và logical provisioning còn thiếu.
- Standalone harness phải cô lập với distributed baseline. `--topology` hoặc `--mode`
  chỉ ghi nhãn mà không đổi endpoint/deployment thật không được xem là benchmark
  Standalone-vs-Distributed.
- Mỗi ngoại lệ phải được Nhóm trưởng phê duyệt trong PR và dùng đúng loại commit;
  không đổi `feat:` thành `fix:` để lách freeze.

## Thay đổi bị từ chối

- `feat:` ngoài danh sách deliverable tồn đọng ở trên.
- Đổi distributed baseline, resource limits hoặc workload benchmark sau khi đã bắt
  đầu phép so sánh. Standalone harness cô lập thuộc ngoại lệ roadmap ở trên.
- Refactor không phục vụ một lỗi cụ thể.
- Hardcode credential, commit `.env`, dataset hoặc file test dung lượng lớn.
- Push trực tiếp vào `develop` hoặc `main`.

## Blocker trước Final Code Freeze

1. `scripts/load_generator.py` chưa có `--mode`; `--topology` hiện chỉ là nhãn report.
2. Chưa có standalone deployment/harness cô lập để so sánh công bằng với 4 node.
3. `scripts/mc_setup.sh` còn credential fallback hardcode và mới tạo một bucket;
   chưa chứng minh ba bucket, IAM/policy, versioning hoặc lifecycle được provision.
4. `scripts/verify_checksum.py` mới hash file local; chưa upload, tải object ngẫu
   nhiên về, so checksum và báo integrity percentage.
5. Chưa có screenshot Grafana idle/load/cooldown, terminal evidence và video demo.
6. Chưa review/merge các deliverable còn thiếu của Member 3.

Các mục này là trạng thái thực tế cần đóng, không phải bằng chứng hệ thống đã đạt.

## Cổng kiểm soát trước merge

Mỗi PR sau Code Freeze phải có:

1. Mô tả lỗi hoặc lý do tài liệu cần đổi.
2. Danh sách file và khẳng định phạm vi không mở rộng.
3. Kết quả CI và command runtime liên quan.
4. Kiểm tra secret, `git diff --check` và tài liệu không lệch implementation.
5. Review của Nhóm trưởng trước khi merge vào `develop`.

Hotfix thất bại phải được revert bằng một PR mới; không dùng `git reset --hard`
hoặc force-push để sửa lịch sử chung.

## Điều kiện kích hoạt Final Code Freeze

- Các blocker trên đã có source review và runtime evidence.
- Benchmark 1 node và 4 node chạy trên topology thật, cùng workload và điều kiện host.
- Security audit không còn credential hardcode hoặc secret được Git track.
- Nhóm trưởng công bố baseline Final Code Freeze mới trên `develop`.

Sau mốc đó chỉ nhận `fix:` và `docs:`. Mọi thay đổi tính năng mới phải chờ freeze
được gỡ hoặc một milestone sau.

## Điều kiện đưa lên main

Chỉ tạo PR `develop -> main` khi:

- infrastructure stack khởi động bằng một lệnh Compose;
- nếu tuyên bố complete-system bootstrap thì bucket, IAM, versioning và lifecycle
  cũng phải được tự provision và có evidence;
- validation chức năng, observability và benchmark cần thiết đã có evidence;
- báo cáo/slide không tuyên bố vượt quá kết quả runtime;
- không còn blocker bảo mật hoặc secret bị Git track.
