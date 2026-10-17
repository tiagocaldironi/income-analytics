from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.capital_flow_type import CapitalFlowType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.value_objects.money import Money


def register_buy(session: PortfolioSession, when: date) -> None:
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        quantity=Decimal("100"),
        unit_price=Decimal("100"),
        effective_date=when,
    )


def add_weekday_quotes(
    session: PortfolioSession, *, start: date, end: date,
    initial: Decimal, final_date: date, final: Decimal,
) -> None:
    current = start
    while current <= end:
        if current.weekday() < 5:
            price = final if current >= final_date else initial
            session.update_market_price(
                ticker="PETR4", current_price=price, effective_date=current
            )
        current += timedelta(days=1)


def test_twr_geometrically_neutralizes_a_contribution() -> None:
    session = PortfolioSession()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("10000"),
        effective_date=date(2026, 1, 1),
    )
    register_buy(session, date(2026, 1, 2))
    add_weekday_quotes(
        session, start=date(2026, 1, 2), end=date(2026, 1, 31),
        initial=Decimal("100"), final_date=date(2026, 1, 30), final=Decimal("110"),
    )
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("9000"),
        effective_date=date(2026, 2, 1),
    )
    add_weekday_quotes(
        session, start=date(2026, 2, 1), end=date(2026, 2, 28),
        initial=Decimal("110"), final_date=date(2026, 2, 27), final=Decimal("130"),
    )

    performance = session.performance(start_date=date(2026, 1, 1), end_date=date(2026, 2, 28))

    assert performance.twr == Decimal("0.21")
    assert performance.total_contributions == Money(Decimal("19000"))
    assert performance.ending_equity == Money(Decimal("22000"))


def test_withdrawal_reduces_cash_without_changing_total_result_or_twr_as_loss() -> None:
    session = PortfolioSession()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("20000"),
        effective_date=date(2026, 1, 1),
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        quantity=Decimal("200"),
        unit_price=Decimal("100"),
        effective_date=date(2026, 1, 2),
    )
    add_weekday_quotes(
        session, start=date(2026, 1, 2), end=date(2026, 1, 31),
        initial=Decimal("100"), final_date=date(2026, 1, 30), final=Decimal("110"),
    )
    session.register_external_flow(
        event_type=FinancialEventType.WITHDRAWAL,
        amount=Decimal("2000"),
        effective_date=date(2026, 2, 1),
    )
    after_withdrawal = session.projection()
    add_weekday_quotes(
        session, start=date(2026, 2, 1), end=date(2026, 2, 28),
        initial=Decimal("110"), final_date=date(2026, 2, 27), final=Decimal("115"),
    )

    portfolio = session.projection()
    performance = session.performance(start_date=date(2026, 1, 1), end_date=date(2026, 2, 28))

    assert portfolio.cash == Money(Decimal("-2000"))
    assert after_withdrawal.total_result == Money(Decimal("2000"))
    assert portfolio.total_withdrawals == Money(Decimal("2000"))
    assert performance.twr == Decimal("0.155")


def test_xirr_uses_real_dates_and_is_distinct_from_twr() -> None:
    session = PortfolioSession()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("10000"),
        effective_date=date(2026, 1, 1),
    )
    register_buy(session, date(2026, 1, 2))
    add_weekday_quotes(
        session, start=date(2026, 1, 2), end=date(2027, 1, 1),
        initial=Decimal("100"), final_date=date(2026, 12, 31), final=Decimal("110"),
    )

    performance = session.performance(start_date=date(2026, 1, 1), end_date=date(2027, 1, 1))

    assert performance.twr == Decimal("0.1")
    assert performance.xirr == pytest.approx(Decimal("0.1"), abs=Decimal("0.000001"))


def test_xirr_is_unavailable_without_positive_and_negative_cashflows() -> None:
    session = PortfolioSession()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("10000"),
        effective_date=date(2026, 1, 1),
    )

    performance = session.performance(start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))

    assert performance.xirr is None


def test_internal_transfer_is_not_counted_as_investor_return_or_xirr_flow() -> None:
    session = PortfolioSession()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("15000"),
        effective_date=date(2025, 12, 31),
    )
    register_buy(session, date(2026, 1, 1))
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("100"), effective_date=date(2026, 1, 1)
    )
    session.register_external_flow(
        event_type=FinancialEventType.WITHDRAWAL,
        amount=Decimal("5000"),
        effective_date=date(2026, 1, 2),
        capital_flow_type=CapitalFlowType.INTERNAL_TRANSFER,
    )
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("110"), effective_date=date(2026, 1, 3)
    )

    result = session.performance(start_date=date(2026, 1, 1), end_date=date(2026, 1, 3))

    assert result.twr == Decimal("0.1")
    assert result.total_withdrawals == Money.zero()


