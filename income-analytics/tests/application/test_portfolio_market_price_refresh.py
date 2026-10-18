"""Portfolio quote refresh routes, batches and values a mixed-market portfolio."""

from datetime import UTC, date, datetime
from decimal import Decimal

from income_analytics.application.base_currency_valuation import BaseCurrencyValuationProjector
from income_analytics.application.fx_data import FxRateObservation
from income_analytics.application.market_data import MarketDataUnavailable, MarketPriceObservation
from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType


class BatchProvider:
    def __init__(self, source, quotes, *, unavailable=()):
        self.source = source
        self.quotes = quotes
        self.unavailable = set(unavailable)
        self.batches = []

    def latest_prices(self, symbols):
        self.batches.append(symbols)
        return {
            symbol: MarketPriceObservation(
                symbol=symbol,
                price=price,
                currency_code=currency,
                effective_date=date(2026, 9, 23),
                source=self.source,
                retrieved_at=datetime(2026, 9, 23, 15, tzinfo=UTC),
                provider_attempts=(
                    ("brapi", "NOT_FOUND", "not covered"),
                    (self.source, "SUCCESS", None),
                ),
            )
            for symbol, (price, currency) in self.quotes.items()
            if symbol in symbols and symbol not in self.unavailable
        }


def _mixed_session():
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    rows = (
        ("PETR4", AssetClass.BRAZILIAN_STOCK, "BRL", "BR", "2", "20"),
        ("KNRI11", AssetClass.FII, "BRL", "BR", "1", "100"),
        ("BTC", AssetClass.CRYPTO, "USD", "US", "0.1", "90000"),
        ("ETH", AssetClass.CRYPTO, "USD", "US", "1", "2500"),
        ("MCD", AssetClass.INTERNATIONAL, "USD", "US", "2", "280"),
        ("IVV", AssetClass.INTERNATIONAL_ETF, "USD", "US", "1", "480"),
        ("O", AssetClass.US_REIT, "USD", "US", "2", "45"),
    )
    for ticker, asset_class, currency, country, quantity, price in rows:
        session.register_trade(
            event_type=FinancialEventType.BUY,
            ticker=ticker,
            asset_class=asset_class,
            currency_code=currency,
            country=country,
            quantity=Decimal(quantity),
            unit_price=Decimal(price),
            effective_date=date(2026, 9, 1),
        )
    return session


def test_refresh_batches_by_provider_preserves_currency_and_calculates_fx_value():
    session = _mixed_session()
    brazil = BatchProvider(
        "brapi", {"PETR4": (Decimal("30"), "BRL"), "KNRI11": (Decimal("110"), "BRL")}
    )
    crypto = BatchProvider(
        "coingecko", {"BTC": (Decimal("100000"), "USD"), "ETH": (Decimal("3000"), "USD")}
    )
    us = BatchProvider(
        "twelve_data",
        {
            "MCD": (Decimal("300"), "USD"),
            "IVV": (Decimal("500"), "USD"),
            "O": (Decimal("50"), "USD"),
        },
    )
    by_class = {
        AssetClass.BRAZILIAN_STOCK: brazil,
        AssetClass.FII: brazil,
        AssetClass.CRYPTO: crypto,
        AssetClass.INTERNATIONAL: us,
        AssetClass.INTERNATIONAL_ETF: us,
        AssetClass.US_REIT: us,
    }
    result = session.refresh_open_market_prices_report(
        lambda asset: by_class[asset.asset_class], today=date(2026, 9, 23)
    )

    assert result["updated"] == 7
    assert result["unavailable"] == []
    assert brazil.batches == [("KNRI11", "PETR4")]
    assert crypto.batches == [("BTC", "ETH")]
    assert us.batches == [("IVV", "MCD", "O")]
    brazil_outcome = next(
        item["asset_results"] for item in result["providers"] if item["provider"] == "brapi"
    )
    assert brazil_outcome[0]["provider_attempts"] == [
        {"provider": "brapi", "result": "NOT_FOUND", "reason": "not covered"},
        {"provider": "brapi", "result": "SUCCESS", "reason": None},
    ]
    assert {price.provider for price in session._market_prices} == {
        "brapi",
        "coingecko",
        "twelve_data",
    }
    assert all(price.price_timestamp is None for price in session._market_prices)
    valuation = BaseCurrencyValuationProjector.project(
        session.projection(),
        base_currency="BRL",
        fx_rates=(
            FxRateObservation(
                base_currency="USD",
                quote_currency="BRL",
                rate=Decimal("5"),
                effective_date=date(2026, 9, 23),
                source="bcb_ptax",
            ),
        ),
        as_of=date(2026, 9, 23),
    )
    assert valuation.complete is True
    assert valuation.market_value == Decimal("71170")


