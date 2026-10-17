"""Detailed, non-executing asset-level rebalance simulation."""

from __future__ import annotations

from dataclasses import dataclass

from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetRebalancingAllocation:
    ticker: str
    allocated_amount: Money
    current_weight_within_class: object | None
    simulated_weight_within_class: object | None


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetRebalancingPlan:
    asset_class: AssetClass
    class_amount: Money
    strategy: str
    allocations: tuple[AssetRebalancingAllocation, ...]
    unallocated_amount: Money
