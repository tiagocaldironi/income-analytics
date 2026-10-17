"""Allocation and economic-result contribution read models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from income_analytics.domain.read_models.position_projection import PositionProjection
from income_analytics.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetAllocation:
    """Current exposure and historical economic contribution of one asset."""

    position: PositionProjection
    portfolio_weight: Decimal | None
    result_contribution_share: Decimal | None


@dataclass(frozen=True, slots=True, kw_only=True)
class AllocationProjection:
    """Point-in-time allocation plus result attribution summaries."""

    assets: tuple[AssetAllocation, ...]
    portfolio_market_value: Money
    valued_assets: int
    total_open_assets: int
    valuation_coverage: Decimal
    largest_position_weight: Decimal | None
    top_3_weight: Decimal | None
    top_5_weight: Decimal | None
    hhi: Decimal | None

    @property
    def top_contributors(self) -> tuple[AssetAllocation, ...]:
        return tuple(
            sorted(
                self.assets,
                key=lambda item: item.position.total_result.amount,
                reverse=True,
            )
        )

    @property
    def top_detractors(self) -> tuple[AssetAllocation, ...]:
        return tuple(sorted(self.assets, key=lambda item: item.position.total_result.amount))
