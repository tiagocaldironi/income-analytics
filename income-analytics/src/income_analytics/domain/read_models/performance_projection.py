"""Read models for portfolio performance over a bounded interval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from income_analytics.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class PerformancePeriod:
    """A TWR subperiod whose return excludes a boundary external flow."""

    start_date: date
    end_date: date
    return_percentage: Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class PerformanceProjection:
    """Portfolio TWR and investor XIRR for a requested date interval."""

    start_date: date
    end_date: date
    beginning_equity: Money | None
    ending_equity: Money | None
    total_contributions: Money
    total_withdrawals: Money
    twr: Decimal | None
    xirr: Decimal | None
    periods: tuple[PerformancePeriod, ...] = ()
    unavailable_reason: str | None = None

    @property
    def net_external_flow(self) -> Money:
        return self.total_contributions - self.total_withdrawals
