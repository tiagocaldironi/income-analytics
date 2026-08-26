from __future__ import annotations

from decimal import Decimal

import pytest

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity


def test_session_projects_trades_for_the_local_dashboard() -> None:
    session = PortfolioSession()

    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        quantity=Decimal("100"),
        unit_price=Decimal("30"),
    )
    portfolio = session.register_trade(
        event_type=FinancialEventType.SELL,
        ticker="PETR4",
        quantity=Decimal("50"),
        unit_price=Decimal("50"),
    )

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("50"))
    assert position.cost == Money(Decimal("1500"))
    assert position.realized_result == Money(Decimal("1000"))
    assert portfolio.cash == Money(Decimal("-500"))


def test_session_does_not_record_an_invalid_sale() -> None:
    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        quantity=Decimal("100"),
        unit_price=Decimal("30"),
    )

    with pytest.raises(ValueError, match="more than"):
        session.register_trade(
            event_type=FinancialEventType.SELL,
            ticker="PETR4",
            quantity=Decimal("101"),
            unit_price=Decimal("40"),
        )

    assert len(session.history()) == 1
