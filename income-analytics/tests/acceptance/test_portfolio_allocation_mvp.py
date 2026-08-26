from __future__ import annotations

from datetime import date
from decimal import Decimal

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.financial_event_type import FinancialEventType


def add_position(session: PortfolioSession, ticker: str, market_value: str) -> None:
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker=ticker,
        quantity=Decimal("10"),
        unit_price=Decimal("100"),
        effective_date=date(2026, 1, 2),
    )
    session.update_market_price(
        ticker=ticker,
        current_price=Decimal(market_value) / Decimal("10"),
        effective_date=date(2026, 1, 31),
    )


def test_allocation_weights_and_concentration_use_market_value() -> None:
    session = PortfolioSession()
    for ticker, value in (
        ("PETR4", "4000"),
        ("BBAS3", "3000"),
        ("WEG3", "2000"),
        ("ITSA4", "1000"),
    ):
        add_position(session, ticker, value)

    allocation = session.allocation()
    weights = {
        str(asset.position.asset.ticker): asset.portfolio_weight for asset in allocation.assets
    }

    assert allocation.portfolio_market_value.amount == Decimal("10000")
    assert allocation.valuation_coverage == Decimal("1")
    assert sum(weight for weight in weights.values() if weight is not None) == Decimal("1")
    assert weights["PETR4"] == Decimal("0.4")
    assert allocation.largest_position_weight == Decimal("0.4")
    assert allocation.top_3_weight == Decimal("0.9")
    assert allocation.top_5_weight == Decimal("1")
    assert allocation.hhi == Decimal("0.30")


def test_missing_price_does_not_create_fictitious_weight() -> None:
    session = PortfolioSession()
    add_position(session, "PETR4", "5000")
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="BBAS3",
        quantity=Decimal("10"),
        unit_price=Decimal("100"),
        effective_date=date(2026, 1, 2),
    )

    allocation = session.allocation()

    assert allocation.valuation_coverage == Decimal("0.5")
    assert allocation.hhi is None
    assert all(asset.portfolio_weight is None for asset in allocation.assets)
