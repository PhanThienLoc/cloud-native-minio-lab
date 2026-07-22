from __future__ import annotations

from pathlib import Path

PARTITION_PATH = Path("year=2026/month=07")


def main() -> None:
    target = PARTITION_PATH / "sample.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("sample payload\n", encoding="utf-8")
    print(f"Prepared partitioned data at {target}")


if __name__ == "__main__":
    main()
