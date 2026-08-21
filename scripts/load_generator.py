"""Generate concurrent S3 upload load and write a reproducible JSON report."""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import platform
import re
import shutil
import subprocess
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any, Callable, TypeVar

import boto3
from botocore.client import Config
from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)
from dotenv import load_dotenv

MAX_ATTEMPTS = 3
MAX_FILES = 20_000
MAX_THREADS = 128
MAX_FILE_SIZE_BYTES = 1024**3
MAX_TOTAL_BYTES = 10 * 1024**3
MAX_INFLIGHT_BYTES = 512 * 1024**2
TRANSIENT_S3_CODES = {
    "InternalError",
    "RequestTimeout",
    "RequestTimeoutException",
    "ServiceUnavailable",
    "SlowDown",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
thread_state = threading.local()
T = TypeVar("T")


@dataclass(frozen=True)
class S3Settings:
    """Connection settings loaded from environment variables."""

    endpoint_url: str
    access_key: str = field(repr=False)
    secret_key: str = field(repr=False)
    credential_source: str


class ConfigurationError(ValueError):
    """Raised when required runtime configuration is missing."""


class OperationFailed(RuntimeError):
    """Raised after a non-retryable error or exhausted transient retries."""

    def __init__(self, message: str, attempts: int) -> None:
        super().__init__(message)
        self.attempts = attempts


def parse_size(size_text: str) -> int:
    """Convert a size such as 1MB or 512KB to bytes."""
    match = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?",
        size_text.strip(),
    )
    if not match:
        raise ValueError(f"Invalid size: {size_text}")

    value = float(match.group(1))
    unit = (match.group(2) or "B").upper()
    units = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
    }
    if unit not in units:
        raise ValueError(f"Unsupported unit: {unit}. Use B, KB, MB, or GB.")

    size_bytes = int(value * units[unit])
    if size_bytes <= 0:
        raise ValueError("File size must be greater than zero.")
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise ValueError("File size must not exceed 1GB for this laptop lab.")
    return size_bytes


def bounded_positive_int(maximum: int) -> Callable[[str], int]:
    """Build an argparse validator for a positive bounded integer."""

    def parse(value: str) -> int:
        try:
            number = int(value)
        except ValueError as error:
            raise argparse.ArgumentTypeError("Expected an integer.") from error
        if number <= 0:
            raise argparse.ArgumentTypeError("Value must be greater than zero.")
        if number > maximum:
            raise argparse.ArgumentTypeError(
                f"Value must not exceed {maximum:,} for this laptop lab."
            )
        return number

    return parse


def size_argument(value: str) -> int:
    """Validate a file-size CLI argument."""
    try:
        return parse_size(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def bucket_argument(value: str) -> str:
    """Validate the subset of S3 bucket naming rules used by this lab."""
    bucket = value.strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
        raise argparse.ArgumentTypeError(
            "Bucket must contain 3-63 lowercase letters, digits, dots, or hyphens."
        )
    if ".." in bucket:
        raise argparse.ArgumentTypeError(
            "Bucket name must not contain consecutive dots."
        )
    return bucket


def validate_workload(
    num_files: int,
    threads: int,
    file_size_bytes: int,
) -> tuple[int, int]:
    """Validate total and concurrently allocated payload sizes."""
    planned_total_bytes = num_files * file_size_bytes
    if planned_total_bytes > MAX_TOTAL_BYTES:
        raise ValueError(
            "Planned workload exceeds 10GiB. "
            "Reduce --num-files or --file-size."
        )

    inflight_bytes = min(threads, num_files) * file_size_bytes
    if inflight_bytes > MAX_INFLIGHT_BYTES:
        raise ValueError(
            "Concurrent in-memory payload exceeds 512MiB. "
            "Reduce --threads or --file-size."
        )
    return planned_total_bytes, inflight_bytes


def load_settings() -> S3Settings:
    """Load endpoint and one complete credential pair without hardcoded secrets."""
    endpoint_url = os.getenv("ENDPOINT_URL", "http://localhost:9000").strip()
    if not endpoint_url:
        raise ConfigurationError("ENDPOINT_URL must not be empty.")

    app_access_key = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    app_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
    if app_access_key or app_secret_key:
        if not app_access_key or not app_secret_key:
            raise ConfigurationError(
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set together."
            )
        return S3Settings(
            endpoint_url=endpoint_url,
            access_key=app_access_key,
            secret_key=app_secret_key,
            credential_source="application",
        )

    root_access_key = os.getenv("MINIO_ROOT_USER", "").strip()
    root_secret_key = os.getenv("MINIO_ROOT_PASSWORD", "").strip()
    if not root_access_key or not root_secret_key:
        raise ConfigurationError(
            "Set application credentials or both MinIO root variables in .env."
        )
    return S3Settings(
        endpoint_url=endpoint_url,
        access_key=root_access_key,
        secret_key=root_secret_key,
        credential_source="root-lab-fallback",
    )


def build_s3_client(settings: S3Settings):
    """Create a client with SDK retries disabled so this script owns retry count."""
    return boto3.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        aws_access_key_id=settings.access_key,
        aws_secret_access_key=settings.secret_key,
        config=Config(
            signature_version="s3v4",
            connect_timeout=3,
            read_timeout=30,
            max_pool_connections=2,
            retries={"mode": "standard", "total_max_attempts": 1},
        ),
    )


