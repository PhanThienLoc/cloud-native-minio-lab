# Phân tích CAP, NFS và MinIO trong kiến trúc Cloud Native

## 1. Cách áp dụng CAP Theorem đúng phạm vi

CAP Theorem chỉ đặt ra lựa chọn khi một hệ thống phân tán thật sự gặp network
partition. Khi partition xảy ra, hệ thống không thể đồng thời bảo đảm tuyệt đối
cả consistency và availability cho mọi request. CAP không nói rằng một sản phẩm
luôn chỉ thuộc một chữ cái, cũng không dùng để so tốc độ giữa hai hệ thống.

NFS truyền thống thường có một server hoặc một control point phục vụ namespace
POSIX cho nhiều client. Nếu client mất đường mạng tới server, dữ liệu có thể còn
nguyên nhưng dịch vụ không truy cập được. Vì vậy NFS tập trung không phải một ví
dụ đối xứng để gắn nhãn `CP` hoặc `AP` như một database replicated; đặc tính nổi
bật trong bài toán này là single point of failure và giới hạn scale-up.

MinIO trong dự án là một storage pool distributed gồm tám drive endpoint. MinIO
dùng quorum và Erasure Coding để bảo vệ object. Khi vẫn còn đủ quorum, cluster
có thể tiếp tục phục vụ các thao tác phù hợp; khi mất write quorum, việc từ chối
ghi an toàn tốt hơn chấp nhận hai trạng thái mâu thuẫn. Do đó cách diễn đạt bảo
vệ được là: MinIO ưu tiên tính nhất quán của object thông qua quorum, còn mức
availability thực tế phụ thuộc số drive khỏe, parity và loại thao tác. Nginx chỉ
phân phối request, không tạo quorum hay redundancy.

## 2. So sánh NFS và MinIO

| Tiêu chí | File Storage/NFS | Object Storage/MinIO |
| --- | --- | --- |
| Mô hình truy cập | File, thư mục, POSIX-like | Object qua HTTP/S3 API |
| Namespace | Phân cấp thư mục | Bucket + object key, có thể mô phỏng prefix |
| Metadata | Thuộc tính file tương đối cố định | Custom metadata gắn với từng object |
| Cập nhật dữ liệu | Phù hợp sửa file tại chỗ | Thường thay toàn object hoặc multipart |
| Mở rộng | Thường scale-up server/storage | Thiết kế cho scale-out storage pool |
| Chịu lỗi trong lab | Phụ thuộc server tập trung | Quorum + Erasure Coding trên 8 drive |
| Client Cloud Native | Cần mount/state ở client | S3 API, client tương đối stateless |
| Trường hợp phù hợp | Shared filesystem, POSIX workload | Data lake, backup, media, log, ML artifact |

NFS vẫn phù hợp khi ứng dụng cần semantics file system, file locking, cập nhật
ngẫu nhiên tại chỗ hoặc latency thấp trên mạng nội bộ. Object Storage không
“thắng” trong mọi trường hợp; nó phù hợp hơn cho bài toán Cloud Native/Data Lake
vì API chuẩn, flat namespace, metadata phong phú, khả năng scale-out và mô hình
object ít phụ thuộc filesystem của host.

## 3. Vì sao Object Storage phù hợp Data Lake

1. S3 API tách ứng dụng khỏi vị trí volume và hệ điều hành của storage node.
2. Object key có thể tổ chức theo Hive-style partition như
   `data_type/year/month/day`, hỗ trợ engine phân tích lọc partition.
3. Custom metadata giúp lưu nguồn dữ liệu, thời gian ingest và loại dữ liệu cùng
   object.
4. Multipart/concurrent upload phù hợp file lớn và pipeline song song.
5. Erasure Coding cung cấp redundancy hiệu quả dung lượng hơn nhiều full replica
   trong cùng một pool.
6. Prometheus/Grafana có thể quan sát request rate, throughput, dung lượng, object
   count và node health mà không phụ thuộc vào từng client.

Trong lab này, full load 4 node đã upload thành công 5.000/5.000 object với source
sạch. Kết quả đó chứng minh pipeline và khả năng quan sát dưới tải, nhưng chưa
chứng minh production scalability vì bốn container vẫn dùng chung một host,
Docker daemon, CPU, RAM, disk và failure domain.

## 4. Hướng phát triển tương lai

### 4.1. Hạ tầng đa máy và Kubernetes

- Chuyển từ một Docker host sang tối thiểu bốn storage host độc lập.
- Dùng Kubernetes StatefulSet/Operator phù hợp, Persistent Volume trên failure
  domain khác nhau, Pod Anti-Affinity và PodDisruptionBudget.
- Tách Nginx/API gateway thành nhiều replica và dùng external load balancer.
- Đo network latency, disk IOPS và healing trong điều kiện đa host thật.

### 4.2. Bảo mật và quản trị dữ liệu

- Bật TLS end-to-end, rotate secret và tích hợp external identity provider.
- Tách application credential khỏi root credential, áp dụng least privilege.
- Tích hợp KMS, server-side encryption, Object Lock và audit log.
- Hoàn thiện Versioning, Lifecycle và replication giữa site/cluster.

### 4.3. Observability và vận hành

- Thêm alert cho node down, quorum risk, disk usage và S3 error rate.
- Tập trung log, liên kết metric với chaos event và lưu dashboard snapshot.
- Tự động hóa benchmark/chaos trong môi trường kiểm thử có kiểm soát.

### 4.4. AI/ML Data Pipeline

- Đưa dữ liệu thô vào `raw-data`, xử lý bằng Spark/Trino hoặc job Kubernetes,
  rồi ghi artifact vào `processed-data`.
- Dùng bucket event đưa message vào queue để kích hoạt validation, feature
  extraction hoặc model training.
- Quản lý dataset/model bằng versioning, checksum và metadata lineage.

## 5. Giới hạn khi trình bày

- Không gọi bốn container trên một laptop là bốn failure domain độc lập.
- Không khẳng định “mất một node luôn ghi được” nếu chưa kiểm tra đúng object và
  quorum runtime.
- Không dùng baseline 4 node Tuần 4 làm kết luận Standalone-vs-Distributed; hai
  topology phải chạy cùng workload, host, resource limit và số lần lặp.
- Không gắn nhãn CAP tuyệt đối cho NFS hoặc MinIO mà bỏ qua loại failure và thao
  tác read/write.
