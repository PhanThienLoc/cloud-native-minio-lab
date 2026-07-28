# MinIO Erasure Coding and Sharding

## 1. Khái niệm chính

MinIO lưu object theo mô hình object storage. Client gửi một object thông qua S3 API; MinIO chọn erasure set phù hợp rồi chia object thành nhiều shard để ghi lên các drive trong set. Một shard có thể là data shard hoặc parity shard.

MinIO mô tả kích thước erasure set theo công thức:

```text
N = K + M
```

- `K`: số data shard.
- `M`: số parity shard.
- `N`: tổng số shard trong erasure set.

Parity được tạo bằng Reed-Solomon Erasure Coding. Khi một số shard bị mất nhưng vẫn còn đủ read quorum, MinIO có thể dùng các shard còn lại để đọc object hoặc tái tạo shard bị mất. Giá trị `M` không nên được suy đoán chỉ từ số container; cần kiểm tra cấu hình và runtime thực tế bằng công cụ quản trị MinIO.

Tham khảo: [MinIO Erasure Coding](https://min.io/docs/minio/linux/operations/concepts/erasure-coding.html).

## 2. Vì sao dự án chọn 4 node × 2 volume

Topology của lab có:

```text
4 node MinIO × 2 volume/node = 8 endpoint lưu trữ
```

Trong Compose, mỗi node dùng hai đường dẫn riêng `/data1` và `/data2`. Các endpoint được truyền cho mọi node bằng command distributed mode:

```text
server http://minio{1...4}/data{1...2}
```

Thiết kế này có ba ý nghĩa:

1. Có nhiều endpoint để MinIO khởi tạo một storage pool distributed thay vì bốn server standalone.
2. Có thể minh họa việc dữ liệu và parity được phân bố trên nhiều endpoint.
3. Có đủ thành phần để thực hiện kiểm thử mất node, healing và benchmark trong các tuần sau.

Con số `4 node × 2 volume` là topology của bài lab, không tự động có nghĩa là mọi object đều có một tỷ lệ data/parity cố định. Tỷ lệ thực tế phụ thuộc vào erasure set và parity configuration của MinIO. Cần dùng runtime evidence, chẳng hạn `mc admin info` và `mc admin object info`, trước khi kết luận chính xác object có bao nhiêu data shard và parity shard.

## 3. Quorum và khả năng chịu lỗi

Để đọc hoặc ghi object, erasure set phải còn đủ số drive khỏe theo quorum của cấu hình parity. Nếu mất một số drive hoặc node nhưng vẫn còn quorum, MinIO có thể tiếp tục phục vụ object và dùng parity để reconstruct dữ liệu thiếu. Nếu mất quá nhiều endpoint làm mất quorum, object hoặc thao tác ghi có thể không còn khả dụng.

Vì vậy, không nên nói đơn giản rằng “mất một node luôn không ảnh hưởng”. Kết quả phụ thuộc vào:

- object đang nằm trong erasure set nào;
- parity của object khi object được ghi;
- số drive thực tế còn khỏe;
- lỗi là lỗi process, container, volume hay toàn bộ host.

## 4. Erasure Coding khác Replication thế nào?

**Replication** tạo nhiều bản sao tương đối đầy đủ của object. Cách này dễ giải thích và truy xuất bản sao khi một bản bị lỗi, nhưng tiêu tốn dung lượng theo số bản sao. Replication thường được dùng giữa các site hoặc cluster để tăng tính độc lập của bản sao.

**Erasure Coding** chia object thành data shard và parity shard. Nó thường đạt hiệu quả dung lượng tốt hơn replication cùng mức bảo vệ, nhưng cần tính toán, quorum và quy trình healing phức tạp hơn. Parity không phải là một bản copy nguyên vẹn của object; nó là thông tin dư thừa để tái tạo shard bị mất.

Trong dự án này, Nginx chỉ là load balancer và không tạo redundancy. Redundancy nằm ở distributed MinIO và cơ chế erasure coding phía sau các endpoint lưu trữ.

## 5. Giới hạn của mô hình Docker trên một máy

Bốn container trên cùng một máy giúp mô phỏng topology, network, volume và failure scenario với chi phí thấp. Tuy nhiên, đây không phải bốn failure domain độc lập:

- Docker daemon hoặc máy host hỏng có thể làm cả bốn node cùng mất.
- Các volume Docker thường dùng chung storage subsystem của host.
- Network giữa container không đại diện đầy đủ cho latency và lỗi của các máy vật lý khác nhau.
- Tài nguyên CPU, RAM và I/O vẫn bị cạnh tranh trên một máy.

Do đó, lab có thể chứng minh cách MinIO distributed khởi động, phân phối object và xử lý một số lỗi container/volume. Không nên dùng kết quả của lab một máy để khẳng định production có khả năng chịu lỗi rack, máy chủ, zone hoặc site.

## 6. Câu hỏi cần chuẩn bị khi thuyết trình

- Vì sao không dùng bốn MinIO standalone sau Nginx? Vì load balancing không tạo ra một storage pool chung; distributed command mới cho MinIO biết toàn bộ endpoint của cluster.
- Vì sao cần hai volume mỗi node? Để lab có nhiều endpoint lưu trữ trong cùng topology, phù hợp với distributed erasure set và giúp quan sát failure/healing.
- Nginx có tạo parity không? Không. Nginx chỉ chuyển tiếp S3 request; MinIO mới chịu trách nhiệm shard, parity, quorum và healing.
- Làm sao chứng minh cluster thật sự distributed? Kiểm tra command, service/network topology và runtime bằng `mc admin info` hoặc `mc admin object info`, không chỉ nhìn vào số container.

## Tài liệu tham khảo

- [MinIO Erasure Coding](https://min.io/docs/minio/linux/operations/concepts/erasure-coding.html)
- [MinIO Availability and Resiliency](https://min.io/docs/minio/container/operations/concepts/availability-and-resiliency.html)
- [MinIO Multi-Node Multi-Drive Deployment](https://min.io/docs/minio/linux/operations/install-deploy-manage/deploy-minio-multi-node-multi-drive.html)
