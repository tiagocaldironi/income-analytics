from decimal import Decimal

from income_analytics.api.routers import dashboard


def test_refresh_run_history_endpoint_returns_recent_logs(monkeypatch):
    expected = ({"id": "run-1", "status": "PARTIAL", "providers": []},)

    class Repository:
        def list_recent(self, limit):
            assert limit == 4
            return expected

    monkeypatch.setattr(dashboard, "market_price_refresh_runs", Repository())

    assert dashboard.list_market_price_refresh_runs(4) == {"runs": expected}


def test_b3_fallback_reports_both_source_errors(monkeypatch):
    class FailedProvider:
        def latest_price(self, _symbol):
            raise RuntimeError("primary unavailable")

    class FailedHistory:
        def latest_price(self, _symbol):
            raise ValueError("ticker not in B3 archive")

    monkeypatch.setattr(dashboard, "market_data", FailedProvider())
    monkeypatch.setattr(dashboard, "historical_market_data", FailedHistory())

    try:
        dashboard.B3MarketDataFallbackProvider().latest_price("AUPO11")
    except dashboard.MarketDataUnavailable as error:
        message = str(error)
    else:
        raise AssertionError("expected the B3 fallback chain to report both failures")

    assert "primary unavailable" in message
    assert "ticker not in B3 archive" in message


def test_etf_fallback_uses_b3_category_provider_and_records_attempts(monkeypatch):
    class FailedProvider:
        def latest_price(self, _symbol):
            raise RuntimeError("not covered by BRAPI")

    class CategoryProvider:
        def latest_price(self, symbol):
            from datetime import date
            from decimal import Decimal

            from income_analytics.application.market_data import MarketPriceObservation

            return MarketPriceObservation(
                symbol=symbol,
                price=Decimal("112.34"),
                currency_code="BRL",
                effective_date=date(2026, 10, 6),
                source="b3_etf",
            )

    class ShouldNotBeCalled:
        def latest_price(self, _symbol):
            raise AssertionError("COTAHIST should not be used after B3 BDI success")

    monkeypatch.setattr(dashboard, "market_data", FailedProvider())
    monkeypatch.setattr(dashboard, "historical_market_data", ShouldNotBeCalled())

    observation = dashboard.B3MarketDataFallbackProvider(CategoryProvider()).latest_price("AUPO11")

    assert observation.source == "b3_etf"
    assert observation.price == Decimal("112.34")
    assert observation.provider_attempts == (
        ("brapi", "NOT_FOUND", "RuntimeError: not covered by BRAPI"),
        ("b3_etf", "SUCCESS", None),
        ("b3_cotahist", "NOT_REQUIRED", "provider anterior respondeu"),
    )


def test_brazilian_etf_uses_category_fallback_chain():
    from income_analytics.domain.enums.asset_class import AssetClass
    from tests.unit.domain.builders import build_asset

    asset = build_asset(asset_class=AssetClass.BRAZILIAN_ETF)

    provider = dashboard.market_data_provider_for(asset)
    assert provider is dashboard.b3_etf_market_data
    assert provider._category_provider.source == "b3_etf"


def test_batched_etf_fallback_keeps_b3_source_and_marks_later_provider_unused(monkeypatch):
    from datetime import date
    from decimal import Decimal

    from income_analytics.application.market_data import (
        MarketDataUnavailable,
        MarketPriceObservation,
    )

    class FailedBrapiBatch:
        def latest_prices(self, _symbols):
            raise MarketDataUnavailable("batch unavailable")

    class BdiBatch:
        def latest_prices(self, symbols):
            return {
                symbol: MarketPriceObservation(
                    symbol=symbol,
                    price=Decimal("112.34"),
                    currency_code="BRL",
                    effective_date=date(2026, 10, 6),
                    source="b3_etf",
                )
                for symbol in symbols
                if symbol in {"AUPO11", "FIXA11"}
            }

    class HistoryMustNotRun:
        def latest_prices(self, _symbols):
            raise AssertionError("COTAHIST should remain unused after BDI succeeds")

    monkeypatch.setattr(dashboard, "market_data", FailedBrapiBatch())
    monkeypatch.setattr(dashboard, "historical_market_data", HistoryMustNotRun())
    provider = dashboard.B3MarketDataFallbackProvider(BdiBatch())

    found = provider.latest_prices(("AUPO11", "FIXA11"))

    assert set(found) == {"AUPO11", "FIXA11"}
    assert all(item.source == "b3_etf" for item in found.values())
    assert found["AUPO11"].provider_attempts == (
        ("brapi", "NOT_FOUND", "MarketDataUnavailable: batch unavailable"),
        ("b3_etf", "SUCCESS", None),
        ("b3_cotahist", "NOT_REQUIRED", "provider anterior respondeu"),
    )


def test_batched_fallback_preserves_single_quote_brapi_for_missing_batch_rows(monkeypatch):
    from datetime import date
    from decimal import Decimal

    from income_analytics.application.market_data import MarketPriceObservation

    class Brapi:
        def latest_prices(self, _symbols):
            return {}

        def latest_price(self, symbol):
            return MarketPriceObservation(
                symbol=symbol,
                price=Decimal("10"),
                currency_code="BRL",
                effective_date=date(2026, 10, 6),
                source="brapi_public",
            )

    class CategoryMustNotRun:
        def latest_prices(self, _symbols):
            raise AssertionError("the previous BRAPI single-quote fallback must be tried first")

    monkeypatch.setattr(dashboard, "market_data", Brapi())
    provider = dashboard.B3MarketDataFallbackProvider(CategoryMustNotRun())

    result = provider.latest_prices(("ALT11",))

    assert result["ALT11"].source == "brapi_public"
    assert result["ALT11"].provider_attempts[0] == ("brapi", "SUCCESS", None)
