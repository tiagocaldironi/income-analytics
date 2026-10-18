from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from income_analytics.api.routers import dashboard
from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)


def _session_with_fixed_income() -> PortfolioSession:
    session = PortfolioSession(portfolio_id=MAIN_PORTFOLIO_ID, persistent=False)
    session.register_fixed_income_asset(
        ticker="FI-CDB-01",
        name="CDB Exemplo",
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.PREFIXED,
        application_date=date(2026, 1, 1),
        principal_amount=Decimal("1000.00"),
        contracted_rate=Decimal("0"),
    )
    return session


def test_fixed_income_sale_reduces_balance_by_amount_and_keeps_remainder(monkeypatch) -> None:
    session = _session_with_fixed_income()
    monkeypatch.setattr(dashboard, "session", session)
    monkeypatch.setattr(dashboard, "rebuild_portfolio_dashboard_snapshot", lambda: {})

    result = dashboard.create_fixed_income_sale(
        dashboard.FixedIncomeSaleInput(
            ticker="FI-CDB-01",
            amount=Decimal("250.00"),
            effective_date=date(2026, 10, 18),
        )
    )

    position = next(item for item in result["positions"] if item["ticker"] == "FI-CDB-01")
    assert position["quantity"] == Decimal("0.75")
    assert position["current_price"] == Decimal("1000.00")
    assert position["market_value"] == Decimal("750.00")
    assert result["total_market_value"] == Decimal("750.00")
    assert result["cash_status"]
    assert session.history()[-1].event_type.value == "SELL"
    assert session.history()[-1].total_amount.amount == Decimal("250.00")


def test_fixed_income_sale_cannot_exceed_the_position_balance(monkeypatch) -> None:
    session = _session_with_fixed_income()
    monkeypatch.setattr(dashboard, "session", session)

    with pytest.raises(HTTPException) as error:
        dashboard.create_fixed_income_sale(
            dashboard.FixedIncomeSaleInput(
                ticker="FI-CDB-01",
                amount=Decimal("1000.01"),
                effective_date=date(2026, 10, 18),
            )
        )

    assert error.value.status_code == 422
    assert len(session.history()) == 1


def test_fixed_income_sale_rejects_non_portfolio_asset_without_creating_it(monkeypatch) -> None:
    session = _session_with_fixed_income()
    monkeypatch.setattr(dashboard, "session", session)

    with pytest.raises(HTTPException) as error:
        dashboard.create_fixed_income_sale(
            dashboard.FixedIncomeSaleInput(
                ticker="FI-NOT-OWNED",
                amount=Decimal("50.00"),
                effective_date=date(2026, 10, 18),
            )
        )

    assert error.value.status_code == 422
    assert "FI-NOT-OWNED" not in session._assets


def test_operation_form_has_total_value_field_for_fixed_income_sales() -> None:
    from pathlib import Path

    static = Path("src/income_analytics/api/static")
    page = (static / "index.html").read_text(encoding="utf-8")
    script = (static / "js/features/operations.js").read_text(encoding="utf-8")

    assert 'id="fixed-income-sale-value"' in page
    assert "Ativo da carteira" in script
    assert 'createFixedIncomeSale({' in script
