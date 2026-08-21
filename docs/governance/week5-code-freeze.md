# Code Freeze Tuần 5

## Trạng thái

- Trạng thái: `ACTIVE`.
- Ngày hiệu lực: 22/08/2026.
- Baseline: `develop` tại `2245087` sau PR #13.
- Người quyết định ngoại lệ: Nhóm trưởng.

Code Freeze đánh dấu thời điểm dự án chuyển từ phát triển tính năng sang ổn định,
đo lường và chuẩn bị bảo vệ. Nó không có nghĩa là ngừng sửa lỗi; nó ngăn thay đổi
không cần thiết làm sai benchmark hoặc tạo regression trước demo.

## Thay đổi được phép

- `fix:` sửa lỗi có thể tái hiện và có bằng chứng kiểm thử.
- `docs:` cập nhật runbook, báo cáo, validation và tài liệu thuyết trình.
- Cập nhật evidence từ cùng source/config đã chốt, không thay đổi hành vi hệ thống.

## Thay đổi bị từ chối

- `feat:` hoặc service, endpoint, dependency, dashboard mới.
- Đổi topology, resource limits hoặc workload benchmark sau khi đã bắt đầu so sánh.
- Refactor không phục vụ một lỗi cụ thể.
- Hardcode credential, commit `.env`, dataset hoặc file test dung lượng lớn.
- Push trực tiếp vào `develop` hoặc `main`.

## Cổng kiểm soát trước merge

Mỗi PR sau Code Freeze phải có:

1. Mô tả lỗi hoặc lý do tài liệu cần đổi.
2. Danh sách file và khẳng định phạm vi không mở rộng.
3. Kết quả CI và command runtime liên quan.
4. Kiểm tra secret, `git diff --check` và tài liệu không lệch implementation.
5. Review của Nhóm trưởng trước khi merge vào `develop`.

Hotfix thất bại phải được revert bằng một PR mới; không dùng `git reset --hard`
hoặc force-push để sửa lịch sử chung.

## Điều kiện đưa lên main

Chỉ tạo PR `develop -> main` khi:

- stack khởi động bằng một lệnh Compose;
- validation chức năng, observability và benchmark cần thiết đã có evidence;
- báo cáo/slide không tuyên bố vượt quá kết quả runtime;
- không còn blocker bảo mật hoặc secret bị Git track.
