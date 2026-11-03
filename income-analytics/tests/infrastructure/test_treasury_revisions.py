from datetime import date
from decimal import Decimal as D
from uuid import uuid4

import pytest

from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.infrastructure.treasury_revisions import save_revision


def test_persisted_revision_is_scoped_versioned_and_keeps_source_facts():
    session = PortfolioSession(portfolio_id=MAIN_PORTFOLIO_ID, persistent=True)
    ticker = "TD-" + uuid4().hex[:10].upper()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker=ticker,
        name="Tesouro Selic 2031",
        asset_class=AssetClass.FIXED_INCOME,
        asset_type=AssetType.TREASURY,
        quantity=D("0.05"),
        unit_price=D("1000"),
        effective_date=date(2026, 1, 1),
    )
    original = next(event for event in session.history() if str(event.asset.ticker) == ticker)
    other_request = PortfolioSession(portfolio_id=MAIN_PORTFOLIO_ID, persistent=True)
    session.amend_treasury_trade(
        event_id=original.id,
        quantity=D("0.06"),
        unit_price=D("1000"),
        effective_date=date(2026, 1, 1),
        expected_revision=0,
    )
    reloaded = PortfolioSession(portfolio_id=MAIN_PORTFOLIO_ID, persistent=True)
    event = next(event for event in reloaded.history() if event.id == original.id)
    assert event.quantity.value == D("0.06")
    assert event.metadata["treasury_revisions"][0]["quantity"] == "0.05"
    assert event.asset.id == original.asset.id
    with pytest.raises(ValueError, match="alterado"):
        other_request.amend_treasury_trade(
            event_id=original.id,
            quantity=D("0.07"),
            unit_price=D("1000"),
            effective_date=date(2026, 1, 1),
            expected_revision=0,
        )
    with pytest.raises(ValueError, match="nesta carteira"):
        save_revision(event, uuid4(), expected_revision=1)
    assert next(
        event for event in other_request.history() if event.id == original.id
    ).quantity.value == D("0.05")
