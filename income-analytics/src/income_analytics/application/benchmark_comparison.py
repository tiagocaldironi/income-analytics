"""Build one persisted-data-only read model for Entender performance."""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Callable

from income_analytics.application.benchmark_data import BenchmarkObservation
from income_analytics.application.performance_coverage import GOOD_COVERAGE, MINIMUM_COVERAGE
from income_analytics.domain.benchmark_rate import BenchmarkRate
from income_analytics.domain.read_models.performance_projection import PerformanceProjection

BENCHMARKS = ("CDI", "IBOV", "IFIX", "IPCA")


def _benchmark_return(
    observations: tuple[BenchmarkObservation, ...],
    *,
    start_date: date,
    end_date: date,
) -> Decimal | None:
    before = [item for item in observations if item.effective_date <= start_date]
    selected = [item for item in observations if start_date < item.effective_date <= end_date]
    if not selected:
        return None
    nature = selected[0].nature
    if nature == "INDEX_LEVEL":
        base = before[-1].value if before else selected[0].value
        ending = selected[-1].value
        return ending / base - Decimal("1") if base > 0 else None
    factor = Decimal("1")
    for item in selected:
        if item.nature != nature:
            return None
        factor *= Decimal("1") + item.value
    return factor - Decimal("1")


def _bucket_periods(
    start_date: date, end_date: date, *, annual: bool
) -> tuple[tuple[date, date], ...]:
    if annual:
        return tuple(
            (max(start_date, date(year, 1, 1)), min(end_date, date(year, 12, 31)))
            for year in range(start_date.year, end_date.year + 1)
        )
    result: list[tuple[date, date]] = []
    year, month = start_date.year, start_date.month
    while date(year, month, 1) <= end_date:
        low = date(year, month, 1)
        high = date(year, month, monthrange(year, month)[1])
        result.append((max(start_date, low), min(end_date, high)))
        if month == 12:
            month, year = 1, year + 1
        else:
            month += 1
    return tuple(result)


def build_performance_comparison(
    *,
    start_date: date,
    end_date: date,
    rates: tuple[BenchmarkRate, ...],
    observations: dict[str, tuple[BenchmarkObservation, ...]],
    performance_at: Callable[[date, date], PerformanceProjection],
) -> dict[str, object]:
    """Return portfolio and benchmark comparisons without making provider calls."""
    normalized: dict[str, tuple[BenchmarkObservation, ...]] = {
        name: tuple(sorted(observations.get(name, ()), key=lambda item: item.effective_date))
        for name in BENCHMARKS
        if name != "CDI"
    }
    normalized["CDI"] = tuple(
        BenchmarkObservation(
            benchmark="CDI",
            effective_date=rate.effective_date,
            value=rate.return_percentage,
            nature="PERIODIC_RATE",
            source="bcb",
        )
        for rate in sorted(rates, key=lambda item: item.effective_date)
        if rate.name.upper() == "CDI"
    )
    performance = performance_at(start_date, end_date)
    benchmarks: list[dict[str, object]] = []
    for code in BENCHMARKS:
        series = normalized[code]
        eligible = [item for item in series if item.effective_date <= end_date]
        latest = eligible[-1] if eligible else None
        result = _benchmark_return(series, start_date=start_date, end_date=end_date)
        status = "UNAVAILABLE" if result is None else "OK"
        if latest is not None and (end_date - latest.effective_date).days > (
            45 if code == "IPCA" else 7
        ):
            status = "STALE" if result is not None else "UNAVAILABLE"
        benchmarks.append(
            {
                "code": code,
                "return": result,
                "excess_return": (
                    performance.twr - result
                    if performance.twr is not None and result is not None
                    else None
                ),
                "last_observation": latest.effective_date if latest else None,
                "status": status,
                "frequency": "MONTHLY" if code == "IPCA" else "DAILY",
            }
        )

    # Sample at the last available observation of each month. The chart remains
    # time-aligned without recalculating the whole portfolio once per trading day.
    month_ends: dict[tuple[int, int], date] = {}
    for values in normalized.values():
        for item in values:
            if start_date < item.effective_date <= end_date:
                key = (item.effective_date.year, item.effective_date.month)
                month_ends[key] = max(month_ends.get(key, item.effective_date), item.effective_date)
    observed_dates = sorted({start_date, end_date, *month_ends.values()})
    series_rows: list[dict[str, object]] = []
    for observed_date in observed_dates:
        portfolio_result = (
            None if observed_date == start_date else performance_at(start_date, observed_date)
        )
        row: dict[str, object] = {
            "date": observed_date,
            "portfolio": Decimal("0") if portfolio_result is None else portfolio_result.twr,
        }
        for code in BENCHMARKS:
            row[code.lower()] = (
                Decimal("0")
                if observed_date == start_date
                else _benchmark_return(
                    normalized[code], start_date=start_date, end_date=observed_date
                )
            )
        series_rows.append(row)

    def table(annual: bool) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for low, high in _bucket_periods(start_date, end_date, annual=annual):
            portfolio_return = performance_at(low, high).twr
            rows.append(
                {
                    "year": low.year,
                    "month": None if annual else low.month,
                    "portfolio": portfolio_return,
                    **{
                        code.lower(): _benchmark_return(
                            normalized[code], start_date=low, end_date=high
                        )
                        for code in BENCHMARKS
                    },
                }
            )
        return rows

    coverage_status = (
        "INSUFFICIENT"
        if performance.coverage_ratio is not None and performance.coverage_ratio < MINIMUM_COVERAGE
        else "PARTIAL"
        if performance.coverage_ratio is not None and performance.coverage_ratio < GOOD_COVERAGE
        else "GOOD"
        if performance.coverage_ratio is not None
        else "UNKNOWN"
    )
    return {
        "period": {"start": start_date, "end": end_date},
        "portfolio": {
            "return": performance.twr,
            "status": performance.performance_status,
            "coverage": performance.coverage_ratio,
            "missing_assets": performance.missing_assets,
            "missing_value": performance.missing_value.amount,
            "missing_periods": performance.missing_periods,
            "unavailable_reason": performance.unavailable_reason,
        },
        "benchmarks": benchmarks,
        "series": series_rows,
        "monthly_returns": table(False),
        "annual_returns": table(True),
        "coverage": {"ratio": performance.coverage_ratio, "status": coverage_status},
    }
