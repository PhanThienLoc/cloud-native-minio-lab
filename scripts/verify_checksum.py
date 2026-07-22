from __future__ import annotations

import hashlib
from pathlib import Path


def checksum(path: Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> None:
    sample = Path(__file__).with_name("sample.txt")
    if not sample.exists():
        sample.write_text("sample payload\n", encoding="utf-8")
    print(checksum(sample))


if __name__ == "__main__":
    main()
