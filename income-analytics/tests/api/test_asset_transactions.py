from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from income_analytics.api.routers import dashboard
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.entities.currency import Currency
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from tests.unit.domain.builders import build_asset

BRL = Currency(code="BRL", name="Brazilian Real", symbol="R$", decimal_places=2)


def build_brl_asset(**overrides):
    return build_asset(currency=BRL, **overrides)


def event(asset, event_type, day, *, source=None, quantity=None, unit_price=None, amount=None):
    metadata = {"source": source} if source else {}
    return FinancialEvent(
        account_id=uuid4(),
        asset=asset,
        event_type=event_type,
        effective_date=date(2026, 8, day),
        occurred_at=datetime(2026, 8, day, tzinfo=UTC),
        registered_at=datetime(2026, 8, day, tzinfo=UTC) + timedelta(seconds=1),
        quantity=Quantity(Decimal(quantity)) if quantity else None,
        unit_price=Money(Decimal(unit_price)) if unit_price else None,
        amount=Money(Decimal(amount)) if amount else None,
        metadata=metadata,
    )


def test_asset_transactions_use_canonical_asset_id_and_preserve_event_facts(monkeypatch):
    weg = build_brl_asset(name="WEG")
    other = build_brl_asset(name="Vale")
    events = [
        event(weg, FinancialEventType.BUY, 1, quantity="16", unit_price="45.55"),
        event(weg, FinancialEventType.SELL, 3, source="B3", quantity="3", unit_price="50"),
        event(weg, FinancialEventType.DIVIDEND, 4, source="B3", amount="12.50"),
        event(other, FinancialEventType.BUY, 5, quantity="1", unit_price="99"),
    ]
    session = PortfolioSession()
    session._assets = {"WEGE3": weg, "VALE3": other}
    session._events = events
    monkeypatch.setattr(dashboard, "session", session)

    result = dashboard.get_asset_transactions(weg.id, page=1, page_size=10)

    assert result["asset_id"] == str(weg.id)
    assert result["total"] == 3
    assert [item["operation"] for item in result["items"]] == ["Dividendo", "Venda", "Compra"]
    assert {item["asset_id"] for item in result["items"]} == {str(weg.id)}
    assert result["items"][0]["quantity"] is None
    assert result["items"][0]["unit_price"] is None
    assert result["items"][0]["source"] == "B3"
    assert result["items"][-1]["source"] is None
    assert result["items"][-1]["currency_code"] == weg.currency.code


def test_asset_transactions_paginate_in_deterministic_descending_order(monkeypatch):
    asset = build_brl_asset()
    events = [
        event(asset, FinancialEventType.BUY, day, quantity="1", unit_price=str(day))
        for day in range(1, 13)
    ]
    session = PortfolioSession()
    session._assets = {"WEGE3": asset}
    session._events = events
    monkeypatch.setattr(dashboard, "session", session)

    first = dashboard.get_asset_transactions(asset.id, page=1, page_size=10)
    second = dashboard.get_asset_transactions(asset.id, page=2, page_size=10)

    assert [item["effective_date"].day for item in first["items"]] == list(range(12, 2, -1))
    assert [item["effective_date"].day for item in second["items"]] == [2, 1]
    assert first["has_next"] is True
    assert second["has_previous"] is True
    assert second["has_next"] is False


def test_asset_transactions_return_empty_for_known_asset_without_events(monkeypatch):
    asset = build_brl_asset()
    session = PortfolioSession()
    session._assets = {"WEGE3": asset}
    monkeypatch.setattr(dashboard, "session", session)

    result = dashboard.get_asset_transactions(asset.id)

    assert result["items"] == []
    assert result["total"] == 0


def test_asset_transactions_reject_unknown_identity_and_invalid_pagination(monkeypatch):
    session = PortfolioSession()
    monkeypatch.setattr(dashboard, "session", session)

    with pytest.raises(HTTPException, match="Ativo não encontrado") as unknown:
        dashboard.get_asset_transactions(uuid4())
    with pytest.raises(HTTPException, match="Paginação inválida") as invalid:
        dashboard.get_asset_transactions(uuid4(), page=0)

    assert unknown.value.status_code == 404
    assert invalid.value.status_code == 422
