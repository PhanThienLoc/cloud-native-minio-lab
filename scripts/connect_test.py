from __future__ import annotations

import argparse
import hashlib
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


def get_credentials() -> tuple[str, str]:
    """Resolve credentials without embedding a secret in source."""
    access_key_id = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("MINIO_ROOT_USER")
    secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("MINIO_ROOT_PASSWORD")

    if not access_key_id or not secret_access_key:
        raise RuntimeError(
            "Missing credentials. Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY "
            "or MINIO_ROOT_USER/MINIO_ROOT_PASSWORD in .env."
        )

    return access_key_id, secret_access_key


def get_s3_client() -> boto3.client:
    try:
        access_key_id, secret_access_key = get_credentials()
        return boto3.client(
            "s3",
            endpoint_url=DEFAULT_ENDPOINT_URL,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=DEFAULT_REGION,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
    except Exception as error:
        raise RuntimeError(f"Unable to create S3 client: {_error_message(error)}") from error


def ensure_bucket_exists(s3_client: boto3.client, bucket_name: str) -> None:
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError as error:
        error_code = str(error.response.get("Error", {}).get("Code", ""))
        if error_code not in {"404", "NoSuchBucket", "NotFound"}:
            raise

        print(f"[INFO] Bucket '{bucket_name}' does not exist; creating it...")
        create_kwargs = {"Bucket": bucket_name}
        if DEFAULT_REGION != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": DEFAULT_REGION}

        s3_client.create_bucket(**create_kwargs)
        print(f"[SUCCESS] Created bucket '{bucket_name}'.")


def upload_file(file_path: str | Path, bucket_name: str, object_name: str | None = None) -> bool:
    local_path = Path(file_path)
    if not local_path.is_file():
        print(f"[ERROR] Local file does not exist: {local_path}")
        return False

    object_name = object_name or local_path.name
    try:
        s3_client = get_s3_client()
        ensure_bucket_exists(s3_client, bucket_name)
    except (BotoCoreError, ClientError, EndpointConnectionError, RuntimeError) as error:
        print(f"[ERROR] Upload failed: {_error_message(error)}")
        return False

    file_size = local_path.stat().st_size
    print(
        f"\n--- UPLOAD: {local_path.name} -> s3://{bucket_name}/{object_name} "
        f"({file_size / (1024 * 1024):.2f} MB) ---"
    )

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
        print("[SUCCESS] Upload completed.")
        print(f"[METRIC] Upload latency: {latency:.4f} seconds")
        return True
    except (BotoCoreError, ClientError, EndpointConnectionError) as error:
        print(f"[ERROR] Upload failed: {_error_message(error)}")
        return False


def download_file(object_name: str, file_path: str | Path, bucket_name: str) -> bool:
    download_path = Path(file_path)
    download_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        s3_client = get_s3_client()
        response = s3_client.head_object(Bucket=bucket_name, Key=object_name)
        file_size = int(response.get("ContentLength", 0))
        print(
            f"\n--- DOWNLOAD: s3://{bucket_name}/{object_name} -> {download_path} "
            f"({file_size / (1024 * 1024):.2f} MB) ---"
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
        print(f"[SUCCESS] Download completed: {download_path}")
        print(f"[METRIC] Download latency: {latency:.4f} seconds")
        return True
    except (BotoCoreError, ClientError, EndpointConnectionError, RuntimeError) as error:
        print(f"[ERROR] Download failed: {_error_message(error)}")
        return False


def sha256_file(file_path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(file_path).open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test boto3 upload/download through the Nginx Load Balancer."
    )
    parser.add_argument("--bucket", default=DEFAULT_BUCKET_NAME, help="Test bucket name.")
    parser.add_argument("--file", dest="file_path", default=str(DEFAULT_SAMPLE_FILE))
    parser.add_argument("--object-name", default=None)
    parser.add_argument("--download-path", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = Path(args.file_path)
    object_name = args.object_name or source_path.name
    download_path = Path(args.download_path) if args.download_path else DEFAULT_DOWNLOAD_DIR / source_path.name

    print("[INFO] Connection configuration:")
    print(f"[INFO]   endpoint_url = {DEFAULT_ENDPOINT_URL}")
    print(f"[INFO]   bucket       = {args.bucket}")
    print(f"[INFO]   source_file  = {source_path}")
    print(f"[INFO]   object_name  = {object_name}")
    print(f"[INFO]   download_path = {download_path}")

    try:
        get_s3_client()
    except (BotoCoreError, ClientError, EndpointConnectionError, RuntimeError) as error:
        print(f"[ERROR] Cannot connect to endpoint: {_error_message(error)}")
        return 1

    if not upload_file(source_path, args.bucket, object_name):
        return 1
    if not download_file(object_name, download_path, args.bucket):
        return 1

    source_size = source_path.stat().st_size
    downloaded_size = download_path.stat().st_size if download_path.exists() else -1
    if source_size != downloaded_size:
        print(f"[ERROR] Size mismatch: source={source_size}, downloaded={downloaded_size}")
        return 1

    print(f"[VERIFY] Size matches: {source_size} bytes")
    source_sha256 = sha256_file(source_path)
    downloaded_sha256 = sha256_file(download_path)
    if source_sha256 != downloaded_sha256:
        print(f"[ERROR] SHA256 mismatch: source={source_sha256}, downloaded={downloaded_sha256}")
        return 1

    print(f"[VERIFY] SHA256 matches: {source_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
