from __future__ import annotations

from income_analytics.domain.projectors.asset_rebalancing_projector import (
    AssetAllocationStrategy,
)


def test_asset_rebalancing_strategies_are_explicit() -> None:
    assert (
        AssetAllocationStrategy.PROPORTIONAL_TO_CURRENT_WEIGHT.value
        == "PROPORTIONAL_TO_CURRENT_WEIGHT"
    )
    assert AssetAllocationStrategy.EQUAL_WEIGHT_WITHIN_CLASS.value == "EQUAL_WEIGHT_WITHIN_CLASS"
