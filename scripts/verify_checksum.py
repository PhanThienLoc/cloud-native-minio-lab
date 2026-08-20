from __future__ import annotations

import argparse
import hashlib
import os
import random
from pathlib import Path
import tempfile

import boto3
from botocore.config import Config
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

ENDPOINT_URL = os.getenv("ENDPOINT_URL", "http://localhost:9000")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
DEFAULT_BUCKET = "raw-data"


def get_s3_client():
    access_key = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("MINIO_ROOT_USER")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("MINIO_ROOT_PASSWORD")

    if not access_key or not secret_key:
        raise RuntimeError("Missing MinIO credentials in .env")

    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=REGION,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def list_objects(s3, bucket: str) -> list[str]:
    keys = []

    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            key = item["Key"]

            if not key.endswith("/"):
                keys.append(key)

    return keys


def find_local_file(local_dir: Path, object_key: str) -> Path | None:
    filename = Path(object_key).name

    matches = list(local_dir.rglob(filename))

    if len(matches) == 1:
        return matches[0]

    return None


def verify_file(
    s3,
    bucket: str,
    object_key: str,
    local_file: Path,
    download_dir: Path,
) -> bool:

    downloaded_file = download_dir / Path(object_key).name

    try:
        local_hash = sha256_file(local_file)

        s3.download_file(
            bucket,
            object_key,
            str(downloaded_file),
        )

        downloaded_hash = sha256_file(downloaded_file)

        result = local_hash == downloaded_hash

        print(
            f"[{'PASS' if result else 'FAIL'}] "
            f"{object_key}"
        )

        if not result:
            print(f"       Local    : {local_hash}")
            print(f"       Download : {downloaded_hash}")

        return result

    except Exception as error:
        print(f"[FAIL] {object_key}")
        print(f"       Error: {error}")
        return False

    finally:
        if downloaded_file.exists():
            downloaded_file.unlink()


def main() -> int:

    parser = argparse.ArgumentParser(
        description="Verify SHA256 integrity between local dataset and MinIO."
    )

    parser.add_argument(
        "--local-dir",
        default=str(ROOT_DIR / "scripts" / "sample_data"),
        help="Local dataset directory.",
    )

    parser.add_argument(
        "--bucket",
        default=DEFAULT_BUCKET,
        help="MinIO bucket.",
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=50,
        help="Number of random files to verify.",
    )

    args = parser.parse_args()

    local_dir = Path(args.local_dir)

    if not local_dir.exists():
        print(f"[ERROR] Dataset not found: {local_dir}")
        return 1

    print("=" * 60)
    print("MINIO CHECKSUM VERIFICATION")
    print("=" * 60)
    print(f"Endpoint : {ENDPOINT_URL}")
    print(f"Bucket   : {args.bucket}")
    print(f"Dataset  : {local_dir}")
    print(f"Samples  : {args.samples}")
    print()

    try:
        s3 = get_s3_client()
        s3.head_bucket(Bucket=args.bucket)
    except Exception as error:
        print(f"[ERROR] Cannot connect to MinIO: {error}")
        return 1

    objects = list_objects(s3, args.bucket)

    if not objects:
        print("[ERROR] No objects found in bucket.")
        return 1

    candidates = []

    for object_key in objects:
        local_file = find_local_file(local_dir, object_key)

        if local_file:
            candidates.append((object_key, local_file))

    if not candidates:
        print("[ERROR] No matching local files found.")
        return 1

    sample_count = min(args.samples, len(candidates))

    selected = random.sample(candidates, sample_count)

    passed = 0
    failed = 0

    with tempfile.TemporaryDirectory(prefix="checksum_") as temp_dir:

        download_dir = Path(temp_dir)

        for object_key, local_file in selected:

            if verify_file(
                s3,
                args.bucket,
                object_key,
                local_file,
                download_dir,
            ):
                passed += 1
            else:
                failed += 1

    total = passed + failed

    integrity = (
        passed / total * 100
        if total
        else 0
    )

    print()
    print("=" * 60)
    print("CHECKSUM SUMMARY")
    print("=" * 60)
    print(f"Total checked : {total}")
    print(f"PASS          : {passed}")
    print(f"FAIL          : {failed}")
    print(f"Integrity     : {integrity:.2f}%")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())