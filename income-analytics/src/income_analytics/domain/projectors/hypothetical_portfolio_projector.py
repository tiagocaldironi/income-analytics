"""Create pure, class-level hypothetical contribution projections."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_DOWN, Decimal

from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.projectors.contribution_target_allocator import (
    ContributionTargetAllocator,
)
from income_analytics.domain.read_models.hypothetical_portfolio_projection import (
    HypotheticalPortfolioProjection,
    SimulationClassAllocation,
    SimulationClassChange,
    SimulationComparison,
    SimulationPortfolioState,
    SimulationScenario,
)


class HypotheticalPortfolioProjector:
    """Project a contribution using the existing *before-state deficit* algorithm.

    This deliberately does not optimise the after-state.  It preserves the historical
    contribution-only semantics while making the residual and resulting state explicit.
    """

    _CENT = Decimal("0.01")
    LEGACY_BEFORE_DEFICIT = "LEGACY_BEFORE_DEFICIT"
    STRATEGY_GUIDED = "STRATEGY_GUIDED"

    @classmethod
    def project_contribution(
        cls,
        *,
        as_of: date,
        base_currency: str,
        class_values: dict[AssetClass, Decimal],
        policy: AllocationPolicy,
        contribution: Decimal,
        valuation_complete: bool,
        valuation_issues: tuple[str, ...] = (),
        allocation_mode: str = LEGACY_BEFORE_DEFICIT,
    ) -> HypotheticalPortfolioProjection:
        if contribution <= 0:
            raise ValueError("O aporte simulado deve ser maior que zero.")
        all_classes = tuple(
            sorted(set(class_values) | set(policy.targets), key=lambda item: item.value)
        )
        issues = list(valuation_issues)
        wealth = sum(class_values.values(), Decimal("0"))
        if not valuation_complete:
            issues.append("INCOMPLETE_VALUATION")
            return cls._insufficient(
                as_of=as_of,
                base_currency=base_currency,
                class_values=class_values,
                policy=policy,
                contribution=contribution,
                all_classes=all_classes,
                issues=tuple(dict.fromkeys(issues)),
            )

        before = cls._state(as_of, base_currency, class_values, policy, all_classes, "COMPLETE", ())
        if allocation_mode not in {cls.LEGACY_BEFORE_DEFICIT, cls.STRATEGY_GUIDED}:
            raise ValueError("Modo de alocação simulada inválido.")
        target_wealth = (
            wealth if allocation_mode == cls.LEGACY_BEFORE_DEFICIT else wealth + contribution
        )
        deficits = {
            asset_class: max(
                policy.targets.get(asset_class, Decimal("0")) * target_wealth - value,
                Decimal("0"),
            )
            for asset_class, value in class_values.items()
            | {
                asset_class: Decimal("0")
                for asset_class in policy.targets
                if asset_class not in class_values
            }.items()
            if policy.targets.get(asset_class, Decimal("0")) > 0
            and policy.targets.get(asset_class, Decimal("0")) * target_wealth - value > 0
        }
        if allocation_mode == cls.STRATEGY_GUIDED:
            result = ContributionTargetAllocator.allocate(
                class_values,
                policy.targets,
                contribution,
                key=lambda item: item.value,
            )
            allocations = result.allocations
            unallocated = result.unallocated
        else:
            total_deficit = sum(deficits.values(), Decimal("0"))
            allocated = min(contribution, total_deficit).quantize(cls._CENT, rounding=ROUND_DOWN)
            allocations = cls._distribute(allocated, deficits)
            unallocated = contribution - allocated
        allocated = sum(allocations.values(), Decimal("0"))
        after_values = {
            asset_class: class_values.get(asset_class, Decimal("0"))
            + allocations.get(asset_class, Decimal("0"))
            for asset_class in all_classes
        }
        after = cls._state(as_of, base_currency, after_values, policy, all_classes, "COMPLETE", ())
        scenario = SimulationScenario(
            scenario_type="NEW_CONTRIBUTION",
            allocation_mode=allocation_mode,
            contribution_amount=contribution,
            base_currency=base_currency,
            class_allocations=tuple(sorted(allocations.items(), key=lambda item: item[0].value)),
            class_reason_codes=tuple(
                (
                    asset_class,
                    "BELOW_TARGET_AFTER_CONTRIBUTION"
                    if allocations.get(asset_class, Decimal("0")) > 0
                    else "ZERO_TARGET_NO_CONTRIBUTION"
                    if policy.targets.get(asset_class, Decimal("0")) == 0
                    else "ABOVE_TARGET_NO_CONTRIBUTION",
                )
                for asset_class in all_classes
            ),
            allocated_amount=allocated,
            unallocated_amount=unallocated,
        )
        comparison = cls._comparison(before, after, all_classes)
        return HypotheticalPortfolioProjection(
            before=before,
            scenario=scenario,
            after=after,
            comparison=comparison,
            status="COMPLETE",
            issues=("UNALLOCATED_CONTRIBUTION",) if unallocated else (),
        )

    @classmethod
    def _distribute(
        cls, amount: Decimal, deficits: dict[AssetClass, Decimal]
    ) -> dict[AssetClass, Decimal]:
        total = sum(deficits.values(), Decimal("0"))
        if not total or not amount:
            return {}
        ordered = sorted(deficits, key=lambda item: item.value)
        values = {
            item: (amount * deficits[item] / total).quantize(cls._CENT, rounding=ROUND_DOWN)
            for item in ordered
        }
        residual = amount - sum(values.values(), Decimal("0"))
        for item in ordered:
            if residual < cls._CENT:
                break
            values[item] += cls._CENT
            residual -= cls._CENT
        return values

    @classmethod
    def _state(
        cls,
        as_of: date,
        base: str,
        values: dict[AssetClass, Decimal],
        policy: AllocationPolicy,
        classes: tuple[AssetClass, ...],
        status: str,
        issues: tuple[str, ...],
    ) -> SimulationPortfolioState:
        wealth = sum(values.values(), Decimal("0"))
        allocations = tuple(
            SimulationClassAllocation(
                asset_class=item,
                current_value=values.get(item, Decimal("0")),
                weight=(values.get(item, Decimal("0")) / wealth if wealth else Decimal("0")),
                target_weight=policy.targets.get(item, Decimal("0")),
                gap_pp=(values.get(item, Decimal("0")) / wealth if wealth else Decimal("0"))
                - policy.targets.get(item, Decimal("0")),
            )
            for item in classes
        )
        distance = sum(
            (abs(item.gap_pp or Decimal("0")) for item in allocations), Decimal("0")
        ) / Decimal("2")
        return SimulationPortfolioState(
            as_of=as_of,
            base_currency=base,
            invested_wealth=wealth,
            class_allocations=allocations,
            strategy_distance=distance,
            valuation_status=status,
            issues=issues,
        )

    @classmethod
    def _insufficient(
        cls,
        *,
        as_of: date,
        base_currency: str,
        class_values: dict[AssetClass, Decimal],
        policy: AllocationPolicy,
        contribution: Decimal,
        all_classes: tuple[AssetClass, ...],
        issues: tuple[str, ...],
    ) -> HypotheticalPortfolioProjection:
        allocations = tuple(
            SimulationClassAllocation(
                asset_class=item,
                current_value=class_values.get(item, Decimal("0")),
                weight=None,
                target_weight=policy.targets.get(item, Decimal("0")),
                gap_pp=None,
            )
            for item in all_classes
        )
        state = SimulationPortfolioState(
            as_of=as_of,
            base_currency=base_currency,
            invested_wealth=None,
            class_allocations=allocations,
            strategy_distance=None,
            valuation_status="INSUFFICIENT",
            issues=issues,
        )
        scenario = SimulationScenario(
            scenario_type="NEW_CONTRIBUTION",
            allocation_mode=cls.LEGACY_BEFORE_DEFICIT,
            contribution_amount=contribution,
            base_currency=base_currency,
            class_allocations=(),
            class_reason_codes=(),
            allocated_amount=Decimal("0"),
            unallocated_amount=contribution,
        )
        comparison = SimulationComparison(
            wealth_before=None,
            invested_wealth_after=None,
            wealth_change=None,
            strategy_distance_before=None,
            strategy_distance_after=None,
            strategy_distance_change=None,
            class_changes=tuple(
                SimulationClassChange(
                    asset_class=item,
                    weight_before=None,
                    weight_after=None,
                    target_weight=policy.targets.get(item, Decimal("0")),
                    weight_change_pp=None,
                    gap_before_pp=None,
                    gap_after_pp=None,
                )
                for item in all_classes
            ),
        )
        return HypotheticalPortfolioProjection(
            before=state,
            scenario=scenario,
            after=state,
            comparison=comparison,
            status="INSUFFICIENT",
            issues=issues,
        )

    @classmethod
    def _comparison(
        cls,
        before: SimulationPortfolioState,
        after: SimulationPortfolioState,
        classes: tuple[AssetClass, ...],
    ) -> SimulationComparison:
        before_map = {item.asset_class: item for item in before.class_allocations}
        after_map = {item.asset_class: item for item in after.class_allocations}
        assert before.invested_wealth is not None
        assert after.invested_wealth is not None
        assert before.strategy_distance is not None
        assert after.strategy_distance is not None
        changes = tuple(
            SimulationClassChange(
                asset_class=item,
                weight_before=before_map[item].weight,
                weight_after=after_map[item].weight,
                target_weight=before_map[item].target_weight,
                weight_change_pp=(after_map[item].weight or Decimal("0"))
                - (before_map[item].weight or Decimal("0")),
                gap_before_pp=before_map[item].gap_pp,
                gap_after_pp=after_map[item].gap_pp,
            )
            for item in classes
        )
        return SimulationComparison(
            wealth_before=before.invested_wealth,
            invested_wealth_after=after.invested_wealth,
            wealth_change=after.invested_wealth - before.invested_wealth,
            strategy_distance_before=before.strategy_distance,
            strategy_distance_after=after.strategy_distance,
            strategy_distance_change=after.strategy_distance - before.strategy_distance,
            class_changes=changes,
        )
