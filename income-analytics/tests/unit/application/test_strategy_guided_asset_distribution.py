from datetime import date
from decimal import Decimal

from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.asset_allocation_policy import AssetAllocationPolicy
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType

TODAY = date(2026, 9, 24)


def _session() -> PortfolioSession:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="STOCK",
        name="Ação",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("1"),
        unit_price=Decimal("70"),
        effective_date=TODAY,
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="FUND-A",
        name="Fundo A",
        asset_class=AssetClass.FII,
        quantity=Decimal("1"),
        unit_price=Decimal("20"),
        effective_date=TODAY,
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="FUND-B",
        name="Fundo B",
        asset_class=AssetClass.FII,
        quantity=Decimal("1"),
        unit_price=Decimal("10"),
        effective_date=TODAY,
    )
    for ticker, price in (("STOCK", "70"), ("FUND-A", "20"), ("FUND-B", "10")):
        session.update_market_price(
            ticker=ticker, current_price=Decimal(price), effective_date=TODAY
        )
    session.set_allocation_policy(
        AllocationPolicy(
            targets={AssetClass.BRAZILIAN_STOCK: Decimal(".5"), AssetClass.FII: Decimal(".5")}
        )
    )
    return session


def test_missing_asset_policy_keeps_class_destination_and_reconciles() -> None:
    projection = _session().hypothetical_contribution(
        amount=Decimal("40"), as_of=TODAY, allocation_mode="STRATEGY_GUIDED"
    )
    detail = projection.scenario.class_details[0]
    assert detail.asset_distribution_status == "NEEDS_USER_DISTRIBUTION"
    assert detail.asset_distributed_amount == 0
    assert detail.undistributed_within_class == detail.amount == Decimal("40.00")
    assert projection.scenario.allocated_amount + projection.scenario.unallocated_amount == Decimal(
        "40"
    )


def test_valid_asset_policy_uses_after_composition_and_reconciles() -> None:
    session = _session()
    session.set_asset_allocation_policy(
        AssetAllocationPolicy(
            targets={AssetClass.FII: {"FUND-A": Decimal(".5"), "FUND-B": Decimal(".5")}}
        )
    )
    projection = session.hypothetical_contribution(
        amount=Decimal("40"), as_of=TODAY, allocation_mode="STRATEGY_GUIDED"
    )
    detail = projection.scenario.class_details[0]
    by_label = {item.asset_label: item for item in detail.asset_allocations}
    assert detail.asset_distribution_status == "DISTRIBUTED_BY_STRATEGY"
    assert by_label["Fundo A"].amount == Decimal("15.00")
    assert by_label["Fundo B"].amount == Decimal("25.00")
    assert detail.asset_composition_distance_after == 0
    assert detail.asset_distributed_amount + detail.undistributed_within_class == detail.amount


def test_strategy_simulation_hides_zero_target_assets_without_positions() -> None:
    session = _session()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="FUND-ZERO",
        name="Fundo sem objetivo",
        asset_class=AssetClass.FII,
        quantity=Decimal("1"),
        unit_price=Decimal("10"),
        effective_date=TODAY,
    )
    session.update_market_price(
        ticker="FUND-ZERO", current_price=Decimal("10"), effective_date=TODAY
    )
    session.register_trade(
        event_type=FinancialEventType.SELL,
        ticker="FUND-ZERO",
        name="Fundo sem objetivo",
        asset_class=AssetClass.FII,
        quantity=Decimal("1"),
        unit_price=Decimal("10"),
        effective_date=TODAY,
    )
    session.set_asset_allocation_policy(
        AssetAllocationPolicy(
            targets={
                AssetClass.FII: {
                    "FUND-A": Decimal(".5"),
                    "FUND-B": Decimal(".5"),
                    "FUND-ZERO": Decimal("0"),
                }
            }
        )
    )

    projection = session.hypothetical_contribution(
        amount=Decimal("40"), as_of=TODAY, allocation_mode="STRATEGY_GUIDED"
    )

    detail = next(
        item for item in projection.scenario.class_details if item.asset_class is AssetClass.FII
    )
    assert {item.asset_label for item in detail.asset_allocations} == {"Fundo A", "Fundo B"}


def test_invalid_mutated_asset_policy_is_not_normalized() -> None:
    session = _session()
    policy = AssetAllocationPolicy(
        targets={AssetClass.FII: {"FUND-A": Decimal(".5"), "FUND-B": Decimal(".5")}}
    )
    session.set_asset_allocation_policy(policy)
    policy.targets[AssetClass.FII].pop("FUND-B")
    projection = session.hypothetical_contribution(
        amount=Decimal("40"), as_of=TODAY, allocation_mode="STRATEGY_GUIDED"
    )
    detail = projection.scenario.class_details[0]
    assert detail.asset_distribution_status == "INCOMPLETE_OR_INVALID_POLICY"
    assert detail.asset_distributed_amount == 0
    assert detail.undistributed_within_class == detail.amount


def test_updating_one_class_preserves_unrelated_policy_even_if_it_is_stale() -> None:
    session = _session()
    fixed_income_policy = AssetAllocationPolicy(
        targets={AssetClass.FII: {"FUND-A": Decimal(".5"), "FUND-B": Decimal(".5")}}
    )
    session.set_asset_allocation_policy(fixed_income_policy)
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="FUND-C",
        name="Fundo C",
        asset_class=AssetClass.FII,
        quantity=Decimal("1"),
        unit_price=Decimal("5"),
        effective_date=TODAY,
    )

    session.set_asset_allocation_policy(
        AssetAllocationPolicy(targets={AssetClass.BRAZILIAN_STOCK: {"STOCK": Decimal("1")}})
    )

    policy = session.asset_allocation_policy
    assert policy is not None
    assert policy.targets[AssetClass.FII] == {
        "FUND-A": Decimal(".5"),
        "FUND-B": Decimal(".5"),
    }
    assert policy.targets[AssetClass.BRAZILIAN_STOCK] == {"STOCK": Decimal("1")}