def test_weighted_coverage_keeps_performance_when_only_a_small_position_lacks_prices() -> None:
    session = PortfolioSession()
    for ticker, cost in (("AAA", "100000"), ("BBB", "49900"), ("CCC", "100")):
        session.register_trade(
            event_type=FinancialEventType.BUY,
            ticker=ticker,
            quantity=Decimal("1"),
            unit_price=Decimal(cost),
            effective_date=date(2025, 12, 1),
        )
    for ticker, price in (("AAA", "100000"), ("BBB", "49900")):
        start_price = Decimal(price)
        for offset in range(31):
            quote_date = date(2026, 1, 1) + timedelta(days=offset)
            if quote_date.weekday() >= 5:
                continue
            quote = start_price * (Decimal("1.1") if quote_date >= date(2026, 1, 30) else Decimal("1"))
            session.update_market_price(
                ticker=ticker, current_price=quote, effective_date=quote_date
            )

    result = session.performance(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))

    assert result.coverage_ratio == Decimal("149900") / Decimal("150000")
    assert result.performance_status == "AVAILABLE"
    assert result.twr == Decimal("0.1")
    assert result.missing_assets == ("CCC",)


def test_weighted_coverage_hides_performance_when_a_large_position_is_unpriced() -> None:
    session = PortfolioSession()
    for ticker, cost in (("AAA", "60000"), ("BBB", "40000")):
        session.register_trade(
            event_type=FinancialEventType.BUY,
            ticker=ticker,
            quantity=Decimal("1"),
            unit_price=Decimal(cost),
            effective_date=date(2025, 12, 1),
        )
    for offset in range(31):
        quote_date = date(2026, 1, 1) + timedelta(days=offset)
        if quote_date.weekday() >= 5:
            continue
        price = Decimal("66000") if quote_date >= date(2026, 1, 30) else Decimal("60000")
        session.update_market_price(ticker="AAA", current_price=price, effective_date=quote_date)

    result = session.performance(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))

    assert result.coverage_ratio == Decimal("0.6")
    assert result.performance_status == "INSUFFICIENT_DATA"
    assert result.twr is None
    assert result.missing_assets == ("BBB",)


def test_twr_rejects_quotes_older_than_seven_calendar_days() -> None:
    session = PortfolioSession()
    register_buy(session, date(2025, 12, 1))
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("100"), effective_date=date(2025, 12, 1)
    )
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("110"), effective_date=date(2026, 1, 10)
    )

    result = session.performance(start_date=date(2026, 1, 9), end_date=date(2026, 1, 10))

    assert result.performance_status == "INSUFFICIENT_DATA"
    assert result.twr is None
    assert result.missing_assets == ("PETR4",)
    assert result.missing_periods == (date(2026, 1, 9),)


def test_performance_can_be_calculated_for_one_asset_class() -> None:
    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY, ticker="AAA", asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("1"), unit_price=Decimal("10"), effective_date=date(2025, 12, 1),
    )
    session.register_trade(
        event_type=FinancialEventType.BUY, ticker="BTC", asset_class=AssetClass.CRYPTO,
        country="US", currency_code="USD", quantity=Decimal("1"), unit_price=Decimal("100"),
        effective_date=date(2025, 12, 1),
    )
    for ticker, price in (("AAA", "10"), ("BTC", "100")):
        session.update_market_price(ticker=ticker, current_price=Decimal(price), effective_date=date(2026, 1, 1))
    for ticker, price in (("AAA", "11"), ("BTC", "50")):
        session.update_market_price(ticker=ticker, current_price=Decimal(price), effective_date=date(2026, 1, 3))

    result = session.performance(
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 3),
        asset_class=AssetClass.BRAZILIAN_STOCK,
    )

    assert result.performance_status == "AVAILABLE"
    assert result.twr == Decimal("0.1")


