"""Aggregate the existing asset allocation by manual asset class."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from income_analytics.domain.read_models.allocation_projection import AllocationProjection
from income_analytics.domain.read_models.class_allocation_projection import (
    AssetClassAllocation,
    ClassAllocationProjection,
)
from income_analytics.domain.value_objects.money import Money


class ClassAllocationProjector:
    @classmethod
    def project(cls, allocation: AllocationProjection) -> ClassAllocationProjection:
        grouped = defaultdict(list)
        for asset in allocation.assets:
            if not asset.position.is_empty or not asset.position.total_result.is_zero:
                grouped[asset.position.asset.asset_class].append(asset)
        classes: list[AssetClassAllocation] = []
        complete = allocation.valuation_coverage == Decimal("1")
        total_result = sum(
            (asset.position.total_result for asset in allocation.assets), Money.zero()
        )
        classified_open = [
            asset
            for asset in allocation.assets
            if not asset.position.is_empty and asset.position.asset.asset_class.value != "OTHER"
        ]
        classified_value = sum(
            (
                asset.position.market_value
                for asset in classified_open
                if asset.position.current_price
            ),
            Money.zero(),
        )
        for asset_class, assets in grouped.items():
            open_assets = [asset for asset in assets if not asset.position.is_empty]
            market_value = sum(
                (
                    asset.position.market_value
                    for asset in open_assets
                    if asset.position.current_price
                ),
                Money.zero(),
            )
            total = sum((asset.position.total_result for asset in assets), Money.zero())
            classes.append(
                AssetClassAllocation(
                    asset_class=asset_class,
                    market_value=market_value,
                    weight=market_value.amount / allocation.portfolio_market_value.amount
                    if complete and not allocation.portfolio_market_value.is_zero
                    else None,
                    asset_count=len(open_assets),
                    total_result=total,
                    realized_result=sum(
                        (asset.position.realized_result for asset in assets), Money.zero()
                    ),
                    unrealized_result=sum(
                        (asset.position.unrealized_result for asset in assets), Money.zero()
                    ),
                    income_received=sum(
                        (asset.position.income_received for asset in assets), Money.zero()
                    ),
                    result_contribution_share=total.amount / total_result.amount
                    if not total_result.is_zero
                    else None,
                )
            )
        classes.sort(key=lambda item: item.market_value.amount, reverse=True)
        weights = [item.weight for item in classes if item.weight is not None]
        open_total = allocation.total_open_assets
        return ClassAllocationProjection(
            classes=tuple(classes),
            classification_coverage=Decimal(len(classified_open)) / Decimal(open_total)
            if open_total
            else Decimal("1"),
            classification_coverage_by_value=classified_value.amount
            / allocation.portfolio_market_value.amount
            if not allocation.portfolio_market_value.is_zero
            else Decimal("1"),
            largest_class=classes[0].asset_class if weights else None,
            largest_class_weight=weights[0] if weights else None,
            class_hhi=sum((weight**2 for weight in weights), Decimal("0")) if weights else None,
        )
