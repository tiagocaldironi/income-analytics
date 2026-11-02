"""Brapi adapter for normalized latest price observations."""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from income_analytics.application.market_data import MarketDataUnavailable, MarketPriceObservation
from income_analytics.infrastructure.operational_provider import fetch_json


class BrapiMarketDataProvider:
    base_url = "https://brapi.dev/api/v2/stocks/quote"
    public_ticker_url = "https://brapi.dev/api/v2/tickers"

    def __init__(self, *, token: str | None = None, timeout_seconds: float = 5) -> None:
        self._token = token or os.getenv("BRAPI_TOKEN")
        self._timeout_seconds = timeout_seconds

    def latest_prices(self, symbols: tuple[str, ...]) -> dict[str, MarketPriceObservation]:
        """Fetch multiple BRAPI quotes in one request for the daily refresh."""
        if not symbols:
            return {}
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            request = Request(
                f"{self.base_url}?{urlencode({'symbols': ','.join(symbols)})}",
                headers=headers,
            )
            def transport(_timeout: float) -> tuple[int, bytes]:
                with urlopen(request, timeout=self._timeout_seconds) as response:
                    return 200, response.read()

            payload = fetch_json(transport, attempts=1)
        except (IndexError, KeyError, OSError, TypeError, URLError, ValueError) as error:
            raise MarketDataUnavailable("BRAPI batch quotes unavailable.") from error
        observations: dict[str, MarketPriceObservation] = {}
        for item in payload.get("results", []):
            data = item.get("data", item)
            ticker = str(data.get("symbol") or item.get("symbol") or "").strip().upper()
            if ticker not in symbols:
                continue
            raw_price = data.get("regularMarketPrice") or data.get("lastPrice")
            try:
                price = Decimal(str(raw_price))
            except (InvalidOperation, TypeError):
                continue
            if price <= 0:
                continue
            timestamp = data.get("regularMarketTime")
            observed_at = (
                datetime.fromisoformat(timestamp.replace("Z", "+00:00")) if timestamp else None
            )
            observations[ticker] = MarketPriceObservation(
                symbol=ticker,
                price=price,
                currency_code=str(data.get("currency", "BRL")),
                effective_date=observed_at.date() if observed_at else datetime.now(UTC).date(),
                source="brapi",
                price_timestamp=observed_at,
            )
        return observations

    def latest_price(self, symbol: str) -> MarketPriceObservation:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            request = Request(f"{self.base_url}?{urlencode({'symbols': symbol})}", headers=headers)
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            item = payload["results"][0]
            data = item.get("data", item)
            price = Decimal(str(data.get("regularMarketPrice") or data.get("lastPrice")))
            timestamp = data.get("regularMarketTime")
            effective_date = (
                datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date()
                if timestamp
                else datetime.now(UTC).date()
            )
            return MarketPriceObservation(
                symbol=symbol.upper(),
                price=price,
                currency_code=str(data.get("currency", "BRL")),
                effective_date=effective_date,
                source="brapi",
            )
        except (IndexError, KeyError, OSError, TypeError, URLError, ValueError):
            # Some BRAPI plans require a token for the quote endpoint, while
            # public ticker search still provides the delayed last price.
            try:
                return self._public_latest_price(symbol)
            except (
                IndexError,
                KeyError,
                OSError,
                TypeError,
                URLError,
                ValueError,
            ) as fallback_error:
                raise MarketDataUnavailable(
                    "Cotação automática indisponível para este ativo."
                ) from fallback_error

    def _public_latest_price(self, symbol: str) -> MarketPriceObservation:
        normalized_symbol = symbol.strip().upper()
        request = Request(
            f"{self.public_ticker_url}?{urlencode({'search': normalized_symbol, 'limit': 10})}",
            headers={"Accept": "application/json"},
        )
        with urlopen(request, timeout=self._timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        item = next(
            candidate
            for candidate in payload.get("results", [])
            if str(candidate.get("symbol", "")).strip().upper() == normalized_symbol
        )
        quote = item.get("quote") or {}
        price = Decimal(str(quote.get("lastPrice")))
        if price <= 0:
            raise ValueError("Cotação pública inválida.")
        return MarketPriceObservation(
            symbol=normalized_symbol,
            price=price,
            currency_code=str(item.get("currency", "BRL")),
            effective_date=datetime.now(UTC).date(),
            source="brapi_public",
        )

    def price_on(self, symbol: str, effective_date: date) -> MarketPriceObservation:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        params = urlencode(
            {"symbols": symbol, "startDate": effective_date, "endDate": effective_date}
        )
        try:
            request = Request(
                f"https://brapi.dev/api/v2/stocks/historical?{params}", headers=headers
            )
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            data = payload["results"][0]["data"]["historicalDataPrice"]
            point = data[-1]
            point_date = point.get("date") or point.get("timestamp")
            observed_date = (
                datetime.fromtimestamp(int(point_date), UTC).date()
                if isinstance(point_date, (int, float))
                else date.fromisoformat(str(point_date)[:10])
                if point_date
                else effective_date
            )
            # BRAPI can repeat Friday's close using the requested weekend date.
            # A stock quote must retain the last valid B3 business date.
            if observed_date.weekday() == 5:
                observed_date -= timedelta(days=1)
            elif observed_date.weekday() == 6:
                observed_date -= timedelta(days=2)
            return MarketPriceObservation(
                symbol=symbol.upper(),
                price=Decimal(str(point["close"])),
                currency_code="BRL",
                effective_date=observed_date,
                source="brapi",
            )
        except (IndexError, KeyError, OSError, TypeError, URLError, ValueError) as error:
            raise MarketDataUnavailable("Cotação histórica indisponível na brapi.") from error

    def _yahoo_price_on(self, symbol: str, effective_date: date) -> MarketPriceObservation:
        start = datetime.combine(effective_date - timedelta(days=7), datetime.min.time(), UTC)
        end = datetime.combine(effective_date + timedelta(days=1), datetime.min.time(), UTC)
        params = urlencode(
            {"period1": int(start.timestamp()), "period2": int(end.timestamp()), "interval": "1d"}
        )
        try:
            with urlopen(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.SA?{params}",
                timeout=self._timeout_seconds,
            ) as response:
                result = json.loads(response.read().decode("utf-8"))["chart"]["result"][0]
            closes = result["indicators"]["quote"][0]["close"]
            timestamps = result["timestamp"]
            pairs = [
                (datetime.fromtimestamp(stamp, UTC).date(), close)
                for stamp, close in zip(timestamps, closes, strict=True)
                if close is not None
            ]
            observed_date, close = max(
                (pair for pair in pairs if pair[0] <= effective_date), key=lambda pair: pair[0]
            )
            return MarketPriceObservation(
                symbol=symbol.upper(),
                price=Decimal(str(close)),
                currency_code="BRL",
                effective_date=observed_date,
                source="yahoo_finance",
            )
        except (IndexError, KeyError, OSError, TypeError, URLError, ValueError) as error:
            raise MarketDataUnavailable(
                "Não há cotação automática para a data escolhida."
            ) from error
