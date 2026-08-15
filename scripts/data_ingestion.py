from __future__ import annotations

import argparse
import logging
import mimetypes
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)
from dotenv import load_dotenv
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT_DIR / "scripts" / "sample_data"
DEFAULT_ENDPOINT_URL = "http://localhost:9000"
DEFAULT_BUCKET = "raw-data"
DEFAULT_REGION = "us-east-1"
LOGGER = logging.getLogger("data_ingestion")

load_dotenv(ROOT_DIR / ".env")

RETRYABLE_S3_CODES = {
    "InternalError",
    "RequestTimeout",
    "RequestTimeoutException",
    "ServiceUnavailable",
    "SlowDown",
}
RETRYABLE_EXCEPTIONS = (
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)
HANDLED_OPERATION_EXCEPTIONS = (
    BotoCoreError,
    ClientError,
    RuntimeError,
)
PREFLIGHT_EXCEPTIONS = (FileNotFoundError, *HANDLED_OPERATION_EXCEPTIONS)
FILE_OPERATION_EXCEPTIONS = (OSError, *HANDLED_OPERATION_EXCEPTIONS)


def is_retryable_s3_error(error: BaseException) -> bool:
    """Return True only for transient network errors and S3 5xx responses."""
    if isinstance(error, RETRYABLE_EXCEPTIONS):
        return True

    if not isinstance(error, ClientError):
        return False

    response = error.response
    status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
    error_code = response.get("Error", {}).get("Code", "")
    return status_code >= 500 or error_code in RETRYABLE_S3_CODES


def retry_s3_operation(function):
    """Apply the project's three-attempt exponential-backoff policy."""
    return retry(
        retry=retry_if_exception(is_retryable_s3_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        before_sleep=before_sleep_log(LOGGER, logging.WARNING),
        reraise=True,
    )(function)


def get_credentials() -> tuple[str, str]:
    """Read application credentials, with root credentials as a lab fallback."""
    access_key = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("MINIO_ROOT_USER")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv(
        "MINIO_ROOT_PASSWORD"
    )
    if not access_key or not secret_key:
        raise RuntimeError(
            "Missing credentials. Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY "
            "or MINIO_ROOT_USER/MINIO_ROOT_PASSWORD in .env."
        )
    return access_key, secret_key


def create_s3_client(endpoint_url: str, region: str):
    """Create a path-style S3 client for the Nginx entrypoint."""
    access_key, secret_key = get_credentials()
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 1, "mode": "standard"},
        ),
    )


@retry_s3_operation
def check_bucket(s3_client, bucket_name: str) -> None:
    """Verify that the bootstrap process created the destination bucket."""
    s3_client.head_bucket(Bucket=bucket_name)


def infer_data_type(file_path: Path) -> str:
    """Map a source file to a stable Data Lake partition value."""
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".log", ".txt"}:
        return "logs"
    if suffix in {".bin", ".bmp", ".gif", ".jpeg", ".jpg", ".png"}:
        return "binary"
    return "other"


def scan_source_files(source_dir: Path) -> list[Path]:
    """Recursively find dataset files while excluding generated downloads."""
    if not source_dir.is_dir():
        raise FileNotFoundError(
            f"Source directory does not exist: {source_dir}. "
            "Run scripts/generate_data.py first."
        )

    files = []
    for file_path in source_dir.rglob("*"):
        if not file_path.is_file():
            continue
        relative_parts = file_path.relative_to(source_dir).parts
        if "downloads" in relative_parts or any(
            part.startswith(".") for part in relative_parts
        ):
            continue
        files.append(file_path)

    return sorted(files)


def build_object_key(
    file_path: Path,
    source_dir: Path,
    partition_date: date,
) -> str:
    """Build data_type/year/month/day partitions inside the raw-data bucket."""
    relative_path = file_path.relative_to(source_dir).as_posix()
    data_type = infer_data_type(file_path)
    return (
        f"{data_type}/year={partition_date:%Y}/month={partition_date:%m}/"
        f"day={partition_date:%d}/{relative_path}"
    )


def build_metadata(file_path: Path, source_id: str) -> dict[str, str]:
    """Build custom metadata sent as x-amz-meta-* headers by boto3."""
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return {
        "source": source_id,
        "ingested-at": datetime.now(timezone.utc).isoformat(),
        "data-type": infer_data_type(file_path),
        "content-type-detected": content_type,
    }


@retry_s3_operation
def upload_object(
    s3_client,
    file_path: Path,
    bucket_name: str,
    object_key: str,
    metadata: dict[str, str],
) -> None:
    """Upload one object through Nginx with custom metadata."""
    with file_path.open("rb") as source_file:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=source_file,
            Metadata=metadata,
        )


