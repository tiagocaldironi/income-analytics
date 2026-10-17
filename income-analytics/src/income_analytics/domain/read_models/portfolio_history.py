"""Derived snapshots that describe the evolution of a portfolio."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from income_analytics.domain.read_models.portfolio_projection import (
    PortfolioProjection,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioSnapshot:
    """A portfolio projection at the end of an effective date."""

    effective_date: date
    portfolio: PortfolioProjection


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioHistory:
    """An ordered collection of derived portfolio snapshots."""

    snapshots: tuple[PortfolioSnapshot, ...]