def get_thread_client(settings: S3Settings):
    """Reuse one boto3 client per worker thread."""
    client = getattr(thread_state, "s3_client", None)
    if client is None:
        client = build_s3_client(settings)
        thread_state.s3_client = client
    return client


def is_transient_error(error: Exception) -> bool:
    """Return true only for connection failures, timeouts, throttling, or S3 5xx."""
    if isinstance(
        error,
        (
            ConnectionClosedError,
            ConnectTimeoutError,
            EndpointConnectionError,
            ReadTimeoutError,
        ),
    ):
        return True
    if not isinstance(error, ClientError):
        return False

    metadata = error.response.get("ResponseMetadata", {})
    status_code = int(metadata.get("HTTPStatusCode", 0))
    error_code = error.response.get("Error", {}).get("Code", "")
    return (
        status_code >= 500
        or status_code in {408, 429}
        or error_code in TRANSIENT_S3_CODES
    )


def run_with_retry(
    operation: Callable[[], T],
    description: str,
) -> tuple[T, int]:
    """Run an S3 operation at most three times for transient failures."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return operation(), attempt
        except Exception as error:
            if not is_transient_error(error):
                raise OperationFailed(
                    f"{description} failed without retry: {error}",
                    attempts=attempt,
                ) from error
            if attempt == MAX_ATTEMPTS:
                raise OperationFailed(
                    f"{description} failed after {MAX_ATTEMPTS} attempts: {error}",
                    attempts=attempt,
                ) from error

            delay_seconds = 0.5 * (2 ** (attempt - 1))
            logger.warning(
                "%s failed on attempt %d/%d; retrying in %.1fs: %s",
                description,
                attempt,
                MAX_ATTEMPTS,
                delay_seconds,
                error,
            )
            time.sleep(delay_seconds)

    raise AssertionError("Retry loop ended unexpectedly.")


def preflight(settings: S3Settings, bucket_name: str) -> None:
    """Verify endpoint, credentials, and destination bucket before scheduling load."""
    client = build_s3_client(settings)
    run_with_retry(
        lambda: client.head_bucket(Bucket=bucket_name),
        f"Preflight for bucket '{bucket_name}'",
    )


def upload_worker(
    settings: S3Settings,
    bucket_name: str,
    object_prefix: str,
    object_index: int,
    file_size_bytes: int,
) -> dict[str, Any]:
    """Generate one in-memory object and upload it with bounded retries."""
    object_key = (
        f"{object_prefix}/object-{object_index:06d}-{uuid.uuid4().hex}.bin"
    )
    start_time: float | None = None
    attempts = 0

    try:
        payload = os.urandom(file_size_bytes)
        client = get_thread_client(settings)
        # Measure the S3 operation, not local random-payload generation.
        start_time = time.perf_counter()
        _, attempts = run_with_retry(
            lambda: client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=payload,
                Metadata={
                    "generated-by": "load-generator",
                    "object-index": str(object_index),
                },
            ),
            f"Upload object {object_index}",
        )
        return {
            "success": True,
            "latency_ms": (time.perf_counter() - start_time) * 1000,
            "bytes": file_size_bytes,
            "attempts": attempts,
            "error": "",
        }
    except OperationFailed as error:
        attempts = error.attempts
        message = str(error)
    except Exception as error:
        message = f"Unexpected worker error: {error}"

    logger.error("Object %d failed: %s", object_index, message)
    return {
        "success": False,
        "latency_ms": (
            (time.perf_counter() - start_time) * 1000
            if start_time is not None
            else 0.0
        ),
        "bytes": 0,
        "attempts": attempts,
        "error": message,
    }


def percentile(values: list[float], percent: float) -> float:
    """Calculate a linearly interpolated percentile without numpy."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]

    rank = (len(ordered) - 1) * percent / 100
    lower_index = math.floor(rank)
    upper_index = math.ceil(rank)
    if lower_index == upper_index:
        return ordered[lower_index]

    weight = rank - lower_index
    return (
        ordered[lower_index] * (1 - weight)
        + ordered[upper_index] * weight
    )


