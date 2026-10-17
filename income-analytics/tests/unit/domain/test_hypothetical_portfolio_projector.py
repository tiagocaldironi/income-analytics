from datetime import date
from decimal import Decimal

from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.projectors.hypothetical_portfolio_projector import (
    HypotheticalPortfolioProjector,
)


def _policy() -> AllocationPolicy:
    return AllocationPolicy(
        targets={AssetClass.BRAZILIAN_STOCK: Decimal(".4"), AssetClass.FII: Decimal(".6")}
    )


def test_contribution_projects_before_after_and_explicit_residual() -> None:
    projection = HypotheticalPortfolioProjector.project_contribution(
        as_of=date(2026, 9, 24),
        base_currency="BRL",
        class_values={AssetClass.BRAZILIAN_STOCK: Decimal("600"), AssetClass.FII: Decimal("400")},
        policy=_policy(),
        contribution=Decimal("500"),
        valuation_complete=True,
    )

    assert projection.status == "COMPLETE"
    assert projection.scenario.allocated_amount == Decimal("200.00")
    assert projection.scenario.unallocated_amount == Decimal("300.00")
    assert projection.scenario.allocated_amount + projection.scenario.unallocated_amount == Decimal(
        "500.00"
    )
    assert projection.before.invested_wealth == Decimal("1000")
    assert projection.after.invested_wealth == Decimal("1200.00")
    assert projection.comparison.strategy_distance_before == Decimal(".2")
    assert projection.comparison.strategy_distance_after == Decimal(".1")


def test_target_zero_stays_in_portfolio_and_receives_no_contribution() -> None:
    policy = AllocationPolicy(targets={AssetClass.FII: Decimal("1")})
    projection = HypotheticalPortfolioProjector.project_contribution(
        as_of=date(2026, 9, 24),
        base_currency="BRL",
        class_values={AssetClass.BRAZILIAN_STOCK: Decimal("500"), AssetClass.FII: Decimal("500")},
        policy=policy,
        contribution=Decimal("100"),
        valuation_complete=True,
    )
    allocations = dict(projection.scenario.class_allocations)
    assert AssetClass.BRAZILIAN_STOCK not in allocations
    assert allocations[AssetClass.FII] == Decimal("100.00")
    assert any(
        item.asset_class is AssetClass.BRAZILIAN_STOCK
        for item in projection.after.class_allocations
    )


def test_missing_valuation_never_normalizes_partial_portfolio() -> None:
    projection = HypotheticalPortfolioProjector.project_contribution(
        as_of=date(2026, 9, 24),
        base_currency="BRL",
        class_values={AssetClass.BRAZILIAN_STOCK: Decimal("100")},
        policy=_policy(),
        contribution=Decimal("10"),
        valuation_complete=False,
        valuation_issues=("MISSING_FX",),
    )
    assert projection.status == "INSUFFICIENT"
    assert projection.before.strategy_distance is None
    assert projection.before.class_allocations[0].weight is None
    assert projection.scenario.allocated_amount == Decimal("0")
    assert projection.scenario.unallocated_amount == Decimal("10")


def test_small_contributions_are_cent_reconciled_and_deterministic() -> None:
    kwargs = dict(
        as_of=date(2026, 9, 24),
        base_currency="BRL",
        class_values={AssetClass.BRAZILIAN_STOCK: Decimal("60"), AssetClass.FII: Decimal("40")},
        policy=_policy(),
        contribution=Decimal(".01"),
        valuation_complete=True,
    )
    first = HypotheticalPortfolioProjector.project_contribution(**kwargs)
    second = HypotheticalPortfolioProjector.project_contribution(**kwargs)
    assert first == second
    assert first.scenario.allocated_amount + first.scenario.unallocated_amount == Decimal(".01")


