from __future__ import annotations

from decimal import Decimal

from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.read_models.allocation_analysis import (
    AllocationComparison,
    PortfolioAllocationAnalysis,
)
from income_analytics.domain.read_models.rebalancing_projection import RebalancingProjection
from income_analytics.domain.value_objects.money import Money


def test_full_and_contribution_only_rebalancing_are_analytical() -> None:
    analysis = PortfolioAllocationAnalysis(
        comparisons=(
            AllocationComparison(
                asset_class=AssetClass.BRAZILIAN_STOCK,
                current_weight=Decimal(".6"),
                target_weight=Decimal(".4"),
                deviation=Decimal(".2"),
                current_market_value=Money(Decimal("600")),
                target_market_value=Money(Decimal("400")),
                value_deviation=Money(Decimal("200")),
                status="ABOVE_TARGET",
            ),
            AllocationComparison(
                asset_class=AssetClass.FII,
                current_weight=Decimal(".4"),
                target_weight=Decimal(".6"),
                deviation=Decimal("-.2"),
                current_market_value=Money(Decimal("400")),
                target_market_value=Money(Decimal("600")),
                value_deviation=Money(Decimal("-200")),
                status="BELOW_TARGET",
            ),
        ),
        portfolio_drift=Decimal(".2"),
        portfolio_drift_value=Money(Decimal("200")),
    )
    plan = RebalancingProjection.from_analysis(analysis)
    assert plan.total_excess == Money(Decimal("200"))
    assert plan.total_deficit == Money(Decimal("200"))
    assert plan.contribution_only(Money(Decimal("50"))) == (("FII", Money(Decimal("50"))),)
