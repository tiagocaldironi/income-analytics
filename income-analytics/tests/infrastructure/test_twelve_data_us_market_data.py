from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from urllib.error import URLError

import pytest

from income_analytics.application.asset_discovery import AssetDiscoveryUnavailable
from income_analytics.application.market_data import MarketDataUnavailable
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.infrastructure.twelve_data_us_market_data import TwelveDataUSMarketProvider


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


@pytest.mark.parametrize(
    ("symbol", "instrument_type", "asset_class"),
    [
        ("AAPL", "Common Stock", AssetClass.INTERNATIONAL),
        ("MCD", "Common Stock", AssetClass.INTERNATIONAL),
        ("IVV", "ETF", AssetClass.INTERNATIONAL_ETF),
        ("VNQ", "ETF", AssetClass.INTERNATIONAL_ETF),
        ("O", "REIT", AssetClass.US_REIT),
        ("PLD", "REIT", AssetClass.US_REIT),
    ],
)
def test_search_classifies_us_assets_from_provider_metadata_only(
    monkeypatch, symbol, instrument_type, asset_class
) -> None:
    monkeypatch.setattr(
        "income_analytics.infrastructure.twelve_data_us_market_data.urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "data": [
                    {
                        "symbol": symbol,
                        "instrument_name": "Provider supplied name",
                        "instrument_type": instrument_type,
                        "currency": "USD",
                    }
                ]
            }
        ),
    )

    candidate = TwelveDataUSMarketProvider(api_key="test-key").search("ignored")[0]

    assert candidate.symbol == symbol
    assert candidate.suggested_asset_class is asset_class
    assert candidate.country == "US"
    assert candidate.currency_code == "USD"


def test_price_on_uses_last_daily_bar_not_after_requested_date(monkeypatch) -> None:
    monkeypatch.setattr(
        "income_analytics.infrastructure.twelve_data_us_market_data.urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "meta": {"symbol": "AAPL", "currency": "USD"},
                "values": [
                    {"datetime": "2026-08-31", "close": "241.50"},
                    {"datetime": "2026-08-28", "close": "240.10"},
                    {"datetime": "2026-08-27", "close": "238.00"},
                ],
            }
        ),
    )

    observation = TwelveDataUSMarketProvider(api_key="test-key").price_on("AAPL", date(2026, 8, 30))

    assert observation.price == Decimal("240.10")
    assert observation.effective_date == date(2026, 8, 28)
    assert observation.currency_code == "USD"
    assert observation.source == "twelve_data"


def test_search_requires_backend_api_key() -> None:
    with pytest.raises(AssetDiscoveryUnavailable, match="chave Twelve Data"):
        TwelveDataUSMarketProvider(api_key="").search("AAPL")


def test_search_translates_provider_error_to_discovery_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        "income_analytics.infrastructure.twelve_data_us_market_data.urlopen",
        lambda *_args, **_kwargs: _Response({"status": "error", "message": "Invalid symbol"}),
    )

    with pytest.raises(AssetDiscoveryUnavailable, match="Twelve Data rejeitou.*Invalid symbol"):
        TwelveDataUSMarketProvider(api_key="test-key").search("INVALID")


def test_price_on_rejects_missing_daily_values(monkeypatch) -> None:
    monkeypatch.setattr(
        "income_analytics.infrastructure.twelve_data_us_market_data.urlopen",
        lambda *_args, **_kwargs: _Response(
            {"meta": {"symbol": "AAPL", "currency": "USD"}, "values": []}
        ),
    )

    with pytest.raises(MarketDataUnavailable, match="Não há cotação US válida"):
        TwelveDataUSMarketProvider(api_key="test-key").price_on("AAPL", date(2026, 8, 30))


def test_latest_prices_falls_back_when_provider_plan_rejects_batch(monkeypatch) -> None:
    calls = []

    def response(request, **_kwargs):
        url = request.full_url
        calls.append(url)
        if "%2C" in url:
            return _Response({"status": "error", "message": "batch unavailable"})
        symbol = "MCD" if "MCD" in url else "IVV"
        return _Response(
            {"symbol": symbol, "close": "300.00", "datetime": "2026-09-22", "currency": "USD"}
        )

    monkeypatch.setattr(
        "income_analytics.infrastructure.twelve_data_us_market_data.urlopen", response
    )
    quotes = TwelveDataUSMarketProvider(api_key="test-key").latest_prices(("MCD", "IVV"))
    assert set(quotes) == {"MCD", "IVV"}
    assert all(quote.currency_code == "USD" for quote in quotes.values())
    assert len(calls) == 3


def test_latest_prices_preserves_network_failure_reason(monkeypatch) -> None:
    def fail_request(*_args, **_kwargs):
        raise URLError("offline")

    monkeypatch.setattr(
        "income_analytics.infrastructure.twelve_data_us_market_data.urlopen", fail_request
    )

    with pytest.raises(MarketDataUnavailable, match="Twelve Data:.*offline"):
        TwelveDataUSMarketProvider(api_key="test-key").latest_prices(("IVV",))


@pytest.mark.parametrize(
    ("symbol", "close", "timestamp", "expected_date"),
    [
        ("XLF", 55.52, 1792108800, "2026-10-16"),
        ("XLV", 176.71, 1792108800, "2026-10-16"),
    ],
)
def test_latest_prices_uses_yahoo_when_twelve_data_is_rate_limited(
    monkeypatch, symbol, close, timestamp, expected_date
) -> None:
    def rate_limited(*_args, **_kwargs):
        raise MarketDataUnavailable("Twelve Data respondeu HTTP 429.")

    monkeypatch.setattr(
        TwelveDataUSMarketProvider, "_latest_batch", lambda self, _symbols: rate_limited()
    )
    monkeypatch.setattr(
        "income_analytics.infrastructure.twelve_data_us_market_data.urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "chart": {
                    "result": [
                        {
                            "meta": {"symbol": symbol, "currency": "USD"},
                            "timestamp": [timestamp],
                            "indicators": {"quote": [{"close": [close]}]},
                        }
                    ],
                    "error": None,
                }
            }
        ),
    )

    quote = TwelveDataUSMarketProvider(api_key="test-key").latest_prices((symbol,))[symbol]

    assert quote.price == Decimal(str(close))
    assert quote.currency_code == "USD"
    assert quote.effective_date.isoformat() == expected_date
    assert quote.source == "yahoo_finance"
    assert quote.provider_attempts == (
        ("twelve_data", "FAILED", "Twelve Data respondeu HTTP 429."),
        ("yahoo_finance", "SUCCESS", None),
    )
