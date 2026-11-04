from datetime import date
from decimal import Decimal as D

import pytest

from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.application.treasury import (
    is_treasury,
    presentation,
    title_name,
    validate_trade,
)
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("LFT 01/03/2031", "Tesouro Selic 2031"),
        ("Tesouro IPCA+ 2045", "Tesouro IPCA+ 2045"),
        ("NTN-B Principal 2045", "Tesouro IPCA+ 2045"),
        ("NTN-B 2045", "Tesouro IPCA+ com Juros Semestrais 2045"),
        ("Tesouro Prefixado 2032", "Tesouro Prefixado 2032"),
        ("NTN-F 2035", "Tesouro Prefixado com Juros Semestrais 2035"),
        ("CDB Tesouro Selic 2031", None),
        ("FI-123", None),
        ("Tesouro RendA+ 2065", "Tesouro RendA+ 2065"),
    ],
)
def test_title_identity(raw, expected):
    assert title_name(raw) == expected


@pytest.mark.parametrize("quantity", ["0", "-0.01", "0.001", "0.055", "NaN", "Infinity"])
def test_invalid_quantity(quantity):
    with pytest.raises(ValueError):
        validate_trade(D(quantity), D("1000"))


def test_decimal_product_and_financial_discrepancy():
    validate_trade(D("0.05"), D("1234.5678"), D("61.73"))
    with pytest.raises(ValueError, match="divergente"):
        validate_trade(D("0.05"), D("1234.5678"), D("61.72"))


def test_fractional_title_buy_partial_sale_and_oversell_are_decimal():
    session = PortfolioSession(portfolio_id=MAIN_PORTFOLIO_ID, persistent=False)
    args = dict(
        ticker="TD-SELIC-2031",
        name="Tesouro Selic 2031",
        asset_class=AssetClass.FIXED_INCOME,
        asset_type=AssetType.TREASURY,
        effective_date=date(2026, 1, 1),
    )
    session.register_trade(
        event_type=FinancialEventType.BUY, quantity=D("0.05"), unit_price=D("1000"), **args
    )
    result = session.register_trade(
        event_type=FinancialEventType.SELL, quantity=D("0.02"), unit_price=D("1100"), **args
    )
    assert result.positions[0].quantity.value == D("0.03")
    assert result.positions[0].average_price.amount == D("1000")
    assert result.positions[0].cost.amount == D("30")
    assert session.history()[-1].total_amount.amount == D("22")
    count = len(session.history())
    with pytest.raises(ValueError):
        session.register_trade(
            event_type=FinancialEventType.SELL, quantity=D("0.04"), unit_price=D("1100"), **args
        )
    assert len(session.history()) == count
    with pytest.raises(ValueError):
        session.register_trade(
            event_type=FinancialEventType.BUY, quantity=D("0.001"), unit_price=D("1000"), **args
        )
    assert len(session.history()) == count


def test_legacy_units_are_preserved_and_bank_taxonomy_is_explicit():
    session = PortfolioSession(portfolio_id=MAIN_PORTFOLIO_ID, persistent=False)
    for ticker, kind in [
        ("FI-TD", FixedIncomeInstrumentType.TESOURO_DIRETO),
        ("FI-CDB", FixedIncomeInstrumentType.CDB),
    ]:
        asset = session.register_fixed_income_asset(
            ticker=ticker,
            name="Tesouro Selic 2031",
            instrument_type=kind,
            indexer_type=FixedIncomeIndexerType.PREFIXED,
            contracted_rate=D("0"),
            application_date=date(2026, 1, 1),
            principal_amount=D("500"),
        )
        details = session._fixed_income_details[asset.id]
        assert is_treasury(asset, details) == (kind == FixedIncomeInstrumentType.TESOURO_DIRETO)
        if is_treasury(asset, details):
            assert presentation(asset, details)["quantity_unit"] == "LEGACY_CONTRACT"
    assert [event.quantity.value for event in session.history()] == [D("1"), D("1")]


def test_explicit_bank_taxonomy_wins_over_a_misleading_name_and_unknown_treasury_has_fallback():
    session = PortfolioSession(portfolio_id=MAIN_PORTFOLIO_ID, persistent=False)
    bank = session._create_asset(
        "BANK",
        name="Tesouro Selic 2031",
        asset_class=AssetClass.FIXED_INCOME,
        asset_type=AssetType.CDB,
    )
    assert not is_treasury(bank)
    assert presentation(bank, None)["display_group"] == "FIXED_INCOME"
    unknown = session._create_asset(
        "FI-UNKNOWN",
        name="FI-UNKNOWN",
        asset_class=AssetClass.FIXED_INCOME,
        asset_type=AssetType.TREASURY,
    )
    assert presentation(unknown, None)["display_name"] == "Tesouro Direto — identificação pendente"
    assert not presentation(unknown, None)["treasury_trade_supported"]
