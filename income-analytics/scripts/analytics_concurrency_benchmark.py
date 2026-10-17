"""Sequentially ramp controlled concurrent requests against one read endpoint."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path


def request(url: str, timeout: float) -> tuple[float, int, int]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = response.read()
            return (time.perf_counter() - started) * 1000, response.status, len(payload)
    except urllib.error.HTTPError as error:
        payload = error.read()
        return (time.perf_counter() - started) * 1000, error.code, len(payload)


def nearest_rank(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8011/api/portfolio/performance?start_date=2026-08-01&end_date=2026-08-31",
    )
    parser.add_argument("--batches", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/appendices/performance_v1_1/concurrency_benchmark.csv"),
    )
    args = parser.parse_args()
    rows = []
    for concurrency in (1, 2, 4):
        samples: list[float] = []
        batch_times: list[float] = []
        statuses: list[int] = []
        sizes: list[int] = []
        for _ in range(args.batches):
            started = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
                results = list(
                    pool.map(lambda _index: request(args.url, args.timeout), range(concurrency))
                )
            batch_times.append((time.perf_counter() - started) * 1000)
            for elapsed, status, size in results:
                samples.append(elapsed)
                statuses.append(status)
                sizes.append(size)
        row = {
            "concurrent_requests": concurrency,
            "batches": args.batches,
            "requests": len(samples),
            "request_median_ms": round(statistics.median(samples), 2),
            "request_p95_ms": round(nearest_rank(samples, 0.95), 2),
            "request_max_ms": round(max(samples), 2),
            "batch_median_ms": round(statistics.median(batch_times), 2),
            "statuses": statuses,
            "response_bytes": max(sizes),
        }
        rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
