from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from income_analytics.application.portfolio_session import PortfolioSession
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


def test_twr_geometrically_neutralizes_a_contribution() -> None:
    session = PortfolioSession()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("10000"),
        effective_date=date(2026, 1, 1),
    )
    register_buy(session, date(2026, 1, 2))
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("110"), effective_date=date(2026, 1, 31)
    )
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("9000"),
        effective_date=date(2026, 2, 1),
    )
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("130"), effective_date=date(2026, 2, 28)
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
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("110"), effective_date=date(2026, 1, 31)
    )
    session.register_external_flow(
        event_type=FinancialEventType.WITHDRAWAL,
        amount=Decimal("2000"),
        effective_date=date(2026, 2, 1),
    )
    after_withdrawal = session.projection()
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("115"), effective_date=date(2026, 2, 28)
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
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("110"), effective_date=date(2027, 1, 1)
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
