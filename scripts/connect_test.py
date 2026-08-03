from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError
from dotenv import load_dotenv
from tqdm import tqdm

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DEFAULT_ENDPOINT_URL = os.getenv("ENDPOINT_URL", "http://localhost:9000")
DEFAULT_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
DEFAULT_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
DEFAULT_BUCKET_NAME = os.getenv("TEST_BUCKET_NAME", "demo-bucket")
DEFAULT_SAMPLE_FILE = ROOT_DIR / "scripts" / "sample_data" / "user_data.csv"
DEFAULT_DOWNLOAD_DIR = ROOT_DIR / "scripts" / "sample_data" / "downloads"


def _error_message(error: Exception) -> str:
    if isinstance(error, ClientError):
        response = error.response.get("Error", {})
        code = response.get("Code", "ClientError")
        message = response.get("Message", str(error))
        return f"{code}: {message}"
    return str(error)


def get_s3_client() -> boto3.client:
    try:
        return boto3.client(
            "s3",
            endpoint_url=DEFAULT_ENDPOINT_URL,
            aws_access_key_id=DEFAULT_ACCESS_KEY_ID,
            aws_secret_access_key=DEFAULT_SECRET_ACCESS_KEY,
            region_name=DEFAULT_REGION,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
    except Exception as error:
        raise RuntimeError(f"Không thể khởi tạo S3 client: {_error_message(error)}") from error


def ensure_bucket_exists(s3_client: boto3.client, bucket_name: str) -> None:
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError as error:
        error_code = str(error.response.get("Error", {}).get("Code", ""))
        if error_code not in {"404", "NoSuchBucket", "NotFound"}:
            raise

        print(f"[INFO] Bucket '{bucket_name}' chưa tồn tại, đang tạo mới...")
        create_kwargs = {"Bucket": bucket_name}
        if DEFAULT_REGION != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": DEFAULT_REGION}

        s3_client.create_bucket(**create_kwargs)
        print(f"[SUCCESS] Đã tạo bucket '{bucket_name}'.")


def upload_file(file_path: str | Path, bucket_name: str, object_name: str | None = None) -> bool:
    local_path = Path(file_path)
    if not local_path.is_file():
        print(f"[ERROR] File cục bộ không tồn tại: {local_path}")
        return False

    if object_name is None:
        object_name = local_path.name

    s3_client = get_s3_client()
    ensure_bucket_exists(s3_client, bucket_name)

    file_size = local_path.stat().st_size
    print(f"\n--- BẮT ĐẦU UPLOAD: {local_path.name} -> s3://{bucket_name}/{object_name} ({file_size / (1024 * 1024):.2f} MB) ---")

    start_time = time.perf_counter()
    try:
        with tqdm(total=file_size, unit="B", unit_scale=True, desc="Upload") as progress:
            s3_client.upload_file(
                Filename=str(local_path),
                Bucket=bucket_name,
                Key=object_name,
                Callback=lambda bytes_transferred: progress.update(bytes_transferred),
            )
        latency = time.perf_counter() - start_time
        print("[SUCCESS] Upload thành công.")
        print(f"[METRIC] Upload latency: {latency:.4f} giây")
        return True
    except (BotoCoreError, ClientError, EndpointConnectionError) as error:
        print(f"[ERROR] Upload thất bại: {_error_message(error)}")
        return False


def download_file(object_name: str, file_path: str | Path, bucket_name: str) -> bool:
    download_path = Path(file_path)
    download_path.parent.mkdir(parents=True, exist_ok=True)

    s3_client = get_s3_client()

    try:
        response = s3_client.head_object(Bucket=bucket_name, Key=object_name)
        file_size = int(response.get("ContentLength", 0))

        print(
            f"\n--- BẮT ĐẦU DOWNLOAD: s3://{bucket_name}/{object_name} -> {download_path} ({file_size / (1024 * 1024):.2f} MB) ---"
        )

        start_time = time.perf_counter()
        with tqdm(total=file_size, unit="B", unit_scale=True, desc="Download") as progress:
            s3_client.download_file(
                Bucket=bucket_name,
                Key=object_name,
                Filename=str(download_path),
                Callback=lambda bytes_transferred: progress.update(bytes_transferred),
            )
        latency = time.perf_counter() - start_time
        print(f"[SUCCESS] Download thành công về: {download_path}")
        print(f"[METRIC] Download latency: {latency:.4f} giây")
        return True
    except (BotoCoreError, ClientError, EndpointConnectionError) as error:
        print(f"[ERROR] Download thất bại: {_error_message(error)}")
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Kiểm thử kết nối boto3 qua Nginx Load Balancer và đo latency upload/download."
    )
    parser.add_argument("--bucket", default=DEFAULT_BUCKET_NAME, help="Tên bucket dùng để kiểm thử.")
    parser.add_argument(
        "--file",
        dest="file_path",
        default=str(DEFAULT_SAMPLE_FILE),
        help="Đường dẫn file mẫu dùng để upload.",
    )
    parser.add_argument(
        "--object-name",
        default=None,
        help="Tên object trên MinIO. Mặc định lấy theo tên file nguồn.",
    )
    parser.add_argument(
        "--download-path",
        default=None,
        help="Đường dẫn lưu file tải về. Mặc định lưu trong scripts/sample_data/downloads/.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = Path(args.file_path)
    object_name = args.object_name or source_path.name
    download_path = Path(args.download_path) if args.download_path else DEFAULT_DOWNLOAD_DIR / source_path.name

    print("[INFO] Cấu hình kết nối:")
    print(f"[INFO]   endpoint_url = {DEFAULT_ENDPOINT_URL}")
    print(f"[INFO]   bucket       = {args.bucket}")
    print(f"[INFO]   source_file  = {source_path}")
    print(f"[INFO]   object_name  = {object_name}")
    print(f"[INFO]   download_path = {download_path}")

    try:
        s3_client = get_s3_client()
        s3_client.list_buckets()
    except (BotoCoreError, ClientError, EndpointConnectionError, RuntimeError) as error:
        print(f"[ERROR] Không thể kết nối tới endpoint: {_error_message(error)}")
        return 1

    upload_success = upload_file(source_path, args.bucket, object_name)
    if not upload_success:
        return 1

    download_success = download_file(object_name, download_path, args.bucket)
    if not download_success:
        return 1

    source_size = source_path.stat().st_size
    downloaded_size = download_path.stat().st_size if download_path.exists() else -1
    if source_size != downloaded_size:
        print(
            f"[ERROR] Kích thước không khớp sau download: source={source_size} bytes, downloaded={downloaded_size} bytes"
        )
        return 1

    print(f"[VERIFY] Kích thước khớp: {source_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())