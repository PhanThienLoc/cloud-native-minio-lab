# Chương 1: Tổng quan dự án

## 1.1 Bối cảnh
Trong kỷ nguyên chuyển đổi số, sự bùng nổ của các công nghệ như Trí tuệ nhân tạo (AI), Điện toán đám mây (Cloud Computing), Dữ liệu lớn (Big Data) và Internet kết nối mọi thứ (IoT) đã dẫn đến sự tăng trưởng vượt bậc về lượng dữ liệu phát sinh hàng ngày. Theo các báo cáo phân tích thị trường công nghệ, khoảng 80% đến 90% lượng dữ liệu mới được tạo ra hiện nay thuộc loại dữ liệu phi cấu trúc (unstructured data). Những dữ liệu này thường bao gồm hình ảnh, video độ phân giải cao, tệp âm thanh, tài liệu văn bản, log hệ thống, dữ liệu cảm biến IoT, bản sao lưu và snapshot.

Khác với dữ liệu có cấu trúc (structured data) có thể dễ dàng sắp xếp và truy vấn qua các hàng và cột trong hệ quản trị cơ sở dữ liệu quan hệ (RDBMS) truyền thống, dữ liệu phi cấu trúc lại có đặc tính kích thước tệp biến động rất lớn, không tuân theo một lược đồ cố định (schema-less) và đòi hỏi khả năng lưu trữ mở rộng cũng như truy xuất song song với độ trễ thấp.

Sự gia tăng đột biến của dữ liệu phi cấu trúc kéo theo nhu cầu lưu trữ ở quy mô Terabyte (TB), Petabyte (PB) và thậm chí Exabyte (EB). Đây chính là nguyên nhân làm lộ rõ những hạn chế của mô hình lưu trữ tập trung truyền thống như NAS hoặc SAN:

- **Chi phí nâng cấp đắt đỏ**: Việc mở rộng hệ thống tập trung phụ thuộc nhiều vào phần cứng chuyên dụng từ các nhà cung cấp lớn, dẫn đến chi phí đầu tư ban đầu (CapEx) và vận hành (OpEx) rất cao.
- **Giới hạn vật lý**: Mô hình tập trung bị giới hạn bởi khả năng xử lý của bộ điều khiển (controller) và dung lượng tối đa mà một tủ đĩa có thể chứa.
- **Nút thắt cổ chai (bottleneck)**: Khi hàng triệu kết nối đồng thời đổ về một điểm trung tâm, hạ tầng mạng và bộ điều khiển sẽ dễ rơi vào trạng thái quá tải, làm giảm đáng kể hiệu năng truy xuất dữ liệu.

Để vượt qua các rào cản này, các kiến trúc hạ tầng hiện đại đang chuyển dịch sang mô hình lưu trữ phân tán (Distributed Storage) với khả năng mở rộng ngang (Scale-out) và chịu lỗi (Fault Tolerance):

- **Khả năng mở rộng ngang (Scale-out)**: Thay vì nâng cấp cấu hình của một máy chủ duy nhất (Scale-up), hệ thống phân tán cho phép bổ sung nhiều máy chủ tiêu chuẩn (commodity hardware) vào cụm (cluster). Điều này giúp mở rộng dung lượng lưu trữ và băng thông xử lý một cách linh hoạt mà không làm gián đoạn hệ thống đang hoạt động.
- **Khả năng chịu lỗi (Fault Tolerance)**: Nhờ áp dụng các thuật toán phân tán và cơ chế bảo vệ dữ liệu tiên tiến, hệ thống vẫn duy trì tính sẵn sàng cao (High Availability) ngay cả khi một hoặc nhiều nút lưu trữ (nodes) hoặc ổ đĩa bị hỏng hoàn toàn.

## 1.2 Bài toán
Khi xây dựng và vận hành hệ thống lưu trữ dữ liệu quy mô lớn, việc tiếp tục trung thành với mô hình lưu trữ máy chủ đơn lẻ hoặc hạ tầng tập trung khiến các tổ chức phải đối mặt với bốn nguy cơ và thách thức cốt lõi sau:

