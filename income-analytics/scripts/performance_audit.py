from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def requests_for_period(start: date, end: date) -> dict[str, list[str]]:
    period = f"start_date={start.isoformat()}&end_date={end.isoformat()}"
    return {
        "Dashboard": ["/api/portfolio/dashboard"],
        "Minha Carteira": ["/api/portfolio/dashboard", "/api/portfolio/intelligence"],
        "Operações": [
            "/api/operations/history?page=1&page_size=25",
            "/api/recurring-rules",
            "/api/imports/b3/history?offset=0&page_size=20",
        ],
        "Rendimentos": ["/api/settings/paid-income"],
        "Entender": [
            f"/api/analytics/wealth-explanation?{period}",
            f"/api/analytics/wealth-evolution?{period}",
            f"/api/analytics/performance-comparison?{period}",
        ],
        "Evolução": ["/api/portfolio/history?period_months=12"],
        "Performance": [f"/api/portfolio/performance?{period}"],
        "Fórmula Mágica": [
            "/api/tools/magic-formula/stocks?q=&exclude_retail=false&exclude_aviation=false&page=1&page_size=25"
        ],
        "Detalhe de ativo": ["/api/portfolio/holdings"],
        "Configurações": [
            "/api/data-sources",
            "/api/settings/paid-income",
            "/api/market-prices/refresh-runs?limit=20",
            "/api/portfolio/configuration",
        ],
    }


def run_endpoint(
    base_url: str, path: str, *, runs: int, timeout: float
) -> dict[str, Any]:
    times: list[float] = []
    sizes: list[int] = []
    statuses: list[int] = []
    errors: list[str] = []
    for _ in range(runs):
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(base_url + path, timeout=timeout) as response:
                payload = response.read()
                statuses.append(response.status)
                sizes.append(len(payload))
        except urllib.error.HTTPError as error:
            payload = error.read()
            statuses.append(error.code)
            sizes.append(len(payload))
            errors.append(payload.decode("utf-8", errors="replace")[:500])
        except Exception as error:  # noqa: BLE001 - report benchmark failures as data
            statuses.append(0)
            sizes.append(0)
            errors.append(f"{type(error).__name__}: {error}")
        times.append((time.perf_counter() - started) * 1000)
    warm = times[1:] or times
    return {
        "endpoint": path,
        "runs": runs,
        "first_ms": round(times[0], 2),
        "warm_p50_ms": round(statistics.median(warm), 2),
        "warm_p95_ms": round(percentile(warm, 0.95), 2),
        "max_ms": round(max(times), 2),
        "response_bytes": max(sizes, default=0),
        "status": statuses[-1],
        "errors": errors[:1],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only local API performance audit; never invokes refresh or write routes."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--runs", type=int, default=7)
    parser.add_argument("--timeout", type=float, default=35)
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date", type=date.fromisoformat, default=date.today())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/appendices/performance_v1"),
    )
    args = parser.parse_args()
    start = args.start_date or (args.end_date - timedelta(days=30))
    args.output.mkdir(parents=True, exist_ok=True)

    screens: dict[str, list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    for screen, paths in requests_for_period(start, args.end_date).items():
        measured = []
        for path in paths:
            frequent = {"Dashboard", "Minha Carteira", "Operações", "Rendimentos"}
            route_runs = args.runs if screen in frequent else max(2, min(3, args.runs))
            result = run_endpoint(
                args.base_url.rstrip("/"), path, runs=route_runs, timeout=args.timeout
            )
            item = {"screen": screen, **result}
            measured.append(item)
            rows.append(item)
            print(json.dumps(item, ensure_ascii=False), flush=True)
        screens[screen] = measured

    output = {
        "captured_at": datetime.now().astimezone().isoformat(),
        "measurement_basis": "direct read-only HTTP API; not browser render time",
        "base_url": args.base_url,
        "database_path": "INCOME_ANALYTICS_DATABASE (default income_analytics.db)",
        "database_size_bytes": Path("income_analytics.db").stat().st_size
        if Path("income_analytics.db").exists()
        else None,
        "period": {"start": start.isoformat(), "end": args.end_date.isoformat()},
        "runs": args.runs,
        "screens": screens,
    }
    (args.output / "system_baseline.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (args.output / "endpoint_benchmarks_before_after.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "screen",
                "endpoint",
                "runs",
                "before_p50_ms",
                "before_p95_ms",
                "after_p50_ms",
                "after_p95_ms",
                "query_before",
                "query_after",
                "response_bytes",
                "status",
            ],
        )
        writer.writeheader()
        for item in rows:
            writer.writerow(
                {
                    "screen": item["screen"],
                    "endpoint": item["endpoint"],
                    "runs": item["runs"],
                    "after_p50_ms": item["warm_p50_ms"],
                    "after_p95_ms": item["warm_p95_ms"],
                    "response_bytes": item["response_bytes"],
                    "status": item["status"],
                }
            )


if __name__ == "__main__":
    main()
