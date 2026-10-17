"""Regression coverage for economic-date, rather than ingestion-time, semantics."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.application.wealth_explanation import WealthExplanationService
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)
from income_analytics.domain.recurring_rule import RecurrenceFrequency, RecurringRule


def _explanation(session: PortfolioSession) -> WealthExplanationService:
    return WealthExplanationService(
        events=session.history(),
        portfolio_at=lambda as_of: session.projection(as_of=as_of),
        valuation_at=lambda as_of: session.base_currency_valuation(as_of=as_of),
        performance_at=lambda start, end: session.performance(start_date=start, end_date=end),
    )


def test_retroactive_buy_and_sell_are_projected_by_effective_date() -> None:
    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("10"),
        unit_price=Decimal("30"),
        effective_date=date(2024, 1, 1),
    )
    session.register_trade(
        event_type=FinancialEventType.SELL,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("10"),
        unit_price=Decimal("35"),
        effective_date=date(2025, 6, 1),
    )

    before_sale = session.projection(as_of=date(2025, 5, 31))
    after_sale = session.projection(as_of=date(2025, 6, 2))
    before_buy = session.projection(as_of=date(2023, 12, 31))

    assert before_sale.positions[0].quantity.value == Decimal("10")
    assert after_sale.positions[0].quantity.value == Decimal("0")
    assert before_buy.positions == ()


def test_registration_timestamp_does_not_change_historical_economics() -> None:
    first = PortfolioSession()
    second = PortfolioSession()
    for session in (first, second):
        session.register_trade(
            event_type=FinancialEventType.BUY,
            ticker="PETR4",
            asset_class=AssetClass.BRAZILIAN_STOCK,
            quantity=Decimal("10"),
            unit_price=Decimal("30"),
            effective_date=date(2025, 6, 15),
        )
    first.history()[0].registered_at = datetime(2025, 6, 15, tzinfo=UTC)
    second.history()[0].registered_at = datetime(2026, 9, 23, tzinfo=UTC)

    assert first.projection(as_of=date(2025, 12, 31)).total_cost == (
        second.projection(as_of=date(2025, 12, 31)).total_cost
    )


def test_late_historical_market_price_is_eligible_at_its_reference_date() -> None:
    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("10"),
        unit_price=Decimal("30"),
        effective_date=date(2025, 6, 15),
    )
    session.update_market_price(
        ticker="PETR4",
        current_price=Decimal("40"),
        effective_date=date(2025, 12, 31),
        retrieved_at=datetime(2026, 9, 23, tzinfo=UTC),
    )

    position = session.projection(as_of=date(2025, 12, 31)).positions[0]
    assert position.market_value.amount == Decimal("400")


def test_retroactive_fixed_income_uses_application_date_not_creation_time() -> None:
    session = PortfolioSession()
    session.register_fixed_income_asset(
        ticker="CDB-RETRO",
        name="CDB retroativo",
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.PREFIXED,
        application_date=date(2024, 3, 15),
        principal_amount=Decimal("10000"),
        contracted_rate=Decimal("10"),
    )

    assert session.projection(as_of=date(2024, 3, 14)).positions == ()
    position = session.projection(as_of=date(2024, 12, 31)).positions[0]
    assert position.market_value.amount > Decimal("10000")


def test_pension_and_real_estate_preserve_their_report_and_valuation_dates() -> None:
    session = PortfolioSession()
    session.register_pension_plan(
        ticker="PGBL-RETRO",
        name="Previdência",
        pension_type="PGBL",
        institution="Banco",
        plan_name="Plano",
        tax_regime="REGRESSIVO",
        start_date=date(2020, 1, 1),
        reported_balance=Decimal("80000"),
        reported_balance_date=date(2025, 12, 31),
    )
    session.register_real_estate(
        ticker="IMOVEL-RETRO",
        name="Imóvel",
        property_type="APARTAMENTO",
        description="Apartamento residencial",
        cep="01001-000",
        acquisition_date=date(2020, 1, 1),
        acquisition_value=Decimal("400000"),
        current_manual_value=Decimal("600000"),
        valuation_date=date(2026, 1, 1),
    )

    at_2020 = {
        str(item.asset.ticker): item
        for item in session.projection(as_of=date(2020, 1, 1)).positions
    }
    at_2025 = {
        str(item.asset.ticker): item
        for item in session.projection(as_of=date(2025, 12, 31)).positions
    }
    at_2026 = {
        str(item.asset.ticker): item
        for item in session.projection(as_of=date(2026, 1, 1)).positions
    }

    assert at_2020["IMOVEL-RETRO"].market_value.amount == Decimal("400000")
    assert "PGBL-RETRO" not in at_2020
    assert at_2025["PGBL-RETRO"].market_value.amount == Decimal("80000")
    assert at_2025["IMOVEL-RETRO"].market_value.amount == Decimal("400000")
    assert at_2026["IMOVEL-RETRO"].market_value.amount == Decimal("600000")


def test_recurring_occurrence_keeps_the_scheduled_economic_date() -> None:
    session = PortfolioSession()
    rule = RecurringRule(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("100"),
        frequency=RecurrenceFrequency.MONTHLY,
        next_execution_date=date(2026, 8, 1),
    )
    session.schedule_recurring_rule(rule)
    session.execute_recurring_rules(through=date(2026, 8, 5))

    assert session.history()[0].effective_date == date(2026, 8, 1)


def test_entender_and_twr_use_retroactive_event_dates_and_rebuild_on_demand() -> None:
    session = PortfolioSession()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("100"),
        effective_date=date(2025, 1, 1),
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("10"),
        unit_price=Decimal("10"),
        effective_date=date(2025, 1, 1),
    )
    quote_date = date(2025, 1, 1)
    while quote_date <= date(2025, 12, 31):
        if quote_date.weekday() < 5:
            session.update_market_price(
                ticker="PETR4",
                current_price=Decimal("11") if quote_date == date(2025, 12, 31) else Decimal("10"),
                effective_date=quote_date,
            )
        quote_date += timedelta(days=1)

    before = (
        _explanation(session)
        .explain(start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))
        .payload
    )
    session.register_income(
        event_type=FinancialEventType.DIVIDEND,
        asset=session._assets["PETR4"],
        amount=Decimal("5"),
        effective_date=date(2025, 7, 15),
    )
    after = (
        _explanation(session)
        .explain(start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))
        .payload
    )
    performance = session.performance(start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))

    assert before["reconciliation"]["paid_income"] == Decimal("0")
    assert after["reconciliation"]["paid_income"] == Decimal("5")
    assert performance.twr == Decimal("0.15")