1. **Nút thắt điểm lỗi đơn lẻ (Single Point of Failure - SPOF)**
   Trong một hệ thống lưu trữ tập trung hoặc chạy trên một máy chủ đơn lẻ, mọi tệp tin và yêu cầu đọc/ghi đều đi qua một điểm duy nhất. Nếu máy chủ này gặp sự cố như hỏng bo mạch chủ, lỗi RAM, sập nguồn hoặc cháy ổ đĩa hệ điều hành, toàn bộ hệ thống lưu trữ sẽ ngay lập tức ngừng hoạt động. Mọi ứng dụng phụ thuộc vào dữ liệu đều bị ngưng trệ, gây gián đoạn toàn bộ quy trình nghiệp vụ.

2. **Khó khăn và giới hạn trong việc mở rộng (Scalability Bottlenecks)**
   Nâng cấp theo chiều dọc (Scale-up)—tức mua ổ cứng dung lượng lớn hơn hoặc bổ sung thêm RAM/CPU cho một máy chủ—luôn chạm trán rào cản về giới hạn phần cứng như số lượng khe cắm ổ đĩa hoặc số kênh RAM tối đa của bo mạch chủ. Việc thay thế máy chủ cũ bằng một máy chủ mạnh hơn rất tốn kém, phức tạp trong khâu di chuyển dữ liệu (data migration) và không giải quyết được bài toán lưu trữ lâu dài khi dữ liệu tiếp tục tăng trưởng.

3. **Nguy cơ gián đoạn dịch vụ (Service Downtime)**
   Đối với máy chủ đơn lẻ, các hoạt động bảo trì định kỳ, nâng cấp hệ điều hành, vá lỗi bảo mật hoặc thay thế phần cứng hỏng bắt buộc phải tắt máy chủ (planned downtime). Với các doanh nghiệp vận hành 24/7, thời gian ngừng hoạt động này gây thiệt hại lớn về kinh tế, làm giảm trải nghiệm người dùng và ảnh hưởng tiêu cực đến uy tín thương hiệu.

4. **Nguy cơ mất mát dữ liệu và không thể truy cập dữ liệu (Data Loss & Inaccessibility)**
   - **Mất mát dữ liệu (Data Loss)**: Ổ cứng vật lý luôn có tỷ lệ hỏng hóc tự nhiên theo thời gian. Nếu không có cơ chế phân tán dữ liệu an toàn, sự cố hư hỏng đĩa cứng hoặc hỏng tệp do lỗi phần mềm (silent data corruption) sẽ dẫn đến mất mát dữ liệu vĩnh viễn và khó phục hồi.
   - **Không thể truy cập dữ liệu (Inaccessibility)**: Dù dữ liệu trên ổ cứng vẫn còn nguyên vẹn, nếu máy chủ chứa ổ cứng đó bị mất kết nối mạng hoặc lỗi hệ điều hành, người dùng và ứng dụng cũng sẽ không thể truy cập hoặc lấy lại dữ liệu kịp thời.

## 1.3 Mục tiêu dự án
Nhằm giải quyết triệt để các bài toán thực tiễn trên, dự án được triển khai với mục tiêu xây dựng, thực nghiệm và đánh giá toàn diện mô hình lưu trữ đối tượng phân tán dựa trên công nghệ MinIO. Các mục tiêu kỹ thuật cụ thể bao gồm:

- **Xây dựng cụm MinIO phân tán (Distributed MinIO Cluster)**: Thiết lập mô hình lưu trữ đối tượng phân tán gồm 4 node MinIO hoạt động liên kết chặt chẽ với nhau, đóng vai trò như một hệ thống lưu trữ nhất quán duy nhất.
- **Đóng gói và quản lý bằng Docker Compose**: Áp dụng công nghệ container hóa để đóng gói toàn bộ các node MinIO và các dịch vụ liên quan. Sử dụng Docker Compose để tự động hóa quy trình khởi chạy, quản lý mạng nội bộ (bridge network) và thiết lập biến môi trường nhất quán.
- **Tích hợp Nginx Load Balancer**: Triển khai một máy chủ Nginx làm cân bằng tải ở phía trước cụm 4 node MinIO. Nginx chịu trách nhiệm tiếp nhận toàn bộ HTTP/HTTPS requests từ client và phân phối đều đến 4 node, giúp tối ưu hóa hiệu năng truy xuất và đảm bảo điểm truy cập duy nhất (Single Entry Point).
- **Giao tiếp chuẩn S3-compatible API**: Đảm bảo hệ thống cung cấp đầy đủ cổng giao tiếp tương thích hoàn toàn với Amazon S3 API (RESTful API), cho phép sử dụng các SDK/CLI phổ biến như Python, AWS CLI và MinIO Client mc để tương tác với dữ liệu.
- **Triển khai cơ chế Erasure Coding**: Nghiên cứu và hiện thực hóa cơ chế mã hóa xóa (Erasure Coding) của MinIO. Cơ chế này chia nhỏ đối tượng dữ liệu thành các đoạn dữ liệu (data blocks) và đoạn mã sửa lỗi (parity blocks), phân tán đều qua 4 node để bảo vệ dữ liệu tối ưu.
- **Phát triển script tự động hóa**: Tự động hóa các thao tác quản trị bằng cách viết các kịch bản (scripts) tự động tạo bucket, upload/download dữ liệu, kiểm tra trạng thái toàn vẹn và xác minh mã băm dữ liệu.
- **Triển khai hệ thống giám sát (Monitoring System)**: Đặt nền móng và tích hợp công cụ theo dõi, thu thập các thông số vận hành, dung lượng sử dụng và trạng thái các node nhằm phục vụ cho công tác đánh giá hiệu năng hệ thống ở các giai đoạn sau.

