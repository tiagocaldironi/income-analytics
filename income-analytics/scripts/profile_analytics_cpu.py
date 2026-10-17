"""Profile one analytics route callable with cProfile, outside HTTP overhead."""

from __future__ import annotations

import argparse
import cProfile
import csv
import pstats
from datetime import date
from pathlib import Path
from typing import Callable

from income_analytics.api.routers import dashboard

ROUTES: dict[str, Callable[..., object]] = {
    "wealth_evolution": dashboard.get_wealth_evolution,
    "wealth_explanation": dashboard.get_wealth_explanation,
    "portfolio_performance": dashboard.get_portfolio_performance,
    "performance_comparison": dashboard.get_performance_comparison,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", choices=tuple(ROUTES))
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2026, 8, 1))
    parser.add_argument("--end-date", type=date.fromisoformat, default=date(2026, 8, 31))
    parser.add_argument(
        "--output", type=Path, default=Path("docs/appendices/performance_v1_1/profiles")
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    profile = cProfile.Profile()
    profile.enable()
    ROUTES[args.endpoint](start_date=args.start_date, end_date=args.end_date)
    profile.disable()
    stats_path = args.output / f"{args.endpoint}.pstats"
    profile.dump_stats(stats_path)
    stats = pstats.Stats(profile)
    total_time = stats.total_tt or 0.0
    rows = []
    for (filename, line, function), (
        primitive,
        calls,
        self_time,
        cumulative,
        _callers,
    ) in stats.stats.items():
        rows.append(
            {
                "function": f"{Path(filename).name}:{line}:{function}",
                "calls": calls,
                "self_time_ms": self_time * 1000,
                "cumulative_time_ms": cumulative * 1000,
                "avg_self_time_ms": self_time * 1000 / calls if calls else 0,
                "percent_total": self_time / total_time * 100 if total_time else 0,
                "primitive_calls": primitive,
            }
        )
    rows.sort(key=lambda row: row["self_time_ms"], reverse=True)
    with (args.output / f"{args.endpoint}_cpu.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"profile={stats_path} total_ms={total_time * 1000:.2f} functions={len(rows)}")
    for row in sorted(rows, key=lambda item: item["cumulative_time_ms"], reverse=True)[:30]:
        print(
            f"{row['function']} calls={row['calls']} self_ms={row['self_time_ms']:.2f} "
            f"cumulative_ms={row['cumulative_time_ms']:.2f} "
            f"avg_self_ms={row['avg_self_time_ms']:.4f}"
        )


if __name__ == "__main__":
    main()
