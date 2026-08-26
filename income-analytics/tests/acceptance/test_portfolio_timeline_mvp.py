from __future__ import annotations

from datetime import date
from decimal import Decimal

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity


def trade(
    session: PortfolioSession,
    event_type: FinancialEventType,
    effective_date: date,
    quantity: str,
    unit_price: str,
) -> None:
    session.register_trade(
        event_type=event_type,
        ticker="PETR4",
        quantity=Decimal(quantity),
        unit_price=Decimal(unit_price),
        effective_date=effective_date,
    )


def test_projects_portfolio_as_of_each_relevant_date() -> None:
    session = PortfolioSession()
    january_5 = date(2026, 1, 5)
    january_10 = date(2026, 1, 10)
    january_20 = date(2026, 1, 20)
    january_25 = date(2026, 1, 25)
    january_31 = date(2026, 1, 31)
    trade(session, FinancialEventType.BUY, january_5, "100", "30")
    trade(session, FinancialEventType.BUY, january_10, "100", "40")
    trade(session, FinancialEventType.SELL, january_20, "50", "50")
    session.register_dividend(
        ticker="PETR4",
        amount=Decimal("120"),
        effective_date=january_25,
    )
    for effective_date, price in (
        (january_5, "30"),
        (january_10, "40"),
        (january_20, "50"),
        (january_31, "42"),
    ):
        session.update_market_price(
            ticker="PETR4",
            current_price=Decimal(price),
            effective_date=effective_date,
        )

    january_5_portfolio = session.projection(as_of=january_5)
    january_10_portfolio = session.projection(as_of=january_10)
    january_20_portfolio = session.projection(as_of=january_20)
    january_25_portfolio = session.projection(as_of=january_25)
    january_31_portfolio = session.projection(as_of=january_31)

    assert january_5_portfolio.positions[0].quantity == Quantity(Decimal("100"))
    assert january_5_portfolio.total_cost == Money(Decimal("3000"))
    assert january_5_portfolio.total_market_value == Money(Decimal("3000"))
    assert january_5_portfolio.cash == Money(Decimal("-3000"))
    assert january_10_portfolio.positions[0].quantity == Quantity(Decimal("200"))
    assert january_10_portfolio.total_cost == Money(Decimal("7000"))
    assert january_10_portfolio.total_market_value == Money(Decimal("8000"))
    assert january_20_portfolio.positions[0].quantity == Quantity(Decimal("150"))
    assert january_20_portfolio.total_realized_result == Money(Decimal("750"))
    assert january_20_portfolio.total_market_value == Money(Decimal("7500"))
    assert january_25_portfolio.income_received == Money(Decimal("120"))
    assert january_25_portfolio.cash == Money(Decimal("-4380"))
    assert january_31_portfolio.total_market_value == Money(Decimal("6300"))
    assert january_31_portfolio.total_result == Money(Decimal("1920"))


def test_orders_events_by_effective_date_instead_of_registration_order() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, date(2026, 1, 10), "100", "40")
    trade(session, FinancialEventType.SELL, date(2026, 1, 20), "50", "50")
    trade(session, FinancialEventType.BUY, date(2026, 1, 5), "100", "30")

    position = session.projection().positions[0]
    assert position.quantity == Quantity(Decimal("150"))
    assert position.cost == Money(Decimal("5250"))
    assert position.average_price == Money(Decimal("35"))
    assert position.realized_result == Money(Decimal("750"))


def test_uses_only_the_latest_market_price_available_as_of_the_requested_date() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, date(2026, 1, 5), "100", "30")
    for effective_date, price in (
        (date(2026, 1, 10), "40"),
        (date(2026, 1, 20), "50"),
        (date(2026, 1, 31), "42"),
    ):
        session.update_market_price(
            ticker="PETR4",
            current_price=Decimal(price),
            effective_date=effective_date,
        )

    january_15 = session.projection(as_of=date(2026, 1, 15)).positions[0]
    january_25 = session.projection(as_of=date(2026, 1, 25)).positions[0]
    january_31 = session.projection(as_of=date(2026, 1, 31)).positions[0]
    assert january_15.current_price == Money(Decimal("40"))
    assert january_25.current_price == Money(Decimal("50"))
    assert january_31.current_price == Money(Decimal("42"))
    before_first_price = session.projection(as_of=date(2026, 1, 8))
    assert before_first_price.positions[0].current_price is None


def test_same_date_events_use_registration_order_as_a_stable_tiebreaker() -> None:
    session = PortfolioSession()
    effective_date = date(2026, 1, 5)
    trade(session, FinancialEventType.BUY, effective_date, "100", "30")
    trade(session, FinancialEventType.SELL, effective_date, "50", "40")

    position = session.projection(as_of=effective_date).positions[0]
    assert position.quantity == Quantity(Decimal("50"))
    assert position.cost == Money(Decimal("1500"))
    assert position.realized_result == Money(Decimal("500"))


def test_history_contains_derived_snapshots_at_each_relevant_date() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, date(2026, 1, 5), "100", "30")
    session.update_market_price(
        ticker="PETR4",
        current_price=Decimal("30"),
        effective_date=date(2026, 1, 5),
    )
    trade(session, FinancialEventType.BUY, date(2026, 1, 10), "100", "40")
    session.update_market_price(
        ticker="PETR4",
        current_price=Decimal("40"),
        effective_date=date(2026, 1, 10),
    )

    history = session.portfolio_history()

    assert [snapshot.effective_date for snapshot in history.snapshots] == [
        date(2026, 1, 5),
        date(2026, 1, 10),
    ]
    assert history.snapshots[-1].portfolio.total_cost == Money(Decimal("7000"))


def test_future_events_do_not_change_a_previous_as_of_projection() -> None:
    session = PortfolioSession()
    trade(session, FinancialEventType.BUY, date(2026, 1, 5), "100", "30")
    trade(session, FinancialEventType.BUY, date(2030, 1, 1), "100", "40")

    portfolio = session.projection(as_of=date(2026, 1, 31))

    assert portfolio.positions[0].quantity == Quantity(Decimal("100"))
    assert portfolio.total_cost == Money(Decimal("3000"))
