# Week 1 Data Generator Validation

## Phạm vi

Tài liệu này ghi lại bằng chứng chạy `scripts/generate_data.py`. Dataset sinh ra không được commit vì có thể tái tạo từ source và đã nằm trong `.gitignore` tại `scripts/sample_data/`.

## Lệnh kiểm tra đã thực hiện

```powershell
python scripts/generate_data.py --help
```

Kết quả:

```text
Not executed successfully
python.exe could not be accessed by the system.
```

Đã kiểm tra thêm Python launcher:

```powershell
py --version
```

Kết quả:

```text
py was not found
```

Vì máy kiểm thử hiện chỉ trỏ `python.exe` tới Windows Store alias và không có Python interpreter hoạt động, chưa thể chạy script để tạo dataset. Do đó chưa có exit code 0 hoặc số liệu runtime để ghi nhận. Kết quả hiện tại phải được đánh dấu là `Not executed`, không phải `Passed`.

## Profile dự kiến từ source inspection

Các giá trị dưới đây được đọc từ default arguments trong `scripts/generate_data.py`; đây không phải kết quả của một lần chạy runtime:

- `system_logs.log`: mục tiêu khoảng 30 MiB.
- `user_data.csv`: mục tiêu khoảng 30 MiB.
- `dummy_images`: 100 file binary × 200 KiB, khoảng 19.5 MiB.
- Tổng mục tiêu: khoảng 79.5 MiB.

Script tăng kích thước log và CSV cho đến khi đạt mục tiêu; binary được tạo bằng `os.urandom` theo đúng số lượng và kích thước truyền vào. Kích thước hiển thị trên hệ điều hành có thể khác nhẹ do cách quy đổi MB/MiB.

## Dependency

Theo `scripts/requirements.txt`, script cần:

- `faker`
- `tqdm`

Các package `boto3` và `python-dotenv` cũng được khai báo cho các bước data pipeline khác của Member 2, nhưng không được import trực tiếp trong `generate_data.py` hiện tại.

## Cách chạy lại sau khi cài Python

Từ thư mục root của repository:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r scripts\requirements.txt
python scripts\generate_data.py
```

Để kiểm thử nhanh và tránh tạo khoảng 80 MiB ngay lần đầu:

```powershell
python scripts\generate_data.py `
  --output-dir .\scripts\sample_data_validation `
  --log-size-mb 1 `
  --csv-size-mb 1 `
  --binary-count 5 `
  --binary-size-kb 20
```

Sau khi chạy, cần ghi lại output thực tế, exit code và kích thước bằng lệnh:

```powershell
Get-ChildItem .\scripts\sample_data_validation -Recurse -File |
  Select-Object FullName, Length
```

Thư mục kiểm thử này không thuộc deliverable tài liệu; cần xóa sau khi đo hoặc bảo đảm nó không được Git theo dõi.

## Kết luận hiện tại

- Source script và default profile phù hợp mục tiêu dataset Tuần 1.
- Dataset output nằm trong vùng ignore theo cấu hình hiện tại.
- Chưa có bằng chứng runtime trên môi trường này vì Python interpreter không khả dụng.
- Thành viên 2 cần chạy lại các lệnh trên một máy có Python hoạt động, sau đó cập nhật số liệu thật vào tài liệu này trước khi tạo PR.
