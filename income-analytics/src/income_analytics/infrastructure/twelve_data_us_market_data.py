"""Twelve Data adapter for US listed instruments.

The provider key is read exclusively from the backend environment. This adapter
uses only provider metadata for asset classification; it never infers a class
from the ticker text.
"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from income_analytics.application.asset_discovery import AssetCandidate, AssetDiscoveryUnavailable
from income_analytics.application.market_data import MarketDataUnavailable, MarketPriceObservation
from income_analytics.domain.enums.asset_class import AssetClass


class TwelveDataUSMarketProvider:
    base_url = "https://api.twelvedata.com"
    source = "twelve_data"
    max_batch_symbols = 8

    def __init__(self, *, api_key: str | None = None, timeout_seconds: float = 8) -> None:
        self._api_key = os.getenv("TWELVE_DATA_API_KEY") if api_key is None else api_key
        self._timeout_seconds = timeout_seconds

    def search(self, query: str, *, limit: int = 8) -> tuple[AssetCandidate, ...]:
        payload = self._get(
            "/symbol_search",
            {"symbol": query.strip()},
            AssetDiscoveryUnavailable,
        )
        candidates = (
            self._candidate(item) for item in payload.get("data", ()) if isinstance(item, dict)
        )
        return tuple(candidate for candidate in candidates if candidate is not None)[:limit]

    def latest_price(self, symbol: str) -> MarketPriceObservation:
        return self.latest_prices((symbol,))[symbol.strip().upper()]

    def latest_prices(self, symbols: tuple[str, ...]) -> dict[str, MarketPriceObservation]:
        normalized = tuple(sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()}))
        if not normalized:
            return {}
        observations = {}
        failures: list[str] = []
        for start in range(0, len(normalized), self.max_batch_symbols):
            batch = normalized[start : start + self.max_batch_symbols]
            try:
                observations.update(self._latest_batch(batch))
            except MarketDataUnavailable as error:
                failures.append(str(error))
        primary_failure = "; ".join(failures) or "Twelve Data omitiu o símbolo no lote."
        for symbol in normalized:
            if symbol in observations:
                continue
            try:
                quote = self._yahoo_latest_price(symbol)
                observations[symbol] = replace(
                    quote,
                    provider_attempts=(
                        (self.source, "FAILED", primary_failure[:300]),
                        ("yahoo_finance", "SUCCESS", None),
                    ),
                )
            except MarketDataUnavailable as error:
                failures.append(f"Yahoo Finance {symbol}: {error}")
        if observations:
            return observations
        detail = "; ".join(failures) or "nenhuma cotação retornada"
        raise MarketDataUnavailable(f"Dados de mercado US indisponíveis: {detail}")

    def _yahoo_latest_price(self, symbol: str) -> MarketPriceObservation:
        """Use Yahoo's daily chart as a resilient fallback for current US quotes."""
        now = datetime.now(UTC)
        start = now - timedelta(days=14)
        end = now + timedelta(days=1)
        params = urlencode(
            {
                "period1": str(int(start.timestamp())),
                "period2": str(int(end.timestamp())),
                "interval": "1d",
            }
        )
        request = Request(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{params}",
            headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            chart = payload.get("chart", {})
            result = next(iter(chart.get("result") or ()), None)
            if not isinstance(result, dict):
                error = chart.get("error")
                message = error.get("description") if isinstance(error, dict) else None
                raise MarketDataUnavailable(str(message or "nenhuma série diária retornada"))
            meta = result.get("meta", {})
            actual_symbol = str(meta.get("symbol") or "").upper()
            currency = str(meta.get("currency") or "").upper()
            if actual_symbol != symbol or currency != "USD":
                raise MarketDataUnavailable(
                    f"identidade/moeda inesperada ({actual_symbol or 'sem símbolo'}, "
                    f"{currency or 'sem moeda'})."
                )
            timestamps = result.get("timestamp", ())
            quotes = result.get("indicators", {}).get("quote", ())
            closes = quotes[0].get("close", ()) if quotes and isinstance(quotes[0], dict) else ()
            points = [
                (datetime.fromtimestamp(timestamp, UTC).date(), Decimal(str(close)))
                for timestamp, close in zip(timestamps, closes)
                if close is not None and Decimal(str(close)) > 0
            ]
            if not points:
                raise MarketDataUnavailable("nenhum fechamento diário válido retornado.")
            observed, price = max(points, key=lambda point: point[0])
            return MarketPriceObservation(
                symbol=actual_symbol,
                price=price,
                currency_code=currency,
                effective_date=observed,
                source="yahoo_finance",
                retrieved_at=now,
            )
        except MarketDataUnavailable:
            raise
        except Exception as error:
            raise MarketDataUnavailable(f"falha ao consultar série diária: {error}") from error

    def _latest_batch(self, symbols: tuple[str, ...]) -> dict[str, MarketPriceObservation]:
        retrieved_at = datetime.now(UTC)
        if len(symbols) == 1:
            payload = self._get("/quote", {"symbol": symbols[0]}, MarketDataUnavailable)
            return {symbols[0]: self._observation_from_quote(payload, symbols[0], retrieved_at)}
        try:
            payload = self._get("/quote", {"symbol": ",".join(symbols)}, MarketDataUnavailable)
            observations = {
                symbol: self._observation_from_quote(item, symbol, retrieved_at)
                for symbol in symbols
                if isinstance((item := payload.get(symbol) or payload.get(symbol.upper())), dict)
            }
            if observations:
                return observations
        except MarketDataUnavailable:
            pass
        # The endpoint response is plan-dependent: some plans reject a comma
        # separated request. Retain one provider group and degrade gracefully.
        observations = {}
        failures = []
        for symbol in symbols:
            try:
                payload = self._get("/quote", {"symbol": symbol}, MarketDataUnavailable)
                observations[symbol] = self._observation_from_quote(payload, symbol, retrieved_at)
            except MarketDataUnavailable as error:
                failures.append(f"{symbol}: {error}")
        if not observations and failures:
            raise MarketDataUnavailable("; ".join(failures))
        return observations

    def price_on(self, symbol: str, effective_date: date) -> MarketPriceObservation:
        payload = self._get(
            "/time_series",
            {
                "symbol": symbol.strip().upper(),
                "interval": "1day",
                "start_date": (effective_date - timedelta(days=14)).isoformat(),
                "end_date": effective_date.isoformat(),
                "outputsize": "30",
            },
            MarketDataUnavailable,
        )
        values = payload.get("values", ())
        if not isinstance(values, list):
            raise MarketDataUnavailable("Cotação histórica US indisponível.")
        points: list[tuple[date, Decimal]] = []
        for value in values:
            if not isinstance(value, dict):
                continue
            try:
                observed = date.fromisoformat(str(value["datetime"])[:10])
                close = Decimal(str(value["close"]))
            except (KeyError, ValueError):
                continue
            if observed <= effective_date and close > 0:
                points.append((observed, close))
        if not points:
            raise MarketDataUnavailable("Não há cotação US válida para a data escolhida.")
        observed, price = max(points, key=lambda point: point[0])
        meta = payload.get("meta", {})
        return MarketPriceObservation(
            symbol=str(meta.get("symbol") or symbol).upper(),
            price=price,
            currency_code=str(meta.get("currency") or "USD").upper(),
            effective_date=observed,
            source=self.source,
        )

    def history(
        self, symbol: str, start_date: date, end_date: date
    ) -> tuple[MarketPriceObservation, ...]:
        payload = self._get(
            "/time_series",
            {
                "symbol": symbol.strip().upper(),
                "interval": "1day",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            MarketDataUnavailable,
        )
        values = payload.get("values", ())
        if not isinstance(values, list):
            raise MarketDataUnavailable("Série histórica US indisponível.")
        meta = payload.get("meta", {})
        observations = []
        for item in values:
            if not isinstance(item, dict):
                continue
            try:
                observed = date.fromisoformat(str(item["datetime"])[:10])
                close = Decimal(str(item["close"]))
            except (KeyError, ValueError):
                continue
            if start_date <= observed <= end_date and close > 0:
                observations.append(
                    MarketPriceObservation(
                        symbol=str(meta.get("symbol") or symbol).upper(),
                        price=close,
                        currency_code=str(meta.get("currency") or "USD").upper(),
                        effective_date=observed,
                        source=self.source,
                    )
                )
        return tuple(sorted(observations, key=lambda item: item.effective_date))

    @classmethod
    def _candidate(cls, item: dict[str, object]) -> AssetCandidate | None:
        symbol = str(item.get("symbol") or "").strip().upper()
        name = str(item.get("instrument_name") or item.get("name") or "").strip()
        instrument_type = str(item.get("instrument_type") or item.get("type") or "").strip()
        if not symbol or not name:
            return None
        asset_class = cls._asset_class(instrument_type)
        if asset_class is None:
            return None
        return AssetCandidate(
            external_id=symbol,
            symbol=symbol,
            name=name,
            instrument_type=instrument_type,
            suggested_asset_class=asset_class,
            country="US",
            currency_code=str(item.get("currency") or "USD").upper(),
            sector=None,
            source=cls.source,
        )

    @staticmethod
    def _asset_class(instrument_type: str) -> AssetClass | None:
        normalized = instrument_type.casefold().strip()
        if normalized == "reit":
            return AssetClass.US_REIT
        if normalized == "etf":
            return AssetClass.INTERNATIONAL_ETF
        if normalized == "common stock":
            return AssetClass.INTERNATIONAL
        return None

    def _observation_from_quote(
        self, payload: dict[str, Any], requested_symbol: str, retrieved_at: datetime | None = None
    ) -> MarketPriceObservation:
        try:
            price = Decimal(str(payload.get("close") or payload.get("price")))
            observed = date.fromisoformat(str(payload["datetime"])[:10])
        except (KeyError, ValueError) as error:
            raise MarketDataUnavailable("Cotação US indisponível.") from error
        if price <= 0:
            raise MarketDataUnavailable("Cotação US indisponível.")
        return MarketPriceObservation(
            symbol=str(payload.get("symbol") or requested_symbol).upper(),
            price=price,
            currency_code=str(payload.get("currency") or "USD").upper(),
            effective_date=observed,
            source=self.source,
            retrieved_at=retrieved_at or datetime.now(UTC),
        )

    def _get(
        self,
        path: str,
        params: dict[str, str],
        exception: type[Exception],
    ) -> dict[str, Any]:
        if not self._api_key:
            raise exception("Integração US indisponível: chave Twelve Data não configurada.")
        query = urlencode({**params, "apikey": self._api_key})
        try:
            request = Request(
                f"{self.base_url}{path}?{query}", headers={"Accept": "application/json"}
            )
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise exception("Twelve Data retornou uma resposta em formato inválido.")
            if payload.get("status") == "error":
                code = str(payload.get("code") or "sem código")
                message = str(payload.get("message") or "erro sem descrição")[:200]
                raise exception(f"Twelve Data rejeitou a consulta ({code}): {message}")
            return payload
        except HTTPError as error:
            raise exception(f"Twelve Data respondeu HTTP {error.code}.") from error
        except URLError as error:
            raise exception(f"Falha de rede ao consultar Twelve Data: {error.reason}.") from error
        except (OSError, ValueError) as error:
            raise exception(f"Falha ao processar resposta da Twelve Data: {error}") from error