def test_partial_failure_keeps_last_quote_and_reports_missing_symbols():
    session = _mixed_session()
    crypto = BatchProvider("coingecko", {"BTC": (Decimal("100000"), "USD")})
    result = session.refresh_open_market_prices_report(
        lambda asset: crypto,
        today=date(2026, 9, 23),
    )
    assert result["updated"] == 1
    assert set(result["unavailable"]) == {"ETH", "IVV", "KNRI11", "MCD", "O", "PETR4"}
    assert session._assets["ETH"].current_price is None


def test_wrong_provider_currency_is_rejected_without_overwriting_asset_price():
    session = _mixed_session()
    wrong = BatchProvider("bad", {"MCD": (Decimal("300"), "BRL")})
    result = session.refresh_open_market_prices_report(lambda _: wrong, today=date(2026, 9, 23))
    assert "MCD" in result["unavailable"]
    assert session._assets["MCD"].current_price is None


def test_assets_whose_valuation_does_not_use_market_quotes_are_skipped():
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="FI-2029-TEST",
        asset_class=AssetClass.FIXED_INCOME,
        currency_code="BRL",
        country="BR",
        quantity=Decimal("1"),
        unit_price=Decimal("1000"),
        effective_date=date(2026, 9, 1),
    )

    class NoQuoteProvider:
        source = "UnavailableMarketDataProvider"
        supports_quotes = False

        def latest_price(self, _symbol):
            raise AssertionError("Provedor sem cotação não deve ser consultado")

    result = session.refresh_open_market_prices_report(
        lambda _asset: NoQuoteProvider(), today=date(2026, 9, 23), force=True
    )

    assert result["updated"] == 0
    assert result["unavailable"] == []
    assert result["skipped"] == ["FI-2029-TEST"]
    assert result["providers"] == []


def test_provider_exception_does_not_stop_another_provider_group():
    session = _mixed_session()

    class FailedProvider:
        source = "failed"

        def latest_prices(self, _symbols):
            raise MarketDataUnavailable("unavailable")

    ok = BatchProvider(
        "coingecko", {"BTC": (Decimal("100000"), "USD"), "ETH": (Decimal("3000"), "USD")}
    )
    result = session.refresh_open_market_prices_report(
        lambda asset: ok if asset.asset_class is AssetClass.CRYPTO else FailedProvider(),
        today=date(2026, 9, 23),
    )
    assert result["updated"] == 2
    assert {item["status"] for item in result["providers"]} == {"SUCCESS", "FAILED"}


def test_us_failure_preserves_last_quote_and_a_later_refresh_recovers():
    session = _mixed_session()
    session.update_market_price(
        ticker="MCD",
        current_price=Decimal("280"),
        effective_date=date(2026, 9, 22),
        provider="twelve_data",
    )

    class FailedUsProvider:
        source = "twelve_data"

        def latest_prices(self, _symbols):
            raise MarketDataUnavailable("temporary provider failure")

    failed = session.refresh_open_market_prices_report(
        lambda asset: (
            FailedUsProvider() if str(asset.ticker) == "MCD" else BatchProvider("none", {})
        ),
        today=date(2026, 9, 23),
    )
    assert session._assets["MCD"].current_price.amount == Decimal("280")
    assert any(item["status"] == "FAILED" for item in failed["providers"])

    recovered = session.refresh_open_market_prices_report(
        lambda asset: (
            BatchProvider("twelve_data", {"MCD": (Decimal("300"), "USD")})
            if str(asset.ticker) == "MCD"
            else BatchProvider("none", {})
        ),
        today=date(2026, 9, 23),
    )
    assert session._assets["MCD"].current_price.amount == Decimal("300")
    assert any(item["status"] == "SUCCESS" for item in recovered["providers"])


def test_single_symbol_failure_does_not_interrupt_provider_group_and_records_error():
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    for ticker in ("AAA3", "BBB3"):
        session.register_trade(
            event_type=FinancialEventType.BUY,
            ticker=ticker,
            asset_class=AssetClass.BRAZILIAN_STOCK,
            currency_code="BRL",
            country="BR",
            quantity=Decimal("1"),
            unit_price=Decimal("10"),
            effective_date=date(2026, 9, 1),
        )

    class SingleQuoteProvider:
        source = "b3"

        def latest_price(self, symbol):
            if symbol == "AAA3":
                raise MarketDataUnavailable("ticker sem cotação na fonte")
            return MarketPriceObservation(
                symbol=symbol,
                price=Decimal("12"),
                currency_code="BRL",
                effective_date=date(2026, 9, 23),
                source=self.source,
            )

    provider = SingleQuoteProvider()
    result = session.refresh_open_market_prices_report(
        lambda _: provider,
        today=date(2026, 9, 23),
    )

    assert result["updated"] == 1
    assert result["unavailable"] == ["AAA3"]
    assert session._assets["BBB3"].current_price.amount == Decimal("12")
    outcome = result["providers"][0]
    assert outcome["status"] == "PARTIAL"
    assert outcome["failed_assets"] == ["AAA3"]
    assert outcome["errors"] == [
        {
            "asset": "AAA3",
            "stage": "single_quote",
            "error_type": "MarketDataUnavailable",
            "message": "ticker sem cotação na fonte",
        }
    ]


