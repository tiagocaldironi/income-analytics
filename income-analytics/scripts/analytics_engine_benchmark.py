"""Controlled, sequential analytics endpoint benchmark (read-only)."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any


def nearest_rank(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def fetch(url: str, timeout: float) -> tuple[int, bytes, float]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = response.read()
            return response.status, payload, (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as error:
        payload = error.read()
        return error.code, payload, (time.perf_counter() - started) * 1000


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2026, 8, 1))
    parser.add_argument("--end-date", type=date.fromisoformat, default=date(2026, 8, 31))
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--output", type=Path, default=Path("docs/appendices/performance_v1_1"))
    parser.add_argument("--golden-dir", type=Path)
    args = parser.parse_args()
    period = f"start_date={args.start_date.isoformat()}&end_date={args.end_date.isoformat()}"
    endpoints = {
        "wealth_evolution": f"/api/analytics/wealth-evolution?{period}",
        "wealth_explanation": f"/api/analytics/wealth-explanation?{period}",
        "portfolio_performance": f"/api/portfolio/performance?{period}",
        "performance_comparison": f"/api/analytics/performance-comparison?{period}",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    if args.golden_dir:
        args.golden_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}
    for name, path in endpoints.items():
        statuses: list[int] = []
        timings: list[float] = []
        sizes: list[int] = []
        hashes: list[str] = []
        body = b""
        for _ in range(11):
            status, body, elapsed_ms = fetch(args.base_url + path, args.timeout)
            statuses.append(status)
            timings.append(elapsed_ms)
            sizes.append(len(body))
            hashes.append(hashlib.sha256(body).hexdigest())
        warm = timings[1:]
        item = {
            "endpoint": path,
            "iterations": {"cold": 1, "warm": 10},
            "status_codes": statuses,
            "cold_ms": round(timings[0], 2),
            "warm_min_ms": round(min(warm), 2),
            "warm_median_ms": round(statistics.median(warm), 2),
            "warm_p95_ms": round(nearest_rank(warm, 0.95), 2),
            "warm_max_ms": round(max(warm), 2),
            "response_bytes": max(sizes),
            "response_sha256_per_run": hashes,
        }
        results[name] = item
        if args.golden_dir:
            (args.golden_dir / f"{name}.json").write_bytes(body)
    (args.output / "controlled_benchmark.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    with (args.output / "analytics_payloads.csv").open("w", encoding="utf-8", newline="") as file:
        file.write("endpoint,response_bytes,status,sha256\n")
        for name, result in results.items():
            file.write(
                f"{name},{result['response_bytes']},{result['status_codes'][-1]},"
                f"{result['response_sha256_per_run'][-1]}\n"
            )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
