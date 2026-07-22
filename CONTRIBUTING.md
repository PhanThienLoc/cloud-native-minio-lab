# Hướng dẫn đóng góp (Contributing Guidelines)

Cảm ơn các thành viên đã tham gia vào dự án **cloud-native-minio-lab**. Để đảm bảo chất lượng mã nguồn và sự đồng bộ trong quá trình phát triển, vui lòng tuân thủ các quy định dưới đây.

## 1. Quy tắc phân nhánh (Branching Strategy)

Chúng ta sử dụng mô hình **Gitflow** đơn giản hóa:

- **`main`**: Nhánh ổn định, chứa code đã được kiểm thử và sẵn sàng để nộp/bảo vệ. Chỉ merge từ `develop` vào đây khi hoàn thành một mốc quan trọng (Milestone).
- **`develop`**: Nhánh tích hợp chính. Mọi tính năng mới sẽ được merge vào đây trước.
- **`feat/<ten-tinh-nang>`**: Nhánh phát triển tính năng mới (Ví dụ: `feat/minio-cluster-setup`).
- **`fix/<ten-loi>`**: Nhánh sửa lỗi (Ví dụ: `fix/docker-network-issue`).
- **`docs/<noi-dung>`**: Nhánh cập nhật tài liệu, báo cáo hoặc slide.

> **Lưu ý:** Tuyệt đối không commit trực tiếp lên nhánh `main` hoặc `develop`. Luôn tạo Pull Request (PR) để được review.

## 2. Quy tắc đặt tên Commit Message

Sử dụng chuẩn **Conventional Commits** để lịch sử git rõ ràng và chuyên nghiệp. Cấu trúc:

```text
<type>: <subject>

[optional body]

[optional footer]
```

### Các loại Type phổ biến:
- **`feat`**: Thêm tính năng mới (Ví dụ: thêm script load generator).
- **`fix`**: Sửa lỗi (Ví dụ: sửa lỗi kết nối boto3).
- **`docs`**: Thay đổi tài liệu, README, báo cáo.
- **`style`**: Định dạng code, thêm khoảng trắng, dấu chấm phẩy (không ảnh hưởng logic).
- **`refactor`**: Tái cấu trúc code (không thêm tính năng mới, không sửa lỗi).
- **`test`**: Thêm hoặc sửa kịch bản kiểm thử.
- **`chore`**: Các tác vụ bảo trì, cập nhật dependencies, cấu hình CI/CD.

### Ví dụ Commit đúng chuẩn:
✅ `feat: add multi-threaded data ingestion script`
✅ `fix: resolve MinIO connection timeout in docker-compose`
✅ `docs: update architecture diagram for Week 2`
✅ `chore: update requirements.txt with new dependencies`

### Ví dụ Commit cần tránh:
❌ `update code`
❌ `fix bug`
❌ `done`
❌ `abc`

## 3. Quy trình làm việc (Workflow)

1. **Pull**: Luôn `git pull origin develop` trước khi tạo nhánh mới để đảm bảo code mới nhất.
2. **Branch**: Tạo nhánh mới từ `develop`: `git checkout -b feat/ten-tinh-nang`.
3. **Commit**: Commit thường xuyên với message rõ ràng.
4. **Push**: Đẩy nhánh lên remote: `git push origin feat/ten-tinh-nang`.
5. **Pull Request (PR)**: Tạo PR từ nhánh của bạn vào `develop`. 
   - Mô tả rõ ràng những gì đã thay đổi.
   - Yêu cầu ít nhất 1 thành viên khác review trước khi merge.
6. **Merge**: Sau khi được approve, tiến hành merge và xóa nhánh cũ.

## 4. Tiêu chuẩn mã nguồn (Code Standards)

- **Python**: Tuân thủ PEP 8. Sử dụng `black` hoặc `flake8` để format code trước khi commit.
- **YAML/Docker**: Đảm bảo thụt lề (indentation) nhất quán (2 hoặc 4 spaces).
- **Bảo mật**: 
  - **TUYỆT ĐỐI KHÔNG** commit file `.env` chứa mật khẩu thật.
  - Sử dụng file `.env.example` làm mẫu.
  - Không hardcode Access Key/Secret Key trong source code.

## 5. Xử lý xung đột (Conflict Resolution)

Nếu gặp conflict khi merge:
1. Không panic.
2. Pull code mới nhất về máy.
3. Giải quyết conflict thủ công, ưu tiên giữ lại logic đúng.
4. Test lại hệ thống sau khi giải quyết xong.
5. Commit và push lại.

---
*Cùng nhau xây dựng một sản phẩm Cloud Native chất lượng cao!*