"""Target-policy drift analysis; it never creates trading instructions."""

from __future__ import annotations

from decimal import Decimal

from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.projectors.class_allocation_projector import ClassAllocationProjector
from income_analytics.domain.read_models.allocation_analysis import (
    AllocationComparison,
    PortfolioAllocationAnalysis,
)
from income_analytics.domain.read_models.allocation_projection import AllocationProjection
from income_analytics.domain.value_objects.money import Money


class AllocationAnalysisProjector:
    @classmethod
    def project(
        cls, allocation: AllocationProjection, policy: AllocationPolicy
    ) -> PortfolioAllocationAnalysis:
        classes = ClassAllocationProjector.project(allocation)
        current = {item.asset_class: item for item in classes.classes}
        comparisons = []
        for asset_class in current.keys() | policy.targets.keys():
            item = current.get(asset_class)
            current_weight = item.weight if item and item.weight is not None else Decimal("0")
            target_weight = policy.targets.get(asset_class, Decimal("0"))
            deviation = current_weight - target_weight
            status = (
                "ON_TARGET"
                if abs(deviation) <= Decimal("0.000001")
                else "ABOVE_TARGET"
                if deviation > 0
                else "BELOW_TARGET"
            )
            current_value = item.market_value if item else Money.zero()
            target_value = Money(allocation.portfolio_market_value.amount * target_weight)
            comparisons.append(
                AllocationComparison(
                    asset_class=asset_class,
                    current_weight=current_weight,
                    target_weight=target_weight,
                    deviation=deviation,
                    current_market_value=current_value,
                    target_market_value=target_value,
                    value_deviation=current_value - target_value,
                    status=status,
                )
            )
        drift = sum((abs(item.deviation) for item in comparisons), Decimal("0")) / Decimal("2")
        return PortfolioAllocationAnalysis(
            comparisons=tuple(comparisons),
            portfolio_drift=drift,
            portfolio_drift_value=Money(allocation.portfolio_market_value.amount * drift),
        )
