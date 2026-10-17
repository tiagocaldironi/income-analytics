from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from income_analytics.api.routers import dashboard
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType


def _session_without_a_confirmed_opening_balance() -> PortfolioSession:
    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("10"),
        unit_price=Decimal("100"),
        effective_date=date(2026, 1, 1),
    )
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("100"), effective_date=date(2026, 1, 1)
    )
    return session


def test_portfolio_payload_hides_unconfirmed_negative_cash(monkeypatch) -> None:
    session = _session_without_a_confirmed_opening_balance()
    monkeypatch.setattr(dashboard, "session", session)

    payload = dashboard.serialize_portfolio(
        session.projection(as_of=date(2026, 1, 1)), as_of=date(2026, 1, 1)
    )

    assert payload["cash"] is None
    assert payload["confirmed_cash"] is None
    assert payload["cash_status"] == "UNKNOWN"
    assert payload["reconstructed_cash_effect"] == Decimal("-1000")
    assert payload["portfolio_equity"] is None
    assert payload["reconstructed_portfolio_equity"] == Decimal("0")
    assert payload["history_boundary"]["boundary_date"] == date(2026, 1, 1)
    assert [event.event_type for event in session.history()] == [FinancialEventType.BUY]


def test_compact_dashboard_payload_omits_unused_history(monkeypatch) -> None:
    session = _session_without_a_confirmed_opening_balance()
    monkeypatch.setattr(dashboard, "session", session)

    full = dashboard.serialize_portfolio(session.projection())
    compact = dashboard.serialize_portfolio(session.projection(), include_history=False)

    assert len(full["history"]) == 1
    assert "history" not in compact
    assert {key: value for key, value in full.items() if key != "history"} == compact


def test_dashboard_get_never_rebuilds_a_missing_read_model(monkeypatch) -> None:
    monkeypatch.setattr(dashboard.dashboard_snapshot_repository, "get", lambda: None)
    monkeypatch.setattr(
        dashboard,
        "rebuild_portfolio_dashboard_snapshot",
        lambda: pytest.fail("GET must not rebuild the dashboard read model"),
    )

    with pytest.raises(HTTPException) as error:
        dashboard.get_portfolio_dashboard()

    assert error.value.status_code == 503


def test_startup_skips_rebuild_for_current_dashboard_schema(monkeypatch) -> None:
    current = {
        "read_model_version": dashboard.PORTFOLIO_DASHBOARD_READ_MODEL_VERSION,
        "version": 4,
    }
    monkeypatch.setattr(dashboard.dashboard_snapshot_repository, "get", lambda: current)
    monkeypatch.setattr(
        dashboard,
        "rebuild_portfolio_dashboard_snapshot",
        lambda: pytest.fail("A current read model must be reused at startup"),
    )

    assert dashboard.ensure_portfolio_dashboard_snapshot_current() is current


def test_portfolio_history_does_not_publish_reconstructed_cash_as_balance(monkeypatch) -> None:
    session = _session_without_a_confirmed_opening_balance()
    monkeypatch.setattr(dashboard, "session", session)

    payload = dashboard.get_portfolio_history(period_months=0)

    assert payload["cash_status"] == "UNKNOWN"
    assert payload["history_boundary"]["source"] == "FIRST_OBSERVED_FINANCIAL_EVENT"
    assert all(point["cash"] is None for point in payload["snapshots"])
    assert all(
        point["reconstructed_cash_effect"] == Decimal("-1000")
        for point in payload["snapshots"]
    )
