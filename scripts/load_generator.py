import argparse
import io
import json
import logging
import os
import re
import time
import uuid
import numpy as np
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Tải biến môi trường từ .env
load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("load_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_size(size_str: str) -> int:
    """Chuyển đổi tham số kích thước (vd: 1MB, 512KB, 100B) sang số byte."""
    match = re.match(r"^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?$", size_str.strip())
    if not match:
        raise ValueError(f"Định dạng dung lượng không hợp lệ: {size_str}")
    value, unit = float(match.group(1)), (match.group(2) or "B").upper()
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    if unit not in units:
        raise ValueError(f"Đơn vị không hỗ trợ: {unit}. Chọn B, KB, MB, hoặc GB.")
    return int(value * units[unit])

def get_s3_client(max_connections: int = 100):
    """Khởi tạo S3 client tối ưu Connection Pool cho đa luồng."""
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ROOT_USER,
        aws_secret_access_key=MINIO_ROOT_PASSWORD,
        config=Config(
            signature_version="s3v4",
            max_pool_connections=max_connections,
            connect_timeout=10,
            read_timeout=30
        )
    )

def upload_worker(bucket_name: str, file_size_bytes: int, max_retries: int = 3) -> dict:
    """Worker sinh dữ liệu trực tiếp trong RAM và upload kèm cơ chế Retry Exponential Backoff."""
    client = get_s3_client()
    object_key = f"load-test/year=2026/month=08/load_{uuid.uuid4().hex}.bin"
    dummy_payload = os.urandom(file_size_bytes)
    
    start_time = time.perf_counter()
    attempts = 0
    success = False
    last_error = ""

    while attempts < max_retries and not success:
        attempts += 1
        try:
            client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=io.BytesIO(dummy_payload),
                Metadata={"generated-by": "load_generator", "size": str(file_size_bytes)}
            )
            success = True
        except (ClientError, EndpointConnectionError, Exception) as err:
            last_error = str(err)
            if attempts < max_retries:
                backoff_delay = 0.5 * (2 ** (attempts - 1))
                logger.warning(f"Thử lại request ({attempts}/{max_retries}) sau {backoff_delay}s. Lỗi: {last_error}")
                time.sleep(backoff_delay)
            else:
                logger.error(f"Thất bại vĩnh viễn Object {object_key} sau {max_retries} lần thử: {last_error}")

    latency_ms = (time.perf_counter() - start_time) * 1000
    return {
        "success": success,
        "latency_ms": latency_ms,
        "bytes": file_size_bytes if success else 0,
        "attempts": attempts
    }

def run_load_generator(num_files: int, threads: int, file_size_str: str, bucket_name: str):
    file_size_bytes = parse_size(file_size_str)
    
    print("\n" + "="*50)
    print(" BẮT ĐẦU CHẠY TẢI (LOAD GENERATOR)")
    print("="*50)
    print(f" Target Bucket : {bucket_name}")
    print(f" Tổng file     : {num_files}")
    print(f" Số luồng      : {threads}")
    print(f" Dung lượng    : {file_size_str} ({file_size_bytes} Bytes)")
    print(f" Endpoint      : {MINIO_ENDPOINT}")
    print("="*50 + "\n")

    results = []
    wall_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [
            executor.submit(upload_worker, bucket_name, file_size_bytes)
            for _ in range(num_files)
        ]
        
        for idx, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if idx % max(1, num_files // 10) == 0 or idx == num_files:
                progress = (idx / num_files) * 100
                print(f"[*] Tiến độ: {idx}/{num_files} ({progress:.1f}%)")

    total_duration = time.perf_counter() - wall_start
    generate_benchmark_report(results, total_duration, num_files, threads, file_size_str)

def generate_benchmark_report(results: list, total_duration: float, num_files: int, threads: int, file_size_str: str):
    """Tính toán latency, throughput, percentile và lưu kết quả JSON."""
    success_requests = [r for r in results if r["success"]]
    failed_requests = [r for r in results if not r["success"]]
    
    latencies = [r["latency_ms"] for r in success_requests]
    total_bytes_sent = sum(r["bytes"] for r in success_requests)
    
    total_data_mb = total_bytes_sent / (1024 * 1024)
    throughput_mb_s = total_data_mb / total_duration if total_duration > 0 else 0
    
    avg_latency = float(np.mean(latencies)) if latencies else 0.0
    p95_latency = float(np.percentile(latencies, 95)) if latencies else 0.0
    p99_latency = float(np.percentile(latencies, 99)) if latencies else 0.0
    success_rate = (len(success_requests) / num_files) * 100 if num_files > 0 else 0.0

    report = {
        "metadata": {
            "num_files": num_files,
            "threads": threads,
            "file_size": file_size_str,
            "timestamp": int(time.time())
        },
        "performance": {
            "total_duration_sec": round(total_duration, 2),
            "total_data_uploaded_mb": round(total_data_mb, 2),
            "average_throughput_mb_s": round(throughput_mb_s, 2),
            "success_rate_percent": round(success_rate, 2),
            "total_success": len(success_requests),
            "total_failed": len(failed_requests)
        },
        "latency_ms": {
            "average": round(avg_latency, 2),
            "p95": round(p95_latency, 2),
            "p99": round(p99_latency, 2)
        }
    }

    print("\n" + "="*50)
    print(" KẾT QUẢ TỔNG KẾT (BENCHMARK REPORT)")
    print("="*50)
    print(f"Tổng thời gian chạy (Total Duration) : {report['performance']['total_duration_sec']} s")
    print(f"Tổng dung lượng nạp                   : {report['performance']['total_data_uploaded_mb']} MB")
    print(f"Tốc độ trung bình (Throughput)       : {report['performance']['average_throughput_mb_s']} MB/s")
    print(f"Tỷ lệ thành công (Success Rate)      : {report['performance']['success_rate_percent']}% ({len(success_requests)} OK, {len(failed_requests)} Fail)")
    print(f"Độ trễ trung bình (Avg Latency)      : {report['latency_ms']['average']} ms")
    print(f"Độ trễ Percentile 95 (P95)           : {report['latency_ms']['p95']} ms")
    print(f"Độ trễ Percentile 99 (P99)           : {report['latency_ms']['p99']} ms")
    print("="*50)

    output_filename = "benchmark_results.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    print(f"[>] Đã lưu file kết quả: {output_filename}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MinIO Distributed Load Testing Tool")
    parser.add_argument("--num-files", type=int, required=True, help="Số lượng file cần upload (vd: 5000)")
    parser.add_argument("--threads", type=int, required=True, help="Số luồng chạy song song (vd: 8)")
    parser.add_argument("--file-size", type=str, required=True, help="Kích thước mỗi file (vd: 1MB, 512KB)")
    parser.add_argument("--bucket", type=str, default="raw-data", help="Tên bucket đích (mặc định: raw-data)")

    args = parser.parse_args()
    run_load_generator(args.num_files, args.threads, args.file_size, args.bucket)