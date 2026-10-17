"""Allocation and concentration calculations based on PortfolioProjection."""

from __future__ import annotations

from decimal import Decimal

from income_analytics.domain.read_models.allocation_projection import (
    AllocationProjection,
    AssetAllocation,
)
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection
from income_analytics.domain.value_objects.money import Money


class AllocationProjector:
    """Explain current asset exposure while retaining closed-asset results."""

    @classmethod
    def project(cls, portfolio: PortfolioProjection) -> AllocationProjection:
        open_positions = tuple(
            position for position in portfolio.positions if not position.is_empty
        )
        valued = tuple(
            position for position in open_positions if position.current_price is not None
        )
        coverage = (
            Decimal("1")
            if not open_positions
            else Decimal(len(valued)) / Decimal(len(open_positions))
        )
        complete = len(valued) == len(open_positions) and bool(open_positions)
        market_value = sum((position.market_value for position in valued), Money.zero())
        total_result = portfolio.total_result
        assets = tuple(
            AssetAllocation(
                position=position,
                portfolio_weight=(
                    position.market_value.amount / market_value.amount
                    if complete and not position.is_empty and not market_value.is_zero
                    else None
                ),
                result_contribution_share=(
                    position.total_result.amount / total_result.amount
                    if not total_result.is_zero
                    else None
                ),
            )
            for position in portfolio.positions
        )
        weights = sorted(
            (asset.portfolio_weight for asset in assets if asset.portfolio_weight is not None),
            reverse=True,
        )
        return AllocationProjection(
            assets=assets,
            portfolio_market_value=market_value,
            valued_assets=len(valued),
            total_open_assets=len(open_positions),
            valuation_coverage=coverage,
            largest_position_weight=weights[0] if weights else None,
            top_3_weight=sum(weights[:3], Decimal("0")) if weights else None,
            top_5_weight=sum(weights[:5], Decimal("0")) if weights else None,
            hhi=sum((weight**2 for weight in weights), Decimal("0")) if weights else None,
        )
