"""Immutable, base-currency projection for a hypothetical portfolio scenario."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from income_analytics.domain.enums.asset_class import AssetClass


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationClassAllocation:
    asset_class: AssetClass
    current_value: Decimal
    weight: Decimal | None
    target_weight: Decimal
    gap_pp: Decimal | None


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationPortfolioState:
    as_of: date
    base_currency: str
    invested_wealth: Decimal | None
    class_allocations: tuple[SimulationClassAllocation, ...]
    strategy_distance: Decimal | None
    valuation_status: str
    issues: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationScenario:
    scenario_type: str
    allocation_mode: str
    contribution_amount: Decimal
    base_currency: str
    class_allocations: tuple[tuple[AssetClass, Decimal], ...]
    class_reason_codes: tuple[tuple[AssetClass, str], ...]
    allocated_amount: Decimal
    unallocated_amount: Decimal
    class_details: tuple[SimulationClassContribution, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationAssetContribution:
    asset_id: str
    asset_label: str
    amount: Decimal
    value_before: Decimal
    value_after: Decimal
    weight_before_in_class: Decimal | None
    weight_after_in_class: Decimal | None
    target_weight_in_class: Decimal
    gap_before_pp: Decimal | None
    gap_after_pp: Decimal | None
    reason_code: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationClassContribution:
    asset_class: AssetClass
    amount: Decimal
    asset_distribution_status: str
    asset_distributed_amount: Decimal
    undistributed_within_class: Decimal
    asset_composition_distance_before: Decimal | None
    asset_composition_distance_after: Decimal | None
    asset_composition_distance_change: Decimal | None
    asset_allocations: tuple[SimulationAssetContribution, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationClassChange:
    asset_class: AssetClass
    weight_before: Decimal | None
    weight_after: Decimal | None
    target_weight: Decimal
    weight_change_pp: Decimal | None
    gap_before_pp: Decimal | None
    gap_after_pp: Decimal | None


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationComparison:
    wealth_before: Decimal | None
    invested_wealth_after: Decimal | None
    wealth_change: Decimal | None
    strategy_distance_before: Decimal | None
    strategy_distance_after: Decimal | None
    strategy_distance_change: Decimal | None
    class_changes: tuple[SimulationClassChange, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class HypotheticalPortfolioProjection:
    before: SimulationPortfolioState
    scenario: SimulationScenario
    after: SimulationPortfolioState
    comparison: SimulationComparison
    status: str
    issues: tuple[str, ...]
