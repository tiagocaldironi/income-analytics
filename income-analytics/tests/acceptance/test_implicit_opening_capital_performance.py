from datetime import date, timedelta
from decimal import Decimal

from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.financial_event_type import FinancialEventType


def test_twr_uses_implicit_opening_capital_when_legacy_purchase_has_no_cash_event() -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="VIVT3",
        quantity=Decimal("10"),
        unit_price=Decimal("100"),
        effective_date=date(2025, 1, 2),
    )
    start = date(2025, 1, 2)
    end = date(2025, 12, 31)
    duration = Decimal((end - start).days)
    current = start
    while current <= end:
        progress = Decimal((current - start).days) / duration
        price = Decimal("100") + Decimal("10") * progress
        session.update_market_price(ticker="VIVT3", current_price=price, effective_date=current)
        current += timedelta(days=5)
    session.update_market_price(ticker="VIVT3", current_price=Decimal("110"), effective_date=end)

    performance = session.performance(start_date=date(2025, 1, 2), end_date=date(2025, 12, 31))

    assert performance.twr == Decimal("0.1")