def test_strategy_guided_uses_after_wealth_and_reaches_simple_target() -> None:
    policy = AllocationPolicy(
        targets={AssetClass.BRAZILIAN_STOCK: Decimal(".5"), AssetClass.FII: Decimal(".5")}
    )
    projection = HypotheticalPortfolioProjector.project_contribution(
        as_of=date(2026, 9, 24),
        base_currency="BRL",
        class_values={AssetClass.BRAZILIAN_STOCK: Decimal("70"), AssetClass.FII: Decimal("30")},
        policy=policy,
        contribution=Decimal("40"),
        valuation_complete=True,
        allocation_mode="STRATEGY_GUIDED",
    )
    assert dict(projection.scenario.class_allocations) == {AssetClass.FII: Decimal("40.00")}
    assert projection.after.strategy_distance == Decimal("0")
    assert projection.scenario.allocation_mode == "STRATEGY_GUIDED"


def test_strategy_guided_preserves_an_aligned_portfolio() -> None:
    policy = AllocationPolicy(
        targets={AssetClass.BRAZILIAN_STOCK: Decimal(".5"), AssetClass.FII: Decimal(".5")}
    )
    projection = HypotheticalPortfolioProjector.project_contribution(
        as_of=date(2026, 9, 24),
        base_currency="BRL",
        class_values={AssetClass.BRAZILIAN_STOCK: Decimal("50"), AssetClass.FII: Decimal("50")},
        policy=policy,
        contribution=Decimal("20"),
        valuation_complete=True,
        allocation_mode="STRATEGY_GUIDED",
    )
    assert dict(projection.scenario.class_allocations) == {
        AssetClass.BRAZILIAN_STOCK: Decimal("10.00"),
        AssetClass.FII: Decimal("10.00"),
    }
    assert projection.before.strategy_distance == projection.after.strategy_distance == Decimal("0")


def test_strategy_guided_is_never_worse_than_legacy_for_large_contribution() -> None:
    kwargs = dict(
        as_of=date(2026, 9, 24),
        base_currency="BRL",
        class_values={AssetClass.BRAZILIAN_STOCK: Decimal("80"), AssetClass.FII: Decimal("20")},
        policy=_policy(),
        contribution=Decimal("100"),
        valuation_complete=True,
    )
    legacy = HypotheticalPortfolioProjector.project_contribution(**kwargs)
    guided = HypotheticalPortfolioProjector.project_contribution(
        **kwargs, allocation_mode="STRATEGY_GUIDED"
    )
    assert guided.scenario.allocated_amount == Decimal("100.00")
    assert guided.scenario.unallocated_amount == Decimal("0.00")
    assert guided.after.strategy_distance <= legacy.after.strategy_distance


def test_strategy_guided_three_class_after_target_proof() -> None:
    policy = AllocationPolicy(
        targets={
            AssetClass.BRAZILIAN_STOCK: Decimal(".4"),
            AssetClass.FII: Decimal(".35"),
            AssetClass.FIXED_INCOME: Decimal(".25"),
        }
    )
    projection = HypotheticalPortfolioProjector.project_contribution(
        as_of=date(2026, 9, 24),
        base_currency="BRL",
        class_values={
            AssetClass.BRAZILIAN_STOCK: Decimal("60"),
            AssetClass.FII: Decimal("30"),
            AssetClass.FIXED_INCOME: Decimal("10"),
        },
        policy=policy,
        contribution=Decimal("50"),
        valuation_complete=True,
        allocation_mode="STRATEGY_GUIDED",
    )
    assert dict(projection.scenario.class_allocations) == {
        AssetClass.FII: Decimal("22.50"),
        AssetClass.FIXED_INCOME: Decimal("27.50"),
    }
    assert projection.after.strategy_distance == Decimal("0")


def test_strategy_guided_can_fund_a_new_target_class() -> None:
    policy = AllocationPolicy(
        targets={AssetClass.BRAZILIAN_STOCK: Decimal(".8"), AssetClass.FII: Decimal(".2")}
    )
    projection = HypotheticalPortfolioProjector.project_contribution(
        as_of=date(2026, 9, 24),
        base_currency="BRL",
        class_values={AssetClass.BRAZILIAN_STOCK: Decimal("100")},
        policy=policy,
        contribution=Decimal("25"),
        valuation_complete=True,
        allocation_mode="STRATEGY_GUIDED",
    )
    assert dict(projection.scenario.class_allocations) == {AssetClass.FII: Decimal("25.00")}
    assert projection.after.strategy_distance == Decimal("0")