def test_same_day_refresh_is_idempotent_without_economic_drift():
    session = _mixed_session()
    provider = BatchProvider("brapi", {"PETR4": (Decimal("30"), "BRL")})

    first = session.refresh_open_market_prices_report(
        lambda asset: provider if str(asset.ticker) == "PETR4" else BatchProvider("none", {}),
        today=date(2026, 9, 23),
    )
    before = session.project(as_of=date(2026, 9, 23))
    second = session.refresh_open_market_prices_report(
        lambda asset: provider if str(asset.ticker) == "PETR4" else BatchProvider("none", {}),
        today=date(2026, 9, 23),
    )
    after = session.project(as_of=date(2026, 9, 23))

    assert first["updated"] == 1
    assert second["updated"] == 0
    assert "PETR4" in second["skipped"]
    assert before.total_market_value == after.total_market_value
    assert before.positions[0].quantity == after.positions[0].quantity


def test_forced_refresh_rechecks_quotes_already_recorded_today():
    session = _mixed_session()
    initial = BatchProvider("brapi", {"PETR4": (Decimal("30"), "BRL")})
    refreshed = BatchProvider("brapi", {"PETR4": (Decimal("31"), "BRL")})

    def provider_for(asset):
        if str(asset.ticker) == "PETR4":
            return initial if not session._market_prices else refreshed
        return BatchProvider("none", {})

    first = session.refresh_open_market_prices_report(provider_for, today=date(2026, 9, 23))
    forced = session.refresh_open_market_prices_report(
        provider_for, today=date(2026, 9, 23), force=True
    )

    assert first["updated"] == 1
    assert refreshed.batches == [("PETR4",)]
    assert forced["updated"] == 1
    assert session._assets["PETR4"].current_price.amount == Decimal("31")


def test_b3_etf_price_source_is_persisted_as_b3_etf():
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="AUPO11",
        asset_class=AssetClass.BRAZILIAN_ETF,
        currency_code="BRL",
        country="BR",
        quantity=Decimal("12"),
        unit_price=Decimal("108"),
        effective_date=date(2026, 9, 1),
    )

    class B3EtfProvider:
        def latest_price(self, symbol):
            return MarketPriceObservation(
                symbol=symbol,
                price=Decimal("111.94"),
                currency_code="BRL",
                effective_date=date(2026, 10, 6),
                source="b3_etf",
                provider_attempts=(
                    ("brapi", "NOT_FOUND", "ticker unavailable"),
                    ("b3_etf", "SUCCESS", None),
                    ("b3_cotahist", "NOT_REQUIRED", "provider anterior respondeu"),
                ),
            )

    result = session.refresh_open_market_prices_report(
        lambda _asset: B3EtfProvider(), today=date(2026, 10, 7)
    )

    assert result["updated"] == 1
    assert session._market_prices[0].provider == "b3_etf"
    assert session.projection().positions[0].asset.current_price.amount == Decimal("111.94")
    saved_attempts = result["providers"][0]["asset_results"][0]["provider_attempts"]
    assert saved_attempts[1]["provider"] == "b3_etf"
    assert saved_attempts[1]["result"] == "SUCCESS"


def test_importing_old_quote_history_does_not_downgrade_current_price():
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="AUPO11",
        asset_class=AssetClass.BRAZILIAN_ETF,
        currency_code="BRL",
        country="BR",
        quantity=Decimal("1"),
        unit_price=Decimal("110.67"),
        effective_date=date(2026, 9, 25),
    )
    session.update_market_price(
        ticker="AUPO11",
        current_price=Decimal("112.00"),
        effective_date=date(2026, 10, 7),
        provider="brapi_public",
    )

    imported = session.import_market_price_history(
        ticker="AUPO11",
        prices=(
            MarketPriceObservation(
                symbol="AUPO11",
                price=Decimal("111.12"),
                currency_code="BRL",
                effective_date=date(2026, 9, 30),
                source="b3_etf",
            ),
        ),
    )

    assert imported == 1
    assert session.projection().positions[0].current_price.amount == Decimal("112.00")
    assert any(
        item.effective_date == date(2026, 9, 30) and item.provider == "b3_etf"
        for item in session._market_prices
    )
