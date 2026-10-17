"""Derived comparison between a portfolio return and a named benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class BenchmarkComparisonProjection:
    start_date: date
    end_date: date
    benchmark_name: str
    portfolio_twr: Decimal | None
    benchmark_return: Decimal | None
    observed_rates: int
    unavailable_reason: str | None = None

    @property
    def difference(self) -> Decimal | None:
        if self.portfolio_twr is None or self.benchmark_return is None:
            return None
        return self.portfolio_twr - self.benchmark_return
