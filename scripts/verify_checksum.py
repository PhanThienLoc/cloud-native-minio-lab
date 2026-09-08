from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

def checksum(path: Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def credentials() -> tuple[str, str]:
    access_key = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("MINIO_ROOT_USER")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("MINIO_ROOT_PASSWORD")
    if not access_key or not secret_key:
        raise ValueError(
            "Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or "
            "MINIO_ROOT_USER/MINIO_ROOT_PASSWORD"
        )
    if access_key.startswith("change-me") or secret_key.startswith("change-me"):
        raise ValueError("Replace placeholder credentials before running checksum verification")
    return access_key, secret_key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download matching MinIO objects and compare their SHA256 checksums."
    )
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument(
        "--endpoint-url",
        default=os.getenv("ENDPOINT_URL", "http://localhost:9000"),
    )
    parser.add_argument("--prefix", default="", help="Optional object-key prefix")
    parser.add_argument("--download-dir", type=Path, help="Keep downloaded files here")
    parser.add_argument("--max-files", type=int, help="Verify only the first N files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = args.source_dir.resolve()
    if not source_dir.is_dir():
        print(f"ERROR: source directory does not exist: {source_dir}", file=sys.stderr)
        return 2
    if args.max_files is not None and args.max_files < 1:
        print("ERROR: --max-files must be positive", file=sys.stderr)
        return 2

    try:
        access_key, secret_key = credentials()
        client = boto3.client(
            "s3",
            endpoint_url=args.endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            config=Config(s3={"addressing_style": "path"}),
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    files = sorted(path for path in source_dir.rglob("*") if path.is_file())
    if args.max_files:
        files = files[: args.max_files]
    if not files:
        print("ERROR: no source files found", file=sys.stderr)
        return 2

    temporary = args.download_dir is None
    download_root = args.download_dir.resolve() if args.download_dir else None
    with tempfile.TemporaryDirectory(prefix="minio-checksum-") as temp_dir:
        root = download_root or Path(temp_dir)
        root.mkdir(parents=True, exist_ok=True)
        passed = 0
        failed = 0
        for source in files:
            relative = source.relative_to(source_dir).as_posix()
            object_name = f"{args.prefix.rstrip('/')}/{relative}" if args.prefix else relative
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                client.download_file(args.bucket, object_name, str(destination))
                source_hash = checksum(source)
                downloaded_hash = checksum(destination)
                if source_hash != downloaded_hash:
                    failed += 1
                    print(f"FAIL {relative}: SHA256 mismatch")
                    continue
                passed += 1
                print(f"PASS {relative}: {source_hash}")
            except (BotoCoreError, ClientError, OSError) as error:
                failed += 1
                print(f"FAIL {relative}: {error}")

    total = passed + failed
    integrity = (passed / total * 100) if total else 0.0
    print(f"SUMMARY checked={total} passed={passed} failed={failed} integrity={integrity:.2f}%")
    if temporary:
        print("Downloaded files were removed after verification.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
