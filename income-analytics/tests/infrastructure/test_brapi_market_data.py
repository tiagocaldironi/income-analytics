from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from income_analytics.infrastructure.brapi_market_data import BrapiMarketDataProvider


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def test_price_on_uses_the_observed_market_date(monkeypatch) -> None:
    payload = {
        "results": [
            {
                "data": {
                    "historicalDataPrice": [
                        {"date": "2026-08-28", "close": 43.55},
                    ]
                }
            }
        ]
    }
    monkeypatch.setattr(
        "income_analytics.infrastructure.brapi_market_data.urlopen",
        lambda *_args, **_kwargs: _Response(payload),
    )

    observation = BrapiMarketDataProvider().price_on("PETR4", date(2026, 8, 30))

    assert observation.effective_date == date(2026, 8, 28)
    assert observation.price == Decimal("43.55")


def test_price_on_normalizes_a_weekend_quote_to_the_previous_business_day(monkeypatch) -> None:
    payload = {
        "results": [
            {
                "data": {
                    "historicalDataPrice": [
                        {"date": 1788058800, "close": 43.55},
                    ]
                }
            }
        ]
    }
    monkeypatch.setattr(
        "income_analytics.infrastructure.brapi_market_data.urlopen",
        lambda *_args, **_kwargs: _Response(payload),
    )

    observation = BrapiMarketDataProvider().price_on("PETR4", date(2026, 8, 30))

    assert observation.effective_date == date(2026, 8, 28)
