from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.config import Config
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

ENDPOINT_URL = os.getenv("ENDPOINT_URL", "http://localhost:9000")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

ACCESS_KEY = (
    os.getenv("AWS_ACCESS_KEY_ID")
    or os.getenv("MINIO_ROOT_USER")
    or "minioadmin"
)

SECRET_KEY = (
    os.getenv("AWS_SECRET_ACCESS_KEY")
    or os.getenv("MINIO_ROOT_PASSWORD")
    or "minioadmin123"
)

BUCKET = "raw-data"
PREFIX = "load-test/"
WORKERS = 8
DOWNLOAD_COUNT = 100


def create_client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name=REGION,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def download_object(key: str) -> str:
    s3 = create_client()
    response = s3.get_object(Bucket=BUCKET, Key=key)

    while response["Body"].read(1024 * 1024):
        pass

    response["Body"].close()
    return key


def main():
    s3 = create_client()

    print("=" * 60)
    print("MINIO DOWNLOAD LOAD TEST")
    print("=" * 60)
    print(f"Endpoint : {ENDPOINT_URL}")
    print(f"Bucket   : {BUCKET}")
    print(f"Workers  : {WORKERS}")

    keys = []

    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(
        Bucket=BUCKET,
        Prefix=PREFIX,
    ):
        for item in page.get("Contents", []):
            keys.append(item["Key"])

    if not keys:
        print("[ERROR] No load-test objects found.")
        return

    keys = keys[:DOWNLOAD_COUNT]

    print(f"Objects  : {len(keys)}")
    print()

    success = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [
            executor.submit(download_object, key)
            for key in keys
        ]

        for future in as_completed(futures):
            try:
                key = future.result()
                success += 1
                print(f"[PASS] {key}")
            except Exception as error:
                failed += 1
                print(f"[FAIL] {error}")

    print()
    print("=" * 60)
    print("DOWNLOAD TEST SUMMARY")
    print("=" * 60)
    print(f"Total   : {len(keys)}")
    print(f"Success : {success}")
    print(f"Failed  : {failed}")
    print("=" * 60)


if __name__ == "__main__":
    main()