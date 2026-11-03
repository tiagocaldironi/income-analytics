import asyncio
import json
from datetime import date
from decimal import Decimal as D

import pytest
from fastapi import HTTPException

from income_analytics.api.routers import dashboard
from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)
from income_analytics.main import app


@pytest.fixture
def session(monkeypatch):
    value = PortfolioSession(portfolio_id=MAIN_PORTFOLIO_ID, persistent=False)
    monkeypatch.setattr(dashboard, "session", value)
    monkeypatch.setattr(dashboard, "rebuild_portfolio_dashboard_snapshot", lambda: {})
    return value


def payload(**changes):
    return {
        "event_type": "BUY",
        "ticker": "TD-SELIC-2031",
        "name": "Tesouro Selic 2031",
        "quantity": "0.05",
        "unit_price": "1000",
        "effective_date": "2026-01-01",
        **changes,
    }


def post(body):
    sent = []
    received = False

    async def receive():
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": json.dumps(body).encode(), "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(
        app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/api/treasury/trades",
                "raw_path": b"/api/treasury/trades",
                "query_string": b"",
                "headers": [(b"content-type", b"application/json")],
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
                "root_path": "",
            },
            receive,
            send,
        )
    )
    return next(message["status"] for message in sent if message["type"] == "http.response.start")


def test_http_accepts_fraction_and_rejects_precision_and_total_discrepancy(session):
    assert post(payload(gross_amount="50")) == 201
    assert session.project().positions[0].quantity.value == D("0.05")
    assert post(payload(event_type="SELL", quantity="0.02", unit_price="1100")) == 201
    assert session.project().positions[0].quantity.value == D("0.03")
    assert post(payload(quantity="0.001")) == 422
    assert post(payload(quantity="-0.01")) == 422
    assert post(payload(gross_amount="51")) == 422
    assert post(payload(event_type="SELL", quantity="0.04")) == 422
    assert len(session.history()) == 2


def test_split_reconciles_values_weights_and_preserves_financial_class(session):
    dashboard.create_treasury_trade(dashboard.TreasuryTradeInput(**payload()))
    session.register_fixed_income_asset(
        ticker="FI-CDB",
        name="CDB Exemplo",
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.PREFIXED,
        contracted_rate=D("0"),
        application_date=date(2026, 1, 1),
        principal_amount=D("1000"),
    )
    session.update_market_price(
        ticker="TD-SELIC-2031", current_price=D("1000"), effective_date=date(2026, 1, 1)
    )
    before = session.project(as_of=date(2026, 1, 1))
    holdings = dashboard._build_portfolio_holdings(as_of=date(2026, 1, 1))
    groups = holdings["display_groups"]
    assert {group["asset_class"] for group in groups} == {"TREASURY", "FIXED_INCOME"}
    assert sum(group["market_value"] for group in groups) == holdings["portfolio_market_value"]
    assert sum(group["weight"] for group in groups) == D("1")
    assert sum(group["total_cost"] for group in groups) == before.total_cost.amount
    assert sum(group["total_result"] for group in groups) == before.total_result.amount
    assert len(holdings["classes"]) == 1
    assert holdings["classes"][0]["asset_class"] == "FIXED_INCOME"
    assert all(group["target_weight"] is None for group in groups)
    assert all(group["performance_coverage"] is None for group in groups)
    assert session.project(as_of=date(2026, 1, 1)) == before


def test_legacy_contract_cannot_be_reinterpreted_or_replaced(session):
    asset = session.register_fixed_income_asset(
        ticker="FI-TD",
        name="Tesouro Selic 2031",
        instrument_type=FixedIncomeInstrumentType.TESOURO_DIRETO,
        indexer_type=FixedIncomeIndexerType.SELIC,
        application_date=date(2026, 1, 1),
        principal_amount=D("1000"),
    )
    before = session.history()
    with pytest.raises(HTTPException) as error:
        dashboard.create_treasury_trade(dashboard.TreasuryTradeInput(**payload(ticker="FI-TD")))
    assert error.value.status_code == 422
    assert session.history() == before
    assert session._assets["FI-TD"].id == asset.id


def test_non_treasury_identity_and_unsupported_titles_are_not_reclassified(session):
    session.register_asset(ticker="PETR4", name="Petrobras", asset_class=AssetClass.BRAZILIAN_STOCK)
    with pytest.raises(HTTPException):
        dashboard.create_treasury_trade(dashboard.TreasuryTradeInput(**payload(ticker="PETR4")))
    with pytest.raises(HTTPException):
        dashboard.create_treasury_trade(
            dashboard.TreasuryTradeInput(**payload(ticker="TD-RENDA", name="Tesouro Renda+ 2065"))
        )
    assert session._assets["PETR4"].asset_class is AssetClass.BRAZILIAN_STOCK
    assert not session.history()


def test_amendment_preserves_identity_and_rejects_stale_revision_and_uncovered_sales(session):
    dashboard.create_treasury_trade(dashboard.TreasuryTradeInput(**payload()))
    original = session.history()[0]
    amended = dashboard.TreasuryAmendInput(**payload(quantity="0.06"), expected_revision=0)
    dashboard.amend_treasury_trade(original.id, amended)
    changed = session.history()[0]
    assert changed.id == original.id
    assert changed.asset.id == original.asset.id
    assert changed.registered_at == original.registered_at
    assert changed.quantity.value == D("0.06")
    assert changed.metadata["treasury_revisions"][0]["quantity"] == "0.05"
    with pytest.raises(HTTPException):
        dashboard.amend_treasury_trade(original.id, amended)
    dashboard.create_treasury_trade(
        dashboard.TreasuryTradeInput(**payload(event_type="SELL", quantity="0.04"))
    )
    with pytest.raises(HTTPException):
        dashboard.amend_treasury_trade(
            original.id,
            dashboard.TreasuryAmendInput(**payload(quantity="0.03"), expected_revision=1),
        )
    assert session.project().positions[0].quantity.value == D("0.02")


def test_read_model_version_refreshes_legacy_snapshot_without_changing_history(
    session, monkeypatch
):
    snapshot = {"read_model_version": 4}

    class Repository:
        def get(self):
            return snapshot

    calls = []

    def rebuild():
        calls.append(True)
        snapshot["read_model_version"] = dashboard.PORTFOLIO_DASHBOARD_READ_MODEL_VERSION
        return snapshot

    monkeypatch.setattr(dashboard, "dashboard_snapshot_repository", Repository())
    monkeypatch.setattr(dashboard, "rebuild_portfolio_dashboard_snapshot", rebuild)
    dashboard.ensure_portfolio_dashboard_snapshot_current()
    dashboard.ensure_portfolio_dashboard_snapshot_current()
    assert len(calls) == 1
    assert not session.history()
