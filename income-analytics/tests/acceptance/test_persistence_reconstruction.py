from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)


def test_persistent_session_reconstructs_asset_event_price_benchmark_and_policy() -> None:
    ticker = f"T{uuid4().hex[:8]}"
    first = PortfolioSession(persistent=True)
    first.register_trade(
        event_type=FinancialEventType.BUY,
        ticker=ticker,
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("2"),
        unit_price=Decimal("10"),
        effective_date=date(2026, 1, 1),
    )
    first.update_market_price(
        ticker=ticker, current_price=Decimal("12"), effective_date=date(2026, 1, 2)
    )
    first.register_benchmark_rate(
        name="TEST_CDI", return_percentage=Decimal("0.001"), effective_date=date(2026, 1, 2)
    )
    first.set_allocation_policy(
        AllocationPolicy(targets={AssetClass.BRAZILIAN_STOCK: Decimal("1")})
    )

    rebuilt = PortfolioSession(persistent=True)

    tickers = {str(position.asset.ticker) for position in rebuilt.projection().positions}
    assert ticker.upper() in tickers
    assert rebuilt.projection().total_market_value.amount >= Decimal("24")
    assert rebuilt._allocation_policy is not None


def test_persistent_clear_removes_data_after_session_reconstruction() -> None:
    ticker = f"C{uuid4().hex[:8]}"
    first = PortfolioSession(persistent=True)
    first.register_trade(
        event_type=FinancialEventType.BUY,
        ticker=ticker,
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("2"),
        unit_price=Decimal("10"),
        effective_date=date(2026, 1, 1),
    )
    first.update_market_price(
        ticker=ticker, current_price=Decimal("12"), effective_date=date(2026, 1, 2)
    )
    first.set_allocation_policy(
        AllocationPolicy(targets={AssetClass.BRAZILIAN_STOCK: Decimal("1")})
    )

    first.clear()
    rebuilt = PortfolioSession(persistent=True)

    assert rebuilt.projection().positions == ()
    assert rebuilt.history() == ()
    assert rebuilt._allocation_policy is None


def test_fixed_income_contract_survives_persistent_reconstruction() -> None:
    first = PortfolioSession(persistent=True)
    first.clear()
    first.register_fixed_income_asset(
        ticker="CDB-REBUILD",
        name="CDB para reconstrução",
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.PREFIXED,
        application_date=date(2026, 1, 1),
        principal_amount=Decimal("1000"),
        contracted_rate=Decimal("10"),
    )

    rebuilt = PortfolioSession(persistent=True)

    assert rebuilt.fixed_income_details("CDB-REBUILD").contracted_rate == Decimal("10")
    assert rebuilt.projection(as_of=date(2027, 1, 1)).positions[0].market_value.amount == Decimal(
        "1100"
    )


def test_non_listed_wealth_survives_persistent_reconstruction() -> None:
    first = PortfolioSession(persistent=True)
    first.clear()
    first.register_pension_plan(
        ticker="PGBL-REBUILD", name="Previdência", pension_type="PGBL",
        institution="Instituição", plan_name="Plano", tax_regime="REGRESSIVO",
        start_date=date(2020, 1, 1), reported_balance=Decimal("1000"),
        reported_balance_date=date(2026, 1, 1),
    )
    first.register_real_estate(
        ticker="IMOVEL-REBUILD", name="Imóvel", property_type="CASA",
        description="Casa residencial", cep="01001-000",
        current_manual_value=Decimal("500000"), valuation_date=date(2026, 1, 1),
    )

    rebuilt = PortfolioSession(persistent=True)
    values = {
        str(position.asset.ticker): position.market_value.amount
        for position in rebuilt.projection().positions
    }

    assert rebuilt._pension_plan_details
    assert rebuilt._real_estate_details
    assert values["PGBL-REBUILD"] == Decimal("1000")
    assert values["IMOVEL-REBUILD"] == Decimal("500000")