## 1.4 Phạm vi dự án
Để đảm bảo dự án đi đúng hướng và tập trung vào các mục tiêu nghiên cứu cốt lõi, phạm vi thực hiện được quy định cụ thể như sau:

- **Mô hình phòng thí nghiệm (Lab Environment)**: Dự án được thiết kế và vận hành hoàn toàn dưới dạng một mô hình lab giả lập. Toàn bộ cụm MinIO 4 node, Nginx Load Balancer và các dịch vụ liên quan đều được triển khai dưới dạng các container trên một máy tính vật lý duy nhất.
- **Mục đích nghiên cứu và thử nghiệm**: Dự án tập trung vào việc mô phỏng kiến trúc lưu trữ phân tán, kiểm chứng tính năng cân bằng tải, thử nghiệm cơ chế Erasure Coding, đánh giá khả năng chịu lỗi khi node bị ngắt kết nối và đo đạc hiệu năng đọc/ghi.

### Tuyên bố giới hạn phạm vi
- Dự án không triển khai trên hạ tầng phần cứng đa máy chủ thực tế (multi-node physical hardware).
- Dự án không cấu hình trên môi trường trung tâm dữ liệu phân tán thật (multi-datacenter / cross-region deployment).
- Dự án không đại diện cho một hệ thống sản xuất thương mại quy mô thực tế (production environment).

## 1.5 Kết quả dự kiến
Khi hoàn thành Chương 1 và toàn bộ nội dung dự án, các kết quả đầu ra dự kiến thu được bao gồm:

- **Bộ mã nguồn cấu hình cụm hoàn chỉnh**: Tệp docker-compose.yml cùng các tệp cấu hình Nginx hoàn chỉnh, cho phép khởi tạo thành công cụm lưu trữ phân tán 4 node MinIO kết hợp Nginx Load Balancer chỉ với một câu lệnh.
- **Bộ tập lệnh tự động hóa (scripts)**: Các script (Bash/Python) có khả năng tự động tạo bucket, tải lên và tải xuống các tập tin mẫu có dung lượng khác nhau thông qua S3 API.
- **Báo cáo kiểm tra tính toàn vẹn dữ liệu**: Kết quả đối sánh checksum (MD5/SHA256) xác minh dữ liệu tải về hoàn toàn trùng khớp với dữ liệu gốc ban đầu, chứng minh tính tin cậy của hệ thống.
- **Kết quả kiểm thử khả năng chịu lỗi (Fault Tolerance Test)**: Kịch bản giả lập sự cố bằng cách cưỡng chế dừng 1 hoặc 2 node MinIO bất kỳ trong cụm, chứng minh hệ thống vẫn tiếp tục phục vụ các yêu cầu đọc/ghi dữ liệu từ client mà không làm gián đoạn dịch vụ hay mất mát dữ liệu.
- **Bộ số liệu và biểu đồ đánh giá hiệu năng**: Thu thập chi tiết các chỉ số hoạt động như thời gian phản hồi (latency), tốc độ truy xuất dữ liệu (throughput MB/s) và mức độ tiêu tốn tài nguyên (CPU, RAM, Disk I/O) trong hai trạng thái: hoạt động bình thường và khi có node gặp sự cố hỏng hóc.
