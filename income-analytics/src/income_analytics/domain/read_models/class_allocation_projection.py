"""Class-level aggregation of the point-in-time portfolio allocation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetClassAllocation:
    asset_class: AssetClass
    market_value: Money
    weight: Decimal | None
    asset_count: int
    total_result: Money
    realized_result: Money
    unrealized_result: Money
    income_received: Money
    result_contribution_share: Decimal | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ClassAllocationProjection:
    classes: tuple[AssetClassAllocation, ...]
    classification_coverage: Decimal
    classification_coverage_by_value: Decimal
    largest_class: AssetClass | None
    largest_class_weight: Decimal | None
    class_hhi: Decimal | None