@pytest.mark.parametrize(
    "income_type",
    [
        FinancialEventType.DIVIDEND,
        FinancialEventType.INTEREST_ON_EQUITY,
        FinancialEventType.FII_INCOME,
    ],
)
def test_distributed_income_is_economic_return_in_twr(income_type: FinancialEventType) -> None:
    session = PortfolioSession()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT, amount=Decimal("100"), effective_date=date(2026, 1, 1)
    )
    session.register_trade(
        event_type=FinancialEventType.BUY, ticker="PETR4", quantity=Decimal("1"),
        unit_price=Decimal("100"), effective_date=date(2026, 1, 2),
    )
    asset = session._assets["PETR4"]
    session.register_income(
        event_type=income_type, asset=asset, amount=Decimal("5"), effective_date=date(2026, 1, 15)
    )
    add_weekday_quotes(
        session, start=date(2026, 1, 2), end=date(2026, 1, 31),
        initial=Decimal("100"), final_date=date(2026, 1, 30), final=Decimal("105"),
    )

    result = session.performance(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))
    portfolio = session.projection()

    assert result.twr == Decimal("0.1")
    assert portfolio.income_received == Money(Decimal("5"))
    assert portfolio.total_market_value == Money(Decimal("105"))



def test_dividend_alone_counts_as_return_without_changing_asset_value() -> None:
    session = PortfolioSession()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT, amount=Decimal("100"), effective_date=date(2026, 1, 1)
    )
    session.register_trade(
        event_type=FinancialEventType.BUY, ticker="PETR4", quantity=Decimal("1"),
        unit_price=Decimal("100"), effective_date=date(2026, 1, 2),
    )
    session.register_income(
        event_type=FinancialEventType.DIVIDEND, asset=session._assets["PETR4"],
        amount=Decimal("5"), effective_date=date(2026, 1, 15),
    )
    add_weekday_quotes(
        session, start=date(2026, 1, 2), end=date(2026, 1, 31),
        initial=Decimal("100"), final_date=date(2026, 1, 30), final=Decimal("100"),
    )

    result = session.performance(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))
    portfolio = session.projection()

    assert result.twr == Decimal("0.05")
    assert portfolio.total_market_value == Money(Decimal("100"))
    assert portfolio.income_received == Money(Decimal("5"))

def test_reinvested_dividend_is_counted_once_in_twr() -> None:
    session = PortfolioSession()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT, amount=Decimal("100"), effective_date=date(2026, 1, 1)
    )
    session.register_trade(
        event_type=FinancialEventType.BUY, ticker="PETR4", quantity=Decimal("1"),
        unit_price=Decimal("100"), effective_date=date(2026, 1, 2),
    )
    asset = session._assets["PETR4"]
    session.register_income(
        event_type=FinancialEventType.DIVIDEND, asset=asset, amount=Decimal("5"), effective_date=date(2026, 1, 15)
    )
    session.register_trade(
        event_type=FinancialEventType.BUY, ticker="PETR4", quantity=Decimal("0.05"),
        unit_price=Decimal("100"), effective_date=date(2026, 1, 15),
    )
    add_weekday_quotes(
        session, start=date(2026, 1, 2), end=date(2026, 1, 31),
        initial=Decimal("100"), final_date=date(2026, 1, 30), final=Decimal("105"),
    )

    result = session.performance(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))
    portfolio = session.projection()

    assert result.twr == Decimal("0.1025")
    assert portfolio.income_received == Money(Decimal("5"))
    assert portfolio.total_market_value == Money(Decimal("110.25"))


def test_class_twr_is_unavailable_when_portfolio_flows_have_no_class_allocation() -> None:
    session = PortfolioSession()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT, amount=Decimal("100"), effective_date=date(2026, 1, 1)
    )
    session.register_trade(
        event_type=FinancialEventType.BUY, ticker="AAA", asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("1"), unit_price=Decimal("100"), effective_date=date(2026, 1, 1),
    )

    result = session.performance(
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 2),
        asset_class=AssetClass.BRAZILIAN_STOCK,
    )

    assert result.twr is None
    assert result.performance_status == "INSUFFICIENT_DATA"
    assert "sem classe associada" in result.unavailable_reason


def test_minha_carteira_and_entender_use_the_same_twr_for_the_same_period() -> None:
    from income_analytics.application.benchmark_comparison import build_performance_comparison

    session = PortfolioSession()
    register_buy(session, date(2026, 1, 1))
    add_weekday_quotes(
        session, start=date(2026, 1, 1), end=date(2026, 1, 31),
        initial=Decimal("100"), final_date=date(2026, 1, 30), final=Decimal("110"),
    )
    start, end = date(2026, 1, 1), date(2026, 1, 31)
    home_twr = session.performance(start_date=start, end_date=end).twr
    comparison = build_performance_comparison(
        start_date=start, end_date=end, rates=(), observations={},
        performance_at=lambda low, high: session.performance(start_date=low, end_date=high),
    )

    assert comparison["portfolio"]["return"] == home_twr
