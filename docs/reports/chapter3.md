# CHƯƠNG 3: THIẾT KẾ KIẾN TRÚC HỆ THỐNG VÀ LUỒNG DỮ LIỆU

## 3.1. Tổng quan kiến trúc hệ thống

Hệ thống được thiết kế theo mô hình Cloud-Native Data Lake sử dụng MinIO Object Storage làm lớp lưu trữ trung tâm. Kiến trúc gồm Nginx Load Balancer, cụm MinIO gồm 4 node, các dịch vụ giám sát Prometheus và Grafana, cùng các bucket phục vụ lưu trữ dữ liệu.

Nginx đóng vai trò Load Balancer, tiếp nhận các request từ client và phân phối đến cụm MinIO. Cụm MinIO gồm 4 node hoạt động phối hợp nhằm cung cấp khả năng lưu trữ phân tán, chịu lỗi và đảm bảo tính sẵn sàng của dữ liệu.

Các bucket chính của hệ thống gồm:

- raw-data: lưu trữ dữ liệu thô từ nguồn dữ liệu.
- processed-data: lưu trữ dữ liệu sau xử lý.
- system-logs: lưu trữ log hệ thống.

Kiến trúc tổng thể:

Client
   |
   v
Nginx Load Balancer
   |
   v
+-----------------------------+
|       MinIO Cluster         |
|                             |
| MinIO 1   MinIO 2           |
| MinIO 3   MinIO 4           |
|                             |
|      Erasure Coding          |
+-----------------------------+
   |
   +---- raw-data
   |
   +---- processed-data
   |
   +---- system-logs

## 3.2. Kiến trúc MinIO Cluster

Hệ thống sử dụng 4 container MinIO tương ứng với 4 node trong cluster. Các node được triển khai bằng Docker Compose và hoạt động như một cụm MinIO phân tán.

Qua quá trình kiểm thử, cả 4 node đều ở trạng thái healthy và có khả năng kết nối với nhau. Hệ thống có tổng cộng 8 drive và sử dụng Erasure Coding với EC:4.

Việc sử dụng MinIO Cluster giúp dữ liệu được phân phối trên nhiều node thay vì phụ thuộc vào một máy chủ duy nhất. Khi xảy ra sự cố ở một thành phần, hệ thống có khả năng tiếp tục hoạt động trong phạm vi chịu lỗi của cấu hình Erasure Coding.

## 3.3. Luồng dữ liệu

Luồng dữ liệu của hệ thống được thực hiện theo các bước:

1. Client hoặc Data Ingestion Pipeline tạo request upload dữ liệu.
2. Request được gửi đến Nginx Load Balancer.
3. Nginx phân phối request đến MinIO Cluster.
4. MinIO tiếp nhận object và xác định bucket cùng object key.
5. Object được lưu trữ phân tán trong MinIO Cluster.
6. Erasure Coding phân phối dữ liệu và parity trên các drive.
7. Metadata của object được lưu cùng với object để phục vụ việc quản lý và truy xuất.

Luồng dữ liệu:

Client
  |
  v
Data Ingestion Pipeline
  |
  v
Nginx Load Balancer
  |
  v
MinIO Cluster
  |
  v
Erasure Coding
  |
  +--> MinIO Node 1
  +--> MinIO Node 2
  +--> MinIO Node 3
  +--> MinIO Node 4

## 3.4. Data Lake và Hive-style Partitioning

Để tổ chức dữ liệu theo chuẩn Data Lake, hệ thống sử dụng cấu trúc Hive-style Partitioning.

Object key được tổ chức theo dạng:

raw-data/data_type/year=2026/month=08/day=05/filename.ext

Trong đó:

- data_type xác định loại dữ liệu.
- year xác định năm.
- month xác định tháng.
- day xác định ngày.
- filename.ext là tên file dữ liệu.

Cách tổ chức này giúp dữ liệu được phân vùng rõ ràng theo thời gian. Các hệ thống xử lý dữ liệu lớn như Apache Spark, Presto hoặc Athena có thể sử dụng partition pruning để chỉ đọc những partition cần thiết thay vì quét toàn bộ bucket.

