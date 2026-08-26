from __future__ import annotations

from decimal import Decimal

import pytest

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


def test_dividend_adds_income_and_cash_without_changing_position_or_valuation() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, "PETR4", "100", "30")
    trade(session, FinancialEventType.BUY, "PETR4", "100", "40")
    trade(session, FinancialEventType.SELL, "PETR4", "50", "50")
    session.update_market_price(ticker="PETR4", current_price=Decimal("42"))

    portfolio = session.register_dividend(ticker="PETR4", amount=Decimal("120"))

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("150"))
    assert position.cost == Money(Decimal("5250"))
    assert position.average_price == Money(Decimal("35"))
    assert position.market_value == Money(Decimal("6300"))
    assert position.unrealized_result == Money(Decimal("1050"))
    assert position.realized_result == Money(Decimal("750"))
    assert position.income_received == Money(Decimal("120"))
    assert portfolio.income_received == Money(Decimal("120"))
    assert portfolio.cash == Money(Decimal("-4380"))


def test_dividends_accumulate_for_an_asset_and_cash() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, "PETR4", "100", "30")

    for amount in ("120", "80", "50"):
        portfolio = session.register_dividend(ticker="PETR4", amount=Decimal(amount))

    assert portfolio.positions[0].income_received == Money(Decimal("250"))
    assert portfolio.income_received == Money(Decimal("250"))
    assert portfolio.cash == Money(Decimal("-2750"))


def test_dividend_is_allowed_after_the_position_has_been_fully_sold() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, "PETR4", "100", "30")
    trade(session, FinancialEventType.SELL, "PETR4", "100", "40")

    portfolio = session.register_dividend(ticker="PETR4", amount=Decimal("100"))

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("0"))
    assert position.income_received == Money(Decimal("100"))
    assert position.realized_result == Money(Decimal("1000"))
    assert portfolio.cash == Money(Decimal("1100"))


def test_dividends_are_attributed_to_their_respective_assets() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, "PETR4", "100", "30")
    trade(session, FinancialEventType.BUY, "BBAS3", "100", "20")
    session.register_dividend(ticker="PETR4", amount=Decimal("100"))
    portfolio = session.register_dividend(ticker="BBAS3", amount=Decimal("50"))

    positions = {str(position.asset.ticker): position for position in portfolio.positions}
    assert positions["PETR4"].income_received == Money(Decimal("100"))
    assert positions["BBAS3"].income_received == Money(Decimal("50"))
    assert portfolio.income_received == Money(Decimal("150"))


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-50")])
def test_rejects_non_positive_dividend_amount(amount: Decimal) -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, "PETR4", "100", "30")

    with pytest.raises(ValueError, match="provento"):
        session.register_dividend(ticker="PETR4", amount=amount)
