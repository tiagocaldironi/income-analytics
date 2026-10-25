from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.infrastructure.sqlite_repositories import SqliteMarketPriceRepository
from income_analytics.main import app


def test_history_routes_do_not_load_market_quotes(monkeypatch):
    monkeypatch.setenv("INCOME_AUTH_MODE", "local")
    session = PortfolioSession(portfolio_id=MAIN_PORTFOLIO_ID, persistent=True)
    ticker = "H" + uuid4().hex[:8].upper()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker=ticker,
        quantity=Decimal("2"),
        unit_price=Decimal("10"),
        effective_date=date(2026, 1, 2),
    )
    asset_id = session._assets[ticker].id

    def forbidden(*args, **kwargs):
        raise AssertionError("History must not load quotes")

    monkeypatch.setattr(SqliteMarketPriceRepository, "list", forbidden)
    monkeypatch.setattr(SqliteMarketPriceRepository, "list_by_asset", forbidden)
    client = TestClient(app)
    for path in [
        "/api/operations",
        "/api/operations/history",
        f"/api/portfolio/assets/{asset_id}/transactions",
    ]:
        result = client.get(path, headers={"X-Portfolio-Id": str(MAIN_PORTFOLIO_ID)})
        assert result.status_code == 200, result.text
    result = client.get(
        f"/api/portfolio/assets/{asset_id}/transactions",
        headers={"X-Portfolio-Id": str(MAIN_PORTFOLIO_ID)},
    )
    assert any(Decimal(str(item["quantity"])) == 2 for item in result.json()["items"])
    with pytest.raises(AssertionError, match="History must not load quotes"):
        PortfolioSession(portfolio_id=MAIN_PORTFOLIO_ID, persistent=True)
