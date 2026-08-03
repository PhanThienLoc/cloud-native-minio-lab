from __future__ import annotations

import argparse
import csv
import os
import random
from pathlib import Path

from faker import Faker
from tqdm import tqdm

fake = Faker()
DEFAULT_OUTPUT_DIR = Path(__file__).with_name("sample_data")


def generate_logs(path: Path, target_size_mb: int) -> None:
    """Generate a text log file for MinIO upload tests."""
    target_bytes = target_size_mb * 1024 * 1024
    current_bytes = 0

    with path.open("w", encoding="utf-8") as handle:
        with tqdm(total=target_bytes, unit="B", unit_scale=True, desc="Logs") as pbar:
            while current_bytes < target_bytes:
                log_entry = (
                    f"{fake.date_time_this_year()} [{fake.http_method()}] "
                    f"- {fake.ipv4_private()} "
                    f"- Status: {random.choice([200, 404, 500])}\n"
                )
                handle.write(log_entry)
                bytes_written = len(log_entry.encode("utf-8"))
                current_bytes += bytes_written
                pbar.update(bytes_written)


def generate_csv(path: Path, target_size_mb: int) -> None:
    """Generate structured CSV data for object storage tests."""
    target_bytes = target_size_mb * 1024 * 1024
    current_bytes = 0

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ID", "Name", "Email", "Job", "Address", "Created_At"])

        with tqdm(total=target_bytes, unit="B", unit_scale=True, desc="CSV") as pbar:
            while current_bytes < target_bytes:
                row = [
                    fake.uuid4(),
                    fake.name(),
                    fake.email(),
                    fake.job(),
                    fake.address().replace("\n", " "),
                    fake.iso8601(),
                ]
                writer.writerow(row)
                bytes_written = len(",".join(row).encode("utf-8")) + 2
                current_bytes += bytes_written
                pbar.update(bytes_written)


def generate_dummy_binary(folder_path: Path, count: int, size_kb: int) -> None:
    """Generate binary dummy files to simulate small image objects."""
    folder_path.mkdir(parents=True, exist_ok=True)

    for index in tqdm(range(count), desc="Binary files"):
        file_path = folder_path / f"image_dummy_{index + 1}.bin"
        file_path.write_bytes(os.urandom(size_kb * 1024))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate sample data for MinIO lab tests.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--log-size-mb", type=int, default=30)
    parser.add_argument("--csv-size-mb", type=int, default=30)
    parser.add_argument("--binary-count", type=int, default=100)
    parser.add_argument("--binary-size-kb", type=int, default=200)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    generate_logs(output_dir / "system_logs.log", args.log_size_mb)
    generate_csv(output_dir / "user_data.csv", args.csv_size_mb)
    generate_dummy_binary(output_dir / "dummy_images", args.binary_count, args.binary_size_kb)

    print(f"Generated sample dataset at: {output_dir}")


if __name__ == "__main__":
    main()


#Chạy script (từ thư mục gốc của repo):
#python scripts/generate_data.py

#Cài dependencies:
#python -m pip install -r scripts/requirements.txt
