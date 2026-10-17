from __future__ import annotations

from decimal import Decimal

import pytest

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity


def register_trade(
    session: PortfolioSession,
    event_type: FinancialEventType,
    quantity: str,
    unit_price: str,
) -> None:
    session.register_trade(
        event_type=event_type,
        ticker="PETR4",
        quantity=Decimal(quantity),
        unit_price=Decimal(unit_price),
    )


def test_market_price_projects_value_without_changing_historical_results() -> None:
    session = PortfolioSession()
    register_trade(session, FinancialEventType.BUY, "100", "30")
    register_trade(session, FinancialEventType.BUY, "100", "40")
    register_trade(session, FinancialEventType.SELL, "50", "50")

    portfolio = session.update_market_price(ticker="PETR4", current_price=Decimal("42"))

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("150"))
    assert position.cost == Money(Decimal("5250"))
    assert position.average_price == Money(Decimal("35"))
    assert position.current_price == Money(Decimal("42"))
    assert position.market_value == Money(Decimal("6300"))
    assert position.unrealized_result == Money(Decimal("1050"))
    assert position.unrealized_return_percentage == Decimal("20")
    assert position.realized_result == Money(Decimal("750"))
    assert portfolio.cash == Money(Decimal("-4500"))


@pytest.mark.parametrize(
    ("current_price", "market_value", "unrealized_result", "return_percentage"),
    [
        ("40", "4000", "1000", Decimal("33.33333333333333333333333333")),
        ("20", "2000", "-1000", Decimal("-33.33333333333333333333333333")),
        ("30", "3000", "0", Decimal("0")),
    ],
)
def test_market_price_handles_gain_loss_and_break_even(
    current_price: str,
    market_value: str,
    unrealized_result: str,
    return_percentage: Decimal,
) -> None:
    session = PortfolioSession()
    register_trade(session, FinancialEventType.BUY, "100", "30")

    position = session.update_market_price(
        ticker="PETR4",
        current_price=Decimal(current_price),
    ).positions[0]

    assert position.market_value == Money(Decimal(market_value))
    assert position.unrealized_result == Money(Decimal(unrealized_result))
    assert position.unrealized_return_percentage == return_percentage


def test_successive_price_updates_only_change_valuation() -> None:
    session = PortfolioSession()
    register_trade(session, FinancialEventType.BUY, "100", "30")

    first = session.update_market_price(ticker="PETR4", current_price=Decimal("35")).positions[0]
    second = session.update_market_price(ticker="PETR4", current_price=Decimal("40")).positions[0]

    assert first.market_value == Money(Decimal("3500"))
    assert second.market_value == Money(Decimal("4000"))
    assert second.quantity == Quantity(Decimal("100"))
    assert second.cost == Money(Decimal("3000"))
    assert second.average_price == Money(Decimal("30"))
    assert second.realized_result == Money.zero()


@pytest.mark.parametrize("current_price", [Decimal("0"), Decimal("-10")])
def test_rejects_non_positive_market_price(current_price: Decimal) -> None:
    session = PortfolioSession()
    register_trade(session, FinancialEventType.BUY, "100", "30")

    with pytest.raises(ValueError, match="preço atual"):
        session.update_market_price(ticker="PETR4", current_price=current_price)


def test_zero_position_has_zero_unrealized_values() -> None:
    session = PortfolioSession()
    register_trade(session, FinancialEventType.BUY, "100", "30")
    register_trade(session, FinancialEventType.SELL, "100", "50")

    position = session.update_market_price(ticker="PETR4", current_price=Decimal("42")).positions[0]

    assert position.quantity == Quantity(Decimal("0"))
    assert position.market_value == Money.zero()
    assert position.unrealized_result == Money.zero()
    assert position.unrealized_return_percentage == Decimal("0")
