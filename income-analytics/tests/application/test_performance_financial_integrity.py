from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType


def make_session(gap_date):
    session = PortfolioSession(portfolio_id=uuid4())
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="TEST3",
        quantity=Decimal("10"),
        unit_price=Decimal("100"),
        effective_date=date(2026, 1, 1),
        asset_class=AssetClass.BRAZILIAN_STOCK,
    )
    buy = session._events[0]
    session._events.append(
        replace(
            buy,
            id=uuid4(),
            event_type=FinancialEventType.SELL,
            unit_price=None,
            effective_date=gap_date,
            metadata={
                "financial_status": "DATA_GAP",
                "original_movement": "Transferência - Liquidação",
            },
        )
    )
    return session


@pytest.mark.parametrize("gap_date", [date(2026, 1, 2), date(2026, 2, 2)])
def test_missing_proceeds_before_or_inside_window_blocks_returns_without_rewriting_events(gap_date):
    session = make_session(gap_date)
    original = tuple(session._events)
    result = session.performance(start_date=date(2026, 2, 1), end_date=date(2026, 2, 28))
    assert result.twr is None and result.xirr is None
    assert result.performance_status == "INSUFFICIENT_DATA"
    assert "valor financeiro pendente" in result.unavailable_reason
    assert "TEST3" in result.unavailable_reason
    assert tuple(session._events) == original


def test_future_gap_does_not_block_an_earlier_valid_period():
    session = make_session(date(2026, 3, 1))
    for day in [1, 5]:
        session.update_market_price(
            ticker="TEST3", current_price=Decimal("100"), effective_date=date(2026, 1, day)
        )
    result = session.performance(start_date=date(2026, 1, 1), end_date=date(2026, 1, 5))
    assert result.twr == Decimal("0")
    assert result.performance_status == "AVAILABLE"


def test_gap_in_another_class_does_not_override_class_specific_reason():
    session = make_session(date(2026, 2, 2))
    result = session.performance(
        start_date=date(2026, 2, 1), end_date=date(2026, 2, 28), asset_class=AssetClass.FIXED_INCOME
    )
    assert "valor financeiro pendente" not in (result.unavailable_reason or "")


def test_invalid_interval_is_still_rejected_with_incomplete_trades():
    session = make_session(date(2026, 1, 2))
    with pytest.raises(ValueError):
        session.performance(start_date=date(2026, 3, 1), end_date=date(2026, 1, 1))