def git_output(*arguments: str) -> str:
    """Read concise Git metadata without failing outside a Git checkout."""
    try:
        result = subprocess.run(
            ["git", *arguments],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip()


def working_tree_is_dirty() -> bool | str:
    """Report whether runtime code differs from its recorded commit."""
    status = git_output("status", "--porcelain")
    if status == "unknown":
        return "unknown"
    return bool(status)


def total_memory_bytes() -> int | None:
    """Return physical host memory using only the Python standard library."""
    try:
        if os.name == "nt":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong),
                    ("memory_load", ctypes.c_ulong),
                    ("total_physical", ctypes.c_ulonglong),
                    ("available_physical", ctypes.c_ulonglong),
                    ("total_page_file", ctypes.c_ulonglong),
                    ("available_page_file", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong),
                    ("available_virtual", ctypes.c_ulonglong),
                    ("available_extended_virtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.length = ctypes.sizeof(MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(
                ctypes.byref(status)
            ):
                return int(status.total_physical)
            return None

        page_size = os.sysconf("SC_PAGE_SIZE")
        page_count = os.sysconf("SC_PHYS_PAGES")
        return int(page_size * page_count)
    except (AttributeError, OSError, ValueError):
        return None


def host_context() -> dict[str, Any]:
    """Capture host context needed to interpret benchmark results."""
    memory_bytes = total_memory_bytes()
    try:
        disk = shutil.disk_usage(Path.cwd())
    except OSError:
        disk = None

    return {
        "platform": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "memory_gib": (
            round(memory_bytes / (1024**3), 2)
            if memory_bytes is not None
            else "unknown"
        ),
        "disk_total_gib": (
            round(disk.total / (1024**3), 2) if disk is not None else "unknown"
        ),
        "disk_free_gib": (
            round(disk.free / (1024**3), 2) if disk is not None else "unknown"
        ),
    }


def build_report(
    *,
    settings: S3Settings,
    bucket_name: str,
    topology: str,
    object_prefix: str,
    num_files: int,
    threads: int,
    file_size_bytes: int,
    results: list[dict[str, Any]],
    total_duration: float,
) -> dict[str, Any]:
    """Build a report containing workload, context, performance, and failures."""
    successful = [result for result in results if result["success"]]
    failed = [result for result in results if not result["success"]]
    latencies = [result["latency_ms"] for result in successful]
    total_bytes = sum(result["bytes"] for result in successful)
    total_mib = total_bytes / (1024**2)
    success_rate = len(successful) / num_files * 100
    failure_rate = len(failed) / num_files * 100
    error_counts = Counter(result["error"] for result in failed)

    return {
        "schema_version": 1,
        "context": {
            "timestamp_utc": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "branch": git_output("branch", "--show-current"),
            "commit": git_output("rev-parse", "HEAD"),
            "working_tree_dirty": working_tree_is_dirty(),
            "endpoint": settings.endpoint_url,
            "bucket": bucket_name,
            "topology": topology,
            "credential_source": settings.credential_source,
            "object_prefix": object_prefix,
            "host": host_context(),
        },
        "workload": {
            "num_files": num_files,
            "threads": threads,
            "file_size_bytes": file_size_bytes,
            "planned_total_bytes": num_files * file_size_bytes,
            "planned_inflight_bytes": min(threads, num_files)
            * file_size_bytes,
        },
        "performance": {
            "total_duration_sec": round(total_duration, 4),
            "total_uploaded_mib": round(total_mib, 4),
            "average_throughput_mib_s": round(
                total_mib / total_duration if total_duration > 0 else 0,
                4,
            ),
            "success_rate_percent": round(success_rate, 4),
            "failure_rate_percent": round(failure_rate, 4),
            "total_success": len(successful),
            "total_failed": len(failed),
        },
        "latency_ms": {
            "average": round(fmean(latencies), 4) if latencies else 0.0,
            "p95": round(percentile(latencies, 95), 4),
            "p99": round(percentile(latencies, 99), 4),
        },
        "retry": {
            "max_attempts": MAX_ATTEMPTS,
            "requests_retried": sum(
                1 for result in results if result["attempts"] > 1
            ),
        },
        "failures": {
            "by_error": dict(error_counts.most_common(10)),
        },
    }


