from datetime import date
from decimal import Decimal

from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)


def test_register_fixed_income_asset_records_contract_and_principal() -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )

    asset = session.register_fixed_income_asset(
        ticker="CDB-2030",
        name="CDB Banco Exemplo 2030",
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.CDI_PERCENT,
        application_date=date(2026, 8, 27),
        principal_amount=Decimal("1000.00"),
        percentage_of_indexer=Decimal("110"),
        maturity_date=date(2030, 8, 27),
    )

    details = session.fixed_income_details("CDB-2030")

    assert details.asset_id == asset.id
    assert details.percentage_of_indexer == Decimal("110")
    assert session.projection().positions[0].cost.amount == Decimal("1000.00")


def test_register_rdb_uses_the_same_cdi_contract_rules_as_cdb() -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )

    session.register_fixed_income_asset(
        ticker="RDB-FINTECH",
        name="RDB Fintech",
        instrument_type=FixedIncomeInstrumentType.RDB,
        indexer_type=FixedIncomeIndexerType.CDI_PERCENT,
        application_date=date(2026, 8, 27),
        principal_amount=Decimal("1000.00"),
        percentage_of_indexer=Decimal("110"),
        issuer="Fintech Exemplo",
    )

    details = session.fixed_income_details("RDB-FINTECH")
    assert details.instrument_type is FixedIncomeInstrumentType.RDB


def test_session_uses_contract_curve_for_prefixed_position() -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    session.register_fixed_income_asset(
        ticker="CDB-PRE",
        name="CDB Prefixado",
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.PREFIXED,
        application_date=date(2025, 1, 1),
        principal_amount=Decimal("1000"),
        contracted_rate=Decimal("10"),
    )

    position = session.projection(as_of=date(2026, 1, 1)).positions[0]

    assert position.market_value.amount == Decimal("1100")


def test_session_registers_pension_and_real_estate_as_non_listed_positions() -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    session.register_pension_plan(
        ticker="PGBL-01",
        name="Previdência",
        pension_type="PGBL",
        institution="Banco",
        plan_name="Plano",
        tax_regime="REGRESSIVO",
        start_date=date(2020, 1, 1),
        reported_balance=Decimal("1000"),
        reported_balance_date=date(2026, 1, 1),
    )
    session.register_real_estate(
        ticker="IMOVEL-01",
        name="Apartamento",
        property_type="APARTAMENTO",
        description="Apartamento residencial",
        cep="01001-000",
        current_manual_value=Decimal("500000"),
        valuation_date=date(2026, 1, 1),
    )

    positions = {
        str(position.asset.ticker): position for position in session.projection().positions
    }

    assert positions["PGBL-01"].market_value.amount == Decimal("1000")
    assert positions["IMOVEL-01"].market_value.amount == Decimal("500000")
