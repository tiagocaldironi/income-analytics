from __future__ import annotations

from decimal import Decimal

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity


def trade(
    session: PortfolioSession,
    event_type: FinancialEventType,
    ticker: str,
    quantity: str,
    unit_price: str,
) -> None:
    session.register_trade(
        event_type=event_type,
        ticker=ticker,
        quantity=Decimal(quantity),
        unit_price=Decimal(unit_price),
    )


def test_portfolio_consolidates_the_total_economic_result() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, "PETR4", "100", "30")
    trade(session, FinancialEventType.BUY, "PETR4", "100", "40")
    trade(session, FinancialEventType.SELL, "PETR4", "50", "50")
    session.update_market_price(ticker="PETR4", current_price=Decimal("42"))
    portfolio = session.register_dividend(ticker="PETR4", amount=Decimal("120"))

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("150"))
    assert position.total_result == Money(Decimal("1920"))
    assert portfolio.total_cost == Money(Decimal("5250"))
    assert portfolio.total_market_value == Money(Decimal("6300"))
    assert portfolio.total_realized_result == Money(Decimal("750"))
    assert portfolio.total_unrealized_result == Money(Decimal("1050"))
    assert portfolio.income_received == Money(Decimal("120"))
    assert portfolio.total_result == Money(Decimal("1920"))
    assert portfolio.cash == Money(Decimal("-4380"))
    assert portfolio.total_result == (
        portfolio.total_realized_result
        + portfolio.total_unrealized_result
        + portfolio.income_received
    )


def test_total_result_can_be_negative() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, "PETR4", "100", "30")
    session.update_market_price(ticker="PETR4", current_price=Decimal("20"))
    portfolio = session.register_dividend(ticker="PETR4", amount=Decimal("100"))

    assert portfolio.total_unrealized_result == Money(Decimal("-1000"))
    assert portfolio.income_received == Money(Decimal("100"))
    assert portfolio.total_result == Money(Decimal("-900"))


def test_closed_position_keeps_historical_total_result_without_market_value() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, "PETR4", "100", "30")
    trade(session, FinancialEventType.SELL, "PETR4", "100", "40")
    portfolio = session.register_dividend(ticker="PETR4", amount=Decimal("100"))

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("0"))
    assert position.market_value == Money.zero()
    assert position.total_result == Money(Decimal("1100"))
    assert portfolio.total_cost == Money.zero()
    assert portfolio.total_market_value == Money.zero()
    assert portfolio.total_result == Money(Decimal("1100"))


def test_multiple_assets_sum_to_the_portfolio_total_result() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, "PETR4", "100", "30")
    trade(session, FinancialEventType.BUY, "BBAS3", "100", "20")
    session.update_market_price(ticker="PETR4", current_price=Decimal("40"))
    session.update_market_price(ticker="BBAS3", current_price=Decimal("25"))
    session.register_dividend(ticker="PETR4", amount=Decimal("100"))
    portfolio = session.register_dividend(ticker="BBAS3", amount=Decimal("50"))

    positions = {str(position.asset.ticker): position for position in portfolio.positions}
    assert positions["PETR4"].total_result == Money(Decimal("1100"))
    assert positions["BBAS3"].total_result == Money(Decimal("550"))
    assert portfolio.total_cost == Money(Decimal("5000"))
    assert portfolio.total_market_value == Money(Decimal("6500"))
    assert portfolio.total_result == Money(Decimal("1650"))
    assert portfolio.total_result == sum(
        (position.total_result for position in portfolio.positions),
        Money.zero(),
    )


def test_open_position_without_quote_has_no_fictitious_market_value() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, "PETR4", "100", "30")

    portfolio = session.projection()
    position = portfolio.positions[0]
    assert position.current_price is None
    assert position.unrealized_result == Money.zero()
    assert portfolio.has_complete_market_data is False
