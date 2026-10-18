"""CoinGecko adapters normalized to the application's asset and price contracts."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

from income_analytics.application.asset_discovery import AssetCandidate, AssetDiscoveryUnavailable
from income_analytics.application.market_data import MarketDataUnavailable, MarketPriceObservation
from income_analytics.domain.enums.asset_class import AssetClass


class CoinGeckoCryptoProvider:
    base_url = "https://api.coingecko.com/api/v3"
    source = "coingecko"

    def __init__(self, *, timeout_seconds: float = 8) -> None:
        self._timeout_seconds = timeout_seconds
        self._symbol_ids: dict[str, str] = {}

    def search(self, query: str, *, limit: int = 8) -> tuple[AssetCandidate, ...]:
        payload = self._get(f"/search?query={quote(query.strip())}", AssetDiscoveryUnavailable)
        coins = payload.get("coins", [])
        return tuple(
            AssetCandidate(
                external_id=str(coin["id"]),
                symbol=str(coin["symbol"]).upper(),
                name=str(coin["name"]),
                instrument_type="Cripto",
                suggested_asset_class=AssetClass.CRYPTO,
                country=None,
                currency_code="USD",
                sector=None,
                source=self.source,
            )
            for coin in coins[:limit]
            if isinstance(coin, dict) and coin.get("id") and coin.get("symbol") and coin.get("name")
        )

    def latest_price(self, symbol: str) -> MarketPriceObservation:
        return self.latest_prices((symbol,))[symbol.strip().upper()]

    def latest_prices(self, symbols: tuple[str, ...]) -> dict[str, MarketPriceObservation]:
        normalized = tuple(sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()}))
        if not normalized:
            return {}
        identifiers = {}
        for symbol in normalized:
            try:
                identifiers[symbol] = self._coin_id(symbol)
            except MarketDataUnavailable:
                continue
        if not identifiers:
            raise MarketDataUnavailable("Nenhum criptoativo elegível para cotação automática.")
        payload = self._get(
            "/simple/price?ids="
            + quote(",".join(identifiers.values()))
            + "&vs_currencies=usd&include_last_updated_at=true",
            MarketDataUnavailable,
        )
        retrieved_at = datetime.now(UTC)
        observations: dict[str, MarketPriceObservation] = {}
        for symbol, coin_id in identifiers.items():
            item = payload.get(coin_id, {})
            timestamp = item.get("last_updated_at") if isinstance(item, dict) else None
            price_timestamp = datetime.fromtimestamp(int(timestamp), UTC) if timestamp else None
            observations[symbol] = self._price_from(
                item.get("usd") if isinstance(item, dict) else None,
                symbol,
                date.today(),
                price_timestamp=price_timestamp,
                retrieved_at=retrieved_at,
            )
        return observations

    def price_on(self, symbol: str, effective_date: date) -> MarketPriceObservation:
        coin_id = self._coin_id(symbol)
        payload = self._get(
            f"/coins/{quote(coin_id)}/history?date={effective_date.strftime('%d-%m-%Y')}&localization=false",
            MarketDataUnavailable,
        )
        price = payload.get("market_data", {}).get("current_price", {}).get("usd")
        return self._price_from(price, symbol, effective_date)

    def history(
        self, symbol: str, start_date: date, end_date: date
    ) -> tuple[MarketPriceObservation, ...]:
        coin_id = self._coin_id(symbol)
        start = int(datetime.combine(start_date, datetime.min.time(), UTC).timestamp())
        end = int(datetime.combine(end_date, datetime.max.time(), UTC).timestamp())
        payload = self._get(
            f"/coins/{quote(coin_id)}/market_chart/range?vs_currency=usd&from={start}&to={end}",
            MarketDataUnavailable,
        )
        values = payload.get("prices", ())
        if not isinstance(values, list):
            raise MarketDataUnavailable("Série histórica de cripto indisponível.")
        observations = []
        for item in values:
            if not isinstance(item, list) or len(item) < 2:
                continue
            try:
                observed_at = datetime.fromtimestamp(float(item[0]) / 1000, UTC)
                price = Decimal(str(item[1]))
            except TypeError, ValueError, OverflowError:
                continue
            effective_date = observed_at.date()
            if start_date <= effective_date <= end_date and price > 0:
                observations.append(
                    self._price_from(price, symbol, effective_date, price_timestamp=observed_at)
                )
        return tuple(sorted(observations, key=lambda item: item.effective_date))

    def _coin_id(self, symbol: str) -> str:
        cached = self._symbol_ids.get(symbol.strip().upper())
        if cached:
            return cached
        candidates = self.search(symbol, limit=10)
        normalized = symbol.strip().upper()
        exact = next((item for item in candidates if item.symbol == normalized), None)
        if exact is None or exact.external_id is None:
            raise MarketDataUnavailable("Criptoativo não encontrado para cotação automática.")
        self._symbol_ids[normalized] = exact.external_id
        return exact.external_id

    def _get(self, path: str, exception: type[Exception]) -> dict[str, Any]:
        try:
            with urlopen(f"{self.base_url}{path}", timeout=self._timeout_seconds) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Resposta de cripto inválida.")
            return payload
        except (OSError, URLError, ValueError) as error:
            raise exception("Dados de cripto indisponíveis no momento.") from error

    def _price_from(
        self,
        value: object,
        symbol: str,
        effective_date: date,
        *,
        price_timestamp: datetime | None = None,
        retrieved_at: datetime | None = None,
    ) -> MarketPriceObservation:
        try:
            price = Decimal(str(value))
        except Exception as error:
            raise MarketDataUnavailable("Não há cotação de cripto para esta data.") from error
        if price <= 0:
            raise MarketDataUnavailable("Não há cotação de cripto para esta data.")
        return MarketPriceObservation(
            symbol=symbol.upper(),
            price=price,
            currency_code="USD",
            effective_date=effective_date,
            source=self.source,
            price_timestamp=price_timestamp,
            retrieved_at=retrieved_at or datetime.now(UTC),
        )
