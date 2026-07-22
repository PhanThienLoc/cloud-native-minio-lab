from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor


def task(index: int) -> str:
    return f"generated-load-{index}"


def main() -> None:
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(task, range(16)))
    print("\n".join(results))


if __name__ == "__main__":
    main()