## 3.5. Identity and Access Management

Hệ thống áp dụng mô hình Identity and Access Management (IAM) theo nguyên tắc Least Privilege.

Ba policy được xây dựng:

### Admin Policy

admin-policy cung cấp toàn quyền thao tác với S3:

- s3:*

Policy này được gán cho admin-user.

### Developer Policy

dev-policy chỉ cho phép thao tác trên bucket raw-data với các quyền:

- GetBucketLocation
- ListBucket
- GetObject
- PutObject
- DeleteObject

Policy này được gán cho dev-user.

### Read-only Policy

readonly-policy chỉ cho phép đọc dữ liệu, bao gồm:

- GetBucketLocation
- ListAllMyBuckets
- ListBucket
- GetObject

Policy này được gán cho readonly-user.

Bảng phân quyền:

| User | Policy | Quyền |
|---|---|---|
| admin-user | admin-policy | Toàn quyền |
| dev-user | dev-policy | Đọc/ghi/xóa raw-data |
| readonly-user | readonly-policy | Chỉ đọc |

Cơ chế này đảm bảo mỗi tài khoản chỉ được cấp những quyền cần thiết cho vai trò của mình.

## 3.6. Kiểm thử IAM

Hệ thống được kiểm thử bằng cách sử dụng credentials của readonly-user để thực hiện thao tác upload file vào bucket raw-data.

Kết quả:

mc cp test.txt readonly/raw-data/

Hệ thống trả về lỗi:

Insufficient permissions to access this path

Điều này chứng minh readonly-user không có quyền PutObject và nguyên tắc Least Privilege được áp dụng thành công.

## 3.7. Versioning

Bucket raw-data được bật tính năng Versioning.

Cấu hình được kiểm tra bằng lệnh:

mc version info myminio/raw-data

Kết quả xác nhận:

myminio/raw-data versioning is enabled

Versioning giúp duy trì nhiều phiên bản của object khi object bị cập nhật hoặc ghi đè. Cơ chế này hỗ trợ khôi phục dữ liệu và giảm rủi ro mất dữ liệu do thao tác nhầm.

## 3.8. Lifecycle Management

Bucket system-logs được cấu hình Lifecycle Management với thời gian hết hạn 30 ngày.

Cấu hình được kiểm tra bằng:

mc ilm rule ls myminio/system-logs

Kết quả:

- Status: Enabled
- Days to Expire: 30

Cơ chế Lifecycle giúp hệ thống tự động loại bỏ dữ liệu log cũ, hạn chế việc sử dụng dung lượng lưu trữ không cần thiết và hỗ trợ tối ưu chi phí vận hành.

## 3.9. Khả năng chịu lỗi và bảo vệ dữ liệu

Hệ thống sử dụng MinIO Distributed với 4 node và Erasure Coding. Dữ liệu không phụ thuộc vào một node duy nhất mà được phân phối trên nhiều drive.

Kết quả kiểm tra cluster cho thấy:

- 4/4 node MinIO hoạt động.
- 8/8 drive online.
- Erasure Coding: EC:4.
- Network: 4/4 OK.

Kiến trúc này nâng cao khả năng chịu lỗi của hệ thống và đảm bảo dữ liệu vẫn có thể được truy cập trong trường hợp một số thành phần gặp sự cố.

## 3.10. Kết luận chương

Chương này đã trình bày thiết kế kiến trúc Cloud-Native Data Lake sử dụng MinIO Cluster. Hệ thống kết hợp Nginx Load Balancer, MinIO Distributed, Erasure Coding, IAM, Versioning và Lifecycle Management.

Kiến trúc đáp ứng các yêu cầu về lưu trữ phân tán, bảo mật truy cập, quản lý phiên bản, tự động quản lý vòng đời dữ liệu và khả năng chịu lỗi. Đây là nền tảng để triển khai Data Ingestion Pipeline và các thành phần xử lý dữ liệu trong các giai đoạn tiếp theo.