from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from income_analytics.infrastructure.coingecko_crypto_data import CoinGeckoCryptoProvider


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def test_price_on_normalizes_usd_quote_as_decimal(monkeypatch) -> None:
    provider = CoinGeckoCryptoProvider()
    monkeypatch.setattr(provider, "_coin_id", lambda _symbol: "solana")
    monkeypatch.setattr(
        "income_analytics.infrastructure.coingecko_crypto_data.urlopen",
        lambda *_args, **_kwargs: _Response(
            {"market_data": {"current_price": {"usd": 82.98}}}
        ),
    )

    observation = provider.price_on("SOL", date(2026, 2, 11))

    assert observation.symbol == "SOL"
    assert observation.price == Decimal("82.98")
    assert observation.currency_code == "USD"
    assert observation.effective_date == date(2026, 2, 11)


def test_latest_prices_uses_one_price_request_for_multiple_resolved_symbols(monkeypatch) -> None:
    provider = CoinGeckoCryptoProvider()
    identities = {"BTC": "bitcoin", "ETH": "ethereum"}
    monkeypatch.setattr(provider, "_coin_id", lambda symbol: identities[symbol])
    requests = []

    def response(url, **_kwargs):
        requests.append(url)
        return _Response(
            {
                "bitcoin": {"usd": 100000, "last_updated_at": 1_790_000_000},
                "ethereum": {"usd": 3000, "last_updated_at": 1_790_000_000},
            }
        )

    monkeypatch.setattr("income_analytics.infrastructure.coingecko_crypto_data.urlopen", response)
    quotes = provider.latest_prices(("BTC", "ETH"))
    assert set(quotes) == {"BTC", "ETH"}
    assert all(quote.currency_code == "USD" and quote.price_timestamp for quote in quotes.values())
    assert len(requests) == 1


def test_history_returns_source_dated_daily_prices(monkeypatch) -> None:
    provider = CoinGeckoCryptoProvider()
    monkeypatch.setattr(provider, "_coin_id", lambda _symbol: "bitcoin")
    monkeypatch.setattr(
        "income_analytics.infrastructure.coingecko_crypto_data.urlopen",
        lambda *_args, **_kwargs: _Response(
            {"prices": [[1767225600000, 87500.25], [1767312000000, 88000.5]]}
        ),
    )

    observations = provider.history("BTC", date(2026, 1, 1), date(2026, 1, 2))

    assert [item.effective_date for item in observations] == [date(2026, 1, 1), date(2026, 1, 2)]
    assert [item.price for item in observations] == [Decimal("87500.25"), Decimal("88000.5")]
    assert all(item.source == "coingecko" and item.currency_code == "USD" for item in observations)