def write_report(report: dict[str, Any], output_path: Path) -> None:
    """Write JSON output to an explicit path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def print_report(report: dict[str, Any], output_path: Path) -> None:
    """Print the required benchmark summary without exposing credentials."""
    performance = report["performance"]
    latency = report["latency_ms"]
    print("\n" + "=" * 60)
    print("LOAD GENERATOR RESULT")
    print("=" * 60)
    print(
        f"Duration      : {performance['total_duration_sec']:.4f} seconds"
    )
    print(
        "Throughput    : "
        f"{performance['average_throughput_mib_s']:.4f} MiB/s"
    )
    print(
        "Success       : "
        f"{performance['total_success']} "
        f"({performance['success_rate_percent']:.2f}%)"
    )
    print(
        "Failure       : "
        f"{performance['total_failed']} "
        f"({performance['failure_rate_percent']:.2f}%)"
    )
    print(f"Average       : {latency['average']:.4f} ms")
    print(f"P95 / P99     : {latency['p95']:.4f} / {latency['p99']:.4f} ms")
    print(f"Result file   : {output_path}")
    print("=" * 60)


def run_load_generator(
    *,
    settings: S3Settings,
    bucket_name: str,
    topology: str,
    num_files: int,
    threads: int,
    file_size_bytes: int,
    output_path: Path,
) -> int:
    """Run preflight, concurrent uploads, and report generation."""
    logger.info(
        "Preflight endpoint=%s bucket=%s credential_source=%s",
        settings.endpoint_url,
        bucket_name,
        settings.credential_source,
    )
    try:
        preflight(settings, bucket_name)
    except OperationFailed as error:
        logger.error("Ingestion preflight failed: %s", error)
        return 1
    except Exception as error:
        logger.error("Preflight setup failed: %s", error)
        return 1

    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    object_prefix = f"load-test/run_id={run_id}"
    logger.info(
        "Starting load: files=%d threads=%d size=%d prefix=%s",
        num_files,
        threads,
        file_size_bytes,
        object_prefix,
    )

    results: list[dict[str, Any]] = []
    wall_start = time.perf_counter()
    with ThreadPoolExecutor(
        max_workers=threads,
        thread_name_prefix="minio-load",
    ) as executor:
        futures = [
            executor.submit(
                upload_worker,
                settings,
                bucket_name,
                object_prefix,
                object_index,
                file_size_bytes,
            )
            for object_index in range(1, num_files + 1)
        ]
        progress_interval = max(1, num_files // 10)
        for completed, future in enumerate(as_completed(futures), 1):
            try:
                results.append(future.result())
            except Exception as error:
                logger.error("Unexpected future error: %s", error)
                results.append(
                    {
                        "success": False,
                        "latency_ms": 0.0,
                        "bytes": 0,
                        "attempts": 0,
                        "error": f"Unexpected future error: {error}",
                    }
                )
            if completed % progress_interval == 0 or completed == num_files:
                logger.info(
                    "Progress %d/%d (%.1f%%)",
                    completed,
                    num_files,
                    completed / num_files * 100,
                )

    total_duration = time.perf_counter() - wall_start
    report = build_report(
        settings=settings,
        bucket_name=bucket_name,
        topology=topology,
        object_prefix=object_prefix,
        num_files=num_files,
        threads=threads,
        file_size_bytes=file_size_bytes,
        results=results,
        total_duration=total_duration,
    )
    write_report(report, output_path)
    print_report(report, output_path)
    return 0 if report["performance"]["total_failed"] == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Generate concurrent upload load against MinIO through Nginx."
    )
    parser.add_argument(
        "--num-files",
        type=bounded_positive_int(MAX_FILES),
        required=True,
        help=f"Number of objects to upload (maximum {MAX_FILES:,}).",
    )
    parser.add_argument(
        "--threads",
        type=bounded_positive_int(MAX_THREADS),
        required=True,
        help=f"Concurrent worker threads (maximum {MAX_THREADS}).",
    )
    parser.add_argument(
        "--file-size",
        type=size_argument,
        required=True,
        metavar="SIZE",
        help="Object size such as 100KB or 1MB (maximum 1GB).",
    )
    parser.add_argument(
        "--bucket",
        type=bucket_argument,
        default="raw-data",
        help="Existing destination bucket (default: raw-data).",
    )
    parser.add_argument(
        "--topology",
        default="distributed-4-node",
        help="Topology label stored in the JSON report.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark_results.json"),
        help="JSON result path (default: benchmark_results.json).",
    )
    return parser


def main() -> int:
    """CLI entrypoint."""
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()
    try:
        validate_workload(args.num_files, args.threads, args.file_size)
    except ValueError as error:
        parser.error(str(error))

    try:
        settings = load_settings()
    except ConfigurationError as error:
        parser.error(str(error))

    return run_load_generator(
        settings=settings,
        bucket_name=args.bucket,
        topology=args.topology,
        num_files=args.num_files,
        threads=args.threads,
        file_size_bytes=args.file_size,
        output_path=args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
