"""Read models for portfolio risk metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioReturn:
    """One observed, external-flow-neutral portfolio return."""

    effective_date: date
    return_percentage: Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class DrawdownPoint:
    """One point in the normalized wealth drawdown series."""

    effective_date: date
    drawdown: Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class RiskProjection:
    """Risk metrics derived from a consistent periodic return series."""

    start_date: date
    end_date: date
    frequency: str
    returns: tuple[PortfolioReturn, ...]
    drawdown_series: tuple[DrawdownPoint, ...]
    periodic_volatility: Decimal | None
    annualized_volatility: Decimal | None
    maximum_drawdown: Decimal | None
    peak_date: date | None
    trough_date: date | None
    recovery_date: date | None
    sharpe_ratio: Decimal | None
    sharpe_unavailable_reason: str | None = None
