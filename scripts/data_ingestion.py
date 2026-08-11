from __future__ import annotations

import logging
import os
import time  # [Thang] Import module đo thời gian
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# ==============================================================================
# 1. CẤU HÌNH LOGGING & MÔI TRƯỜNG
# ==============================================================================
# [Thang] Định dạng hiển thị log theo thời gian và mức độ nghiêm trọng
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# [Thang] Nạp biến môi trường từ file .env
load_dotenv()

# [Loc] Khai báo cấu trúc thư mục phân hoạch dữ liệu mẫu ban đầu
PARTITION_PATH = Path("year=2026/month=07")

# [Thang] Đọc cấu hình kết nối MinIO qua Nginx Load Balancer (Cổng 9000 dành cho Code)
ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000")
AWS_ACCESS_KEY_ID = os.getenv("MINIO_ROOT_USER", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "my-data-lake")


# ==============================================================================
# 2. KHỞI TẠO S3 CLIENT [Thang]
# ==============================================================================
def tao_ket_noi_s3():
    """Khởi tạo kết nối boto3 S3 Client đến MinIO qua Nginx Load Balancer (Port 9000)."""
    try:
        return boto3.client(
            "s3",
            endpoint_url=ENDPOINT_URL,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
    except Exception as e:
        logging.error(f"Lỗi khởi tạo S3 Client: {e}")
        return None


# ==============================================================================
# 3. RESILIENCE: UPLOAD VỚI EXPONENTIAL BACKOFF RETRY & ĐO TỐC ĐỘ [Thang]
# ==============================================================================
@retry(
    stop=stop_after_attempt(3),  # [Thang] Thử lại tối đa 3 lần
    wait=wait_exponential(multiplier=1, min=2, max=10),  # [Thang] Chờ tăng dần theo cấp số nhân (2s, 4s, 8s...)
    retry=retry_if_exception_type((BotoCoreError, ClientError)),  # [Thang] Chỉ retry khi gặp lỗi kết nối/S3 SDK
    before_sleep=lambda state: logging.warning(f"[Retry] Mạng chập chờn/Timeout. Thử lại lần {state.attempt_number}/3..."),
    reraise=True,  # [Thang] Ném lỗi ra ngoài nếu quá 3 lần thất bại
)
def upload_file_voi_retry(s3_client, file_path: Path, object_key: str, metadata: dict):
    """Upload file lên S3/MinIO kèm HTTP Metadata Headers và tính toán tốc độ truyền tải."""
    # [Thang] 1. Tính kích thước file (Bytes)
    file_size_bytes = file_path.stat().st_size

    # [Thang] 2. Bắt đầu bấm giờ
    start_time = time.perf_counter()

    # [Thang] 3. Thực thi upload file
    s3_client.upload_file(
        Filename=str(file_path),
        Bucket=BUCKET_NAME,
        Key=object_key,
        ExtraArgs={"Metadata": metadata},  # [Thang] Gắn metadata (boto3 tự đổi thành x-amz-meta-*)
    )

    # [Thang] 4. Dừng bấm giờ và tính toán thông số
    duration = time.perf_counter() - start_time
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    # Tránh chia cho 0 nếu thời gian upload quá nhanh (< 0.001 giây)
    speed_mbps = file_size_mb / duration if duration > 0 else 0.0

    # [Thang] 5. In log kết quả đo tốc độ
    logging.info(f"--> Upload thành công!")
    logging.info(f"    - Dung lượng: {file_size_bytes} Bytes ({file_size_mb:.4f} MB)")
    logging.info(f"    - Thời gian thực thi: {duration:.4f} giây")
    logging.info(f"    - Tốc độ truyền trung bình: {speed_mbps:.2f} MB/s")


# ==============================================================================
# 4. CHƯƠNG TRÌNH CHÍNH (DATA INGESTION PIPELINE)
# ==============================================================================
def main() -> None:
    # --------------------------------------------------------------------------
    # TẠO DỮ LIỆU MẪU CỤC BỘ (LOCAL MOCK DATA) [Loc]
    # --------------------------------------------------------------------------
    # [Loc] Xác định đường dẫn file đầu ra: year=2026/month=07/sample.txt
    target = PARTITION_PATH / "sample.txt"
    
    # [Loc] Tạo cây thư mục cha nếu chưa tồn tại
    target.parent.mkdir(parents=True, exist_ok=True)
    
    # [Loc] Ghi nội dung payload mẫu vào file
    target.write_text("sample payload\n", encoding="utf-8")
    print(f"[Member 1] Prepared partitioned data at {target}")

    # --------------------------------------------------------------------------
    # TIẾN HÀNH INGESTION LÊN MINIO DATA LAKE [Thang]
    # --------------------------------------------------------------------------
    # [Thang] Tạo kết nối tới S3/MinIO
    s3_client = tao_ket_noi_s3()
    if not s3_client:
        logging.critical("Không thể kết nối S3 Client. Dừng chương trình.")
        return

    # [Thang] Tự động tạo Bucket 'my-data-lake' nếu chưa có sẵn trên MinIO
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
    except (ClientError, BotoCoreError):
        logging.info(f"Bucket '{BUCKET_NAME}' chưa tồn tại. Đang khởi tạo mới...")
        try:
            s3_client.create_bucket(Bucket=BUCKET_NAME)
        except Exception as create_err:
            logging.warning(f"Không thể tạo bucket tự động: {create_err}")

    # [Thang] Xây dựng Hive-style Object Key chuẩn Big Data
    # Chuyển đường dẫn Windows 'year=2026\month=07' thành 'year=2026/month=07' bằng as_posix()
    now = datetime.now()
    day_str = now.strftime("%d")
    partition_posix = target.parent.as_posix()
    object_key = f"raw-data/sensor/{partition_posix}/day={day_str}/{target.name}"

    # [Thang] Inject Metadata vào HTTP Headers (x-amz-meta-*)
    custom_metadata = {
        "source": "sensor-01",                     # Nguồn dữ liệu (x-amz-meta-source)
        "timestamp": datetime.now().isoformat(),   # Thời điểm upload (x-amz-meta-timestamp)
        "ingested-by": "member2-pipeline",         # Tên pipeline xử lý (x-amz-meta-ingested-by)
    }

    # [Thang] Thực thi Upload kèm cơ chế Resilience Retry qua cổng 9000
    try:
        logging.info(f"Đang upload: {target} -> {object_key}")
        upload_file_voi_retry(s3_client, target, object_key, custom_metadata)
    except Exception as e:
        logging.error(f"--> Upload thất bại hoàn toàn sau 3 lần retry. Lỗi: {e}")


# [Member 1 & 2] Điểm khởi chạy chương trình khi thực thi trực tiếp
if __name__ == "__main__":
    main()