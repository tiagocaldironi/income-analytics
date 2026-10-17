"""Measure 1x/2x/4x chronological projection growth from real read-only data."""

from __future__ import annotations

import argparse
import csv
import statistics
import time
from datetime import date, timedelta
from pathlib import Path

from income_analytics.api.routers.dashboard import session
from income_analytics.domain.projectors.portfolio_projector import PortfolioProjector


def business_dates(start: date, count: int) -> tuple[date, ...]:
    dates: list[date] = []
    current = start
    while len(dates) < count:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return tuple(dates)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/appendices/performance_v1_1/scaling_benchmark.csv"),
    )
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    events = tuple(session.history())
    prices = tuple(session._market_prices)
    if not events or not prices:
        raise SystemExit("Real portfolio ledger/prices are required for this scaling audit.")
    rows = []
    start = min(event.effective_date for event in events)
    for factor in (1, 2, 4):
        scaled_events = events * factor
        scaled_prices = prices * factor
        dates = business_dates(start, 21 * factor)
        samples = []
        for _ in range(args.repeats):
            before = time.perf_counter()
            PortfolioProjector.project_timeline(
                scaled_events,
                scaled_prices,
                dates,
                market_data_available=True,
            )
            samples.append((time.perf_counter() - before) * 1000)
        rows.append(
            {
                "scale": f"{factor}x",
                "events": len(scaled_events),
                "prices": len(scaled_prices),
                "valuation_dates": len(dates),
                "median_ms": round(statistics.median(samples), 2),
                "samples_ms": ";".join(f"{value:.2f}" for value in samples),
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("\n".join(str(row) for row in rows))


if __name__ == "__main__":
    main()
