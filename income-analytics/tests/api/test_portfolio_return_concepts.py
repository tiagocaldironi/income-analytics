from datetime import date, timedelta
from decimal import Decimal

from income_analytics.api.routers import dashboard
from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType


def _quotes(session: PortfolioSession, start: date, end: date, *, final: Decimal) -> None:
    current = start
    while current <= end:
        if current.weekday() < 5:
            session.update_market_price(
                ticker="PETR4",
                current_price=final if current >= end - timedelta(days=1) else Decimal("100"),
                effective_date=current,
            )
        current += timedelta(days=1)


def test_class_coverage_reports_the_actual_twr(monkeypatch) -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    start, end = date(2026, 1, 2), date(2026, 1, 30)
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        effective_date=start,
    )
    _quotes(session, start, end, final=Decimal("110"))
    monkeypatch.setattr(dashboard, "session", session)

    result = dashboard._class_performance_coverage(AssetClass.BRAZILIAN_STOCK, end)

    assert result["status"] == "AVAILABLE"
    assert result["twr"] == Decimal("0.1")
    assert result["performance_coverage_start_date"] == start


def test_performance_payload_income_is_limited_to_requested_period(monkeypatch) -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    start, end = date(2026, 1, 2), date(2026, 1, 30)
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        effective_date=start,
    )
    asset = session._assets["PETR4"]
    session.register_income(
        event_type=FinancialEventType.DIVIDEND,
        asset=asset,
        amount=Decimal("7"),
        effective_date=date(2025, 12, 30),
    )
    session.register_income(
        event_type=FinancialEventType.INTEREST_ON_EQUITY,
        asset=asset,
        amount=Decimal("5"),
        effective_date=date(2026, 1, 15),
    )
    _quotes(session, start, end, final=Decimal("100"))
    monkeypatch.setattr(dashboard, "session", session)

    result = dashboard._performance_payload(start, end)

    assert result["income"] == Decimal("5")
    assert result["twr"] == Decimal("0.05")
