"""Comparison between current and target class allocation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class AllocationComparison:
    asset_class: AssetClass
    current_weight: Decimal
    target_weight: Decimal
    deviation: Decimal
    current_market_value: Money
    target_market_value: Money
    value_deviation: Money
    status: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioAllocationAnalysis:
    comparisons: tuple[AllocationComparison, ...]
    portfolio_drift: Decimal
    portfolio_drift_value: Money
