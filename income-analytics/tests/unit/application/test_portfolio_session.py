from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity


def test_session_projects_trades_for_the_local_dashboard() -> None:
    session = PortfolioSession()

    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        quantity=Decimal("100"),
        unit_price=Decimal("30"),
    )
    portfolio = session.register_trade(
        event_type=FinancialEventType.SELL,
        ticker="PETR4",
        quantity=Decimal("50"),
        unit_price=Decimal("50"),
    )

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("50"))
    assert position.cost == Money(Decimal("1500"))
    assert position.realized_result == Money(Decimal("1000"))
    assert portfolio.cash == Money(Decimal("-500"))


def test_session_does_not_record_an_invalid_sale() -> None:
    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        quantity=Decimal("100"),
        unit_price=Decimal("30"),
    )

    with pytest.raises(ValueError, match="more than"):
        session.register_trade(
            event_type=FinancialEventType.SELL,
            ticker="PETR4",
            quantity=Decimal("101"),
            unit_price=Decimal("40"),
        )

    assert len(session.history()) == 1


def test_session_registers_crypto_trade_with_decimal_usd_price() -> None:
    session = PortfolioSession()

    portfolio = session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="SOL",
        name="Solana",
        asset_class=AssetClass.CRYPTO,
        country="US",
        currency_code="USD",
        quantity=Decimal("1"),
        unit_price=Decimal("82.98"),
        effective_date=date(2026, 2, 11),
    )

    position = portfolio.positions[0]
    assert position.asset.asset_class is AssetClass.CRYPTO
    assert position.asset.currency.code == "USD"
    assert position.quantity == Quantity(Decimal("1"))
    assert position.average_price == Money(Decimal("82.98"))


def test_session_creates_us_reit_with_explicit_domain_type() -> None:
    session = PortfolioSession()

    portfolio = session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PLD",
        name="Prologis",
        asset_class=AssetClass.US_REIT,
        country="US",
        currency_code="USD",
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        effective_date=date(2026, 8, 28),
    )

    assert portfolio.positions[0].asset.asset_type is AssetType.REIT


def test_historical_crypto_trade_ignores_fixed_income_not_yet_applied() -> None:
    session = PortfolioSession()
    session.register_fixed_income_asset(
        ticker="CDB-FUTURO",
        name="CDB futuro",
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.PREFIXED,
        application_date=date(2026, 8, 30),
        principal_amount=Decimal("1000"),
        contracted_rate=Decimal("10"),
    )

    portfolio = session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="SOL",
        name="Solana",
        asset_class=AssetClass.CRYPTO,
        country="US",
        currency_code="USD",
        quantity=Decimal("0.5"),
        unit_price=Decimal("82.98"),
        effective_date=date(2026, 2, 11),
    )

    position = next(item for item in portfolio.positions if str(item.asset.ticker) == "SOL")
    assert position.quantity == Quantity(Decimal("0.5"))
    assert position.average_price == Money(Decimal("82.98"))
    event = session.history()[-1]
    assert str(event.asset.ticker) == "SOL"
    assert event.quantity == Quantity(Decimal("0.5"))
    assert event.unit_price == Money(Decimal("82.98"))


def test_explicit_buy_reclassifies_an_existing_stock_as_brazilian_etf() -> None:
    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="BOVA11",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
    )

    portfolio = session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="BOVA11",
        asset_class=AssetClass.BRAZILIAN_ETF,
        quantity=Decimal("1"),
        unit_price=Decimal("110"),
    )

    position = portfolio.positions[0]
    assert position.asset.asset_class is AssetClass.BRAZILIAN_ETF
    assert position.quantity == Quantity(Decimal("2"))


def test_explicit_buy_reclassifies_an_existing_stock_as_fii() -> None:
    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="SNAG11",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("1"),
        unit_price=Decimal("10"),
    )

    portfolio = session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="SNAG11",
        asset_class=AssetClass.FII,
        quantity=Decimal("1"),
        unit_price=Decimal("11"),
    )

    assert portfolio.positions[0].asset.asset_class is AssetClass.FII


def test_imported_history_preserves_provider_and_is_idempotent() -> None:
    from income_analytics.application.market_data import MarketPriceObservation

    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY, ticker="WEGE3", quantity=Decimal("1"),
        unit_price=Decimal("10"), effective_date=date(2025, 1, 2),
    )
    observation = MarketPriceObservation(
        symbol="WEGE3", price=Decimal("11"), currency_code="BRL",
        effective_date=date(2025, 1, 3), source="b3_cotahist",
    )

    assert session.import_market_price_history(ticker="WEGE3", prices=(observation,)) == 1
    assert session.import_market_price_history(ticker="WEGE3", prices=(observation,)) == 0
    imported = next(price for price in session._market_prices if price.effective_date == date(2025, 1, 3))
    assert imported.provider == "b3_cotahist"
