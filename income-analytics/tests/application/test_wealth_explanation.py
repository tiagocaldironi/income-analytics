from datetime import date
from decimal import Decimal

from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.application.wealth_explanation import WealthExplanationService
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType


def _service(session: PortfolioSession) -> WealthExplanationService:
    return WealthExplanationService(
        events=session.history(),
        portfolio_at=lambda as_of: session.projection(as_of=as_of),
        valuation_at=lambda as_of: session.base_currency_valuation(as_of=as_of),
        performance_at=lambda start, end: session.performance(start_date=start, end_date=end),
    )


def _seed_position(*, asset_class=AssetClass.BRAZILIAN_STOCK):
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        asset_class=asset_class,
        quantity=Decimal("10"),
        unit_price=Decimal("10"),
        effective_date=date(2026, 1, 1),
    )
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("10"), effective_date=date(2026, 1, 1)
    )
    return session


def _payload(session, end=date(2026, 1, 2)):
    return _service(session).explain(start_date=date(2026, 1, 1), end_date=end).payload


def test_asset_balance_does_not_include_reconstructed_cash_or_external_deposits():
    session = _seed_position()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("500"),
        effective_date=date(2026, 1, 2),
    )
    payload = _payload(session)
    assert payload["asset_balance"] == {
        "start": Decimal("100"),
        "end": Decimal("100"),
        "change": Decimal("0"),
        "change_percentage": Decimal("0"),
    }
    assert payload["data_quality"]["implicit_cash_used_in_asset_balance"] is False


def test_price_appreciation_is_asset_bridge_effect():
    session = _seed_position()
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("11"), effective_date=date(2026, 1, 2)
    )
    payload = _payload(session)
    assert payload["bridge"]["market_appreciation"] == Decimal("10")
    assert payload["bridge"]["unexplained"] == Decimal("0")


def test_buy_is_net_acquisition_and_does_not_need_funding_source():
    session = _seed_position()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("2"),
        unit_price=Decimal("10"),
        effective_date=date(2026, 1, 2),
    )
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("10"), effective_date=date(2026, 1, 2)
    )
    payload = _payload(session)
    assert payload["bridge"]["net_acquisitions"] == Decimal("20")
    assert payload["asset_balance"]["change"] == Decimal("20")
    assert payload["bridge"]["unexplained"] == Decimal("0")


def test_dividend_not_reinvested_is_income_only():
    session = _seed_position()
    session.register_income(
        event_type=FinancialEventType.DIVIDEND,
        asset=session._assets["PETR4"],
        amount=Decimal("5"),
        effective_date=date(2026, 1, 2),
    )
    payload = _payload(session)
    assert payload["asset_balance"]["change"] == Decimal("0")
    assert payload["income_generated"]["total"] == Decimal("5")
    assert payload["bridge"]["unexplained"] == Decimal("0")
    assert all(component["component_type"] != "PAID_INCOME" for component in payload["components"])


def test_reinvested_dividend_is_shown_as_income_and_separate_acquisition():
    session = _seed_position()
    session.register_income(
        event_type=FinancialEventType.DIVIDEND,
        asset=session._assets["PETR4"],
        amount=Decimal("5"),
        effective_date=date(2026, 1, 2),
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("0.5"),
        unit_price=Decimal("10"),
        effective_date=date(2026, 1, 2),
    )
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("10"), effective_date=date(2026, 1, 2)
    )
    payload = _payload(session)
    assert payload["bridge"]["net_acquisitions"] == Decimal("5")
    assert payload["income_generated"]["total"] == Decimal("5")
    assert payload["asset_balance"]["change"] == Decimal("5")


def test_sell_reduces_asset_stock_as_negative_net_acquisition():
    session = _seed_position()
    session.register_trade(
        event_type=FinancialEventType.SELL,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("10"),
        unit_price=Decimal("10"),
        effective_date=date(2026, 1, 2),
    )
    payload = _payload(session)
    assert payload["bridge"]["net_acquisitions"] == Decimal("-100")
    assert payload["asset_balance"]["end"] == Decimal("0")
    assert payload["bridge"]["unexplained"] == Decimal("0")


def test_unpriced_buy_is_explicit_adjustment_with_partial_coverage():
    session = _seed_position()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="AUPO11",
        asset_class=AssetClass.BRAZILIAN_ETF,
        quantity=Decimal("1"),
        unit_price=Decimal("10"),
        effective_date=date(2026, 1, 2),
    )
    payload = _payload(session)
    assert payload["bridge"]["net_acquisitions"] == Decimal("10")
    assert payload["bridge"]["valuation_adjustments"] == Decimal("-10")
    assert payload["data_quality"]["valuation_coverage_percentage"] < Decimal("100")
    assert payload["bridge"]["unexplained"] == Decimal("0")


def test_income_breakdown_reconciles_independently():
    session = _seed_position()
    asset = session._assets["PETR4"]
    for event_type, amount in (
        (FinancialEventType.DIVIDEND, "3"),
        (FinancialEventType.INTEREST_ON_EQUITY, "2"),
    ):
        session.register_income(
            event_type=event_type,
            asset=asset,
            amount=Decimal(amount),
            effective_date=date(2026, 1, 2),
        )
    payload = _payload(session)
    income = payload["income_generated"]
    assert (
        income["dividends"]
        + income["jcp"]
        + income["fii_income"]
        + income["other_distributed_income"]
        == income["total"]
        == Decimal("5")
    )


def test_twr_remains_a_separate_existing_performance_result():
    session = _seed_position()
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("11"), effective_date=date(2026, 1, 2)
    )
    payload = _payload(session)
    assert (
        payload["performance"]["twr"]
        == session.performance(start_date=date(2026, 1, 1), end_date=date(2026, 1, 2)).twr
    )
    assert payload["data_quality"]["twr_algorithm_changed"] is False


def test_fixed_income_embedded_growth_is_asset_valuation_not_distributed_income():
    session = _seed_position(asset_class=AssetClass.FIXED_INCOME)
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("10.5"), effective_date=date(2026, 1, 2)
    )
    payload = _payload(session)
    assert payload["bridge"]["fixed_income_return"] == Decimal("5.0")
    assert payload["income_generated"]["total"] == Decimal("0")
    assert payload["bridge"]["unexplained"] == Decimal("0")