@retry_s3_operation
def verify_object(
    s3_client,
    bucket_name: str,
    object_key: str,
    expected_size: int,
    expected_metadata: dict[str, str],
) -> None:
    """Verify object size and custom metadata after upload."""
    response: dict[str, Any] = s3_client.head_object(
        Bucket=bucket_name,
        Key=object_key,
    )
    if response.get("ContentLength") != expected_size:
        raise RuntimeError(
            f"Size verification failed for s3://{bucket_name}/{object_key}"
        )

    actual_metadata = response.get("Metadata", {})
    mismatched_keys = [
        key
        for key, value in expected_metadata.items()
        if actual_metadata.get(key) != value
    ]
    if mismatched_keys:
        raise RuntimeError(
            f"Metadata verification failed for {object_key}: {mismatched_keys}"
        )


def parse_partition_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Partition date must use YYYY-MM-DD format."
        ) from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload a local dataset to partitioned MinIO objects."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path(os.getenv("INGESTION_SOURCE_DIR", DEFAULT_SOURCE_DIR)),
        help="Directory scanned recursively for source files.",
    )
    parser.add_argument(
        "--bucket",
        default=os.getenv("INGESTION_BUCKET", DEFAULT_BUCKET),
        help="Destination bucket created by the MinIO bootstrap task.",
    )
    parser.add_argument(
        "--endpoint-url",
        default=os.getenv("ENDPOINT_URL", DEFAULT_ENDPOINT_URL),
        help="Nginx S3 endpoint.",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_DEFAULT_REGION", DEFAULT_REGION),
    )
    parser.add_argument(
        "--source-id",
        default=os.getenv("DATA_SOURCE_ID", "sensor-01"),
        help="Value stored in x-amz-meta-source.",
    )
    parser.add_argument(
        "--partition-date",
        type=parse_partition_date,
        default=datetime.now(timezone.utc).date(),
        help="Partition date in YYYY-MM-DD format; defaults to the current UTC date.",
    )
    return parser.parse_args()


def resolve_source_dir(source_dir: Path) -> Path:
    if source_dir.is_absolute():
        return source_dir.resolve()
    return (ROOT_DIR / source_dir).resolve()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    args = parse_args()
    source_dir = resolve_source_dir(args.source_dir)

    LOGGER.info("Endpoint: %s", args.endpoint_url)
    LOGGER.info("Bucket: %s", args.bucket)
    LOGGER.info("Source directory: %s", source_dir)
    LOGGER.info("Partition date: %s", args.partition_date.isoformat())

    try:
        source_files = scan_source_files(source_dir)
        if not source_files:
            raise RuntimeError(f"No source files found in {source_dir}")
        s3_client = create_s3_client(args.endpoint_url, args.region)
        check_bucket(s3_client, args.bucket)
    except PREFLIGHT_EXCEPTIONS as error:
        LOGGER.error("Ingestion preflight failed: %s", error)
        return 1

    uploaded_files = 0
    uploaded_bytes = 0
    failed_files = 0
    pipeline_started = time.perf_counter()

    for file_path in source_files:
        try:
            object_key = build_object_key(
                file_path,
                source_dir,
                args.partition_date,
            )
            metadata = build_metadata(file_path, args.source_id)
            file_size = file_path.stat().st_size
            upload_started = time.perf_counter()
            upload_object(
                s3_client,
                file_path,
                args.bucket,
                object_key,
                metadata,
            )
            verify_object(
                s3_client,
                args.bucket,
                object_key,
                file_size,
                metadata,
            )
        except FILE_OPERATION_EXCEPTIONS as error:
            failed_files += 1
            LOGGER.error("Upload failed for %s: %s", file_path, error)
            continue

        elapsed = time.perf_counter() - upload_started
        uploaded_files += 1
        uploaded_bytes += file_size
        LOGGER.info(
            "Uploaded %s -> s3://%s/%s (%d bytes, %.4f seconds)",
            file_path.relative_to(source_dir),
            args.bucket,
            object_key,
            file_size,
            elapsed,
        )

    pipeline_elapsed = time.perf_counter() - pipeline_started
    throughput = (
        uploaded_bytes / (1024 * 1024) / pipeline_elapsed
        if pipeline_elapsed > 0
        else 0.0
    )
    LOGGER.info(
        "Summary: uploaded=%d failed=%d bytes=%d duration=%.4fs throughput=%.2f MB/s",
        uploaded_files,
        failed_files,
        uploaded_bytes,
        pipeline_elapsed,
        throughput,
    )
    return 1 if failed_files else 0


if __name__ == "__main__":
    raise SystemExit(main())
