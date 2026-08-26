"""Distribute a class-level simulated amount among existing assets only."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.read_models.allocation_projection import AllocationProjection
from income_analytics.domain.value_objects.money import Money


class AssetAllocationStrategy(StrEnum):
    PROPORTIONAL_TO_CURRENT_WEIGHT = "PROPORTIONAL_TO_CURRENT_WEIGHT"
    EQUAL_WEIGHT_WITHIN_CLASS = "EQUAL_WEIGHT_WITHIN_CLASS"


class AssetRebalancingProjector:
    @classmethod
    def distribute(
        cls,
        allocation: AllocationProjection,
        asset_class: AssetClass,
        amount: Money,
        strategy: AssetAllocationStrategy,
    ) -> tuple[tuple[str, Money], ...]:
        assets = [
            item
            for item in allocation.assets
            if not item.position.is_empty
            and item.position.asset.asset_class is asset_class
            and item.position.current_price
        ]
        if not assets or amount.is_zero:
            return ()
        if strategy is AssetAllocationStrategy.EQUAL_WEIGHT_WITHIN_CLASS:
            weights = [Decimal("1") / Decimal(len(assets))] * len(assets)
        else:
            total = sum((item.position.market_value.amount for item in assets), Decimal("0"))
            weights = [item.position.market_value.amount / total for item in assets]
        return tuple(
            (str(item.position.asset.ticker), Money(amount.amount * weight))
            for item, weight in zip(assets, weights, strict=True)
        )
