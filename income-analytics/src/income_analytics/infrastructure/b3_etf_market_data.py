"""B3 BDI price provider for ETFs covered by the fixed-income Puma table.

The BDI table is a daily, structured JSON dataset published by B3. It covers
fixed-income ETFs that do not appear in COTAHIST; it is not a real-time feed.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from threading import RLock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from income_analytics.application.market_data import MarketDataUnavailable, MarketPriceObservation


class B3EtfPriceProvider:
    """Read the latest valid daily trade from B3's fixed-income Puma table."""

    source = "b3_etf"
    table_endpoint = "DebenturesBusiness"
    base_url = "https://arquivos.b3.com.br/bdi/table"

    def __init__(self, *, timeout_seconds: float = 8) -> None:
        self._timeout_seconds = timeout_seconds
        self._cache: dict[date, dict[str, Decimal]] = {}
        self._lock = RLock()

    def latest_prices(self, symbols: tuple[str, ...]) -> dict[str, MarketPriceObservation]:
        """Fetch all matching ETFs from each recent BDI daily table once."""
        pending = {self._normalize_symbol(symbol) for symbol in symbols if symbol.strip()}
        observations: dict[str, MarketPriceObservation] = {}
        today = date.today()
        for offset in range(8):
            reference = today - timedelta(days=offset)
            prices = self._prices_for_date(reference)
            for symbol in tuple(pending):
                price = prices.get(symbol)
                if price is not None:
                    observations[symbol] = MarketPriceObservation(
                        symbol=symbol, price=price, currency_code="BRL",
                        effective_date=reference, source=self.source,
                    )
                    pending.remove(symbol)
            if not pending:
                break
        return observations

    def history(
        self, symbol: str, *, start_date: date, end_date: date
    ) -> tuple[MarketPriceObservation, ...]:
        """Return observed BDI daily prices for one symbol in a bounded range."""
        if end_date < start_date:
            raise ValueError("A data final deve ser igual ou posterior à inicial.")
        normalized = self._normalize_symbol(symbol)
        observations: list[MarketPriceObservation] = []
        for offset in range((end_date - start_date).days + 1):
            reference = start_date + timedelta(days=offset)
            if reference.weekday() >= 5:
                continue
            price = self._prices_for_date(reference).get(normalized)
            if price is not None:
                observations.append(
                    MarketPriceObservation(
                        symbol=normalized,
                        price=price,
                        currency_code="BRL",
                        effective_date=reference,
                        source=self.source,
                    )
                )
        return tuple(observations)

    def latest_price(self, symbol: str) -> MarketPriceObservation:
        normalized = self._normalize_symbol(symbol)
        today = date.today()
        for offset in range(8):
            reference = today - timedelta(days=offset)
            price = self._prices_for_date(reference).get(normalized)
            if price is not None:
                return MarketPriceObservation(
                    symbol=normalized,
                    price=price,
                    currency_code="BRL",
                    effective_date=reference,
                    source=self.source,
                )
        raise MarketDataUnavailable(
            f"B3 BDI não encontrou negócio recente para {normalized} "
            "na tabela de ETFs de renda fixa."
        )

    def price_on(self, symbol: str, effective_date: date) -> MarketPriceObservation:
        """Return the latest BDI close on or before the requested date.

        This method never substitutes today's price for a historical date.
        The BDI web table only exposes the recent publication window; older
        history requires the B3 archive/PDF backfill source.
        """
        normalized = self._normalize_symbol(symbol)
        for offset in range(8):
            reference = effective_date - timedelta(days=offset)
            price = self._prices_for_date(reference).get(normalized)
            if price is not None:
                return MarketPriceObservation(
                    symbol=normalized,
                    price=price,
                    currency_code="BRL",
                    effective_date=reference,
                    source=self.source,
                )
        raise MarketDataUnavailable(
            f"B3 BDI não encontrou cotação de {normalized} até {effective_date.isoformat()}."
        )

    def _prices_for_date(self, reference_date: date) -> dict[str, Decimal]:
        with self._lock:
            cached = self._cache.get(reference_date)
            if cached is not None:
                return cached
        payload = self._request_table(reference_date)
        table = payload.get("table")
        if not isinstance(table, dict):
            raise MarketDataUnavailable("Resposta B3 BDI sem a tabela estruturada esperada.")
        columns = table.get("columns")
        values = table.get("values")
        if not isinstance(columns, list) or not isinstance(values, list):
            raise MarketDataUnavailable("Resposta B3 BDI sem colunas ou linhas válidas.")
        names = [
            self._normalize_column(column.get("name", ""))
            if isinstance(column, dict)
            else ""
            for column in columns
        ]
        ticker_index = self._column_index(
            names,
            {
                "code",
                "ticker",
                "tickersymb",
                "tckrsymb",
                "symbol",
                "codigo",
                "codigonegociacao",
            },
        )
        price_index = self._column_index(
            names,
            {
                "final",
                "last",
                "lastprice",
                "ultimo",
                "ultimopreco",
                "precolast",
                "ult",
                "price",
                "preco",
            },
        )
        # This table's stable BDI column order starts with the ticker and has
        # the last-traded price in column 6, as defined by the official layout.
        if ticker_index is None and len(columns) >= 1:
            ticker_index = 0
        if price_index is None and len(columns) >= 7:
            price_index = 6
        if ticker_index is None or price_index is None:
            raise MarketDataUnavailable("Layout da tabela B3 BDI não reconhecido.")
        prices: dict[str, Decimal] = {}
        for row in values:
            if not isinstance(row, list) or max(ticker_index, price_index) >= len(row):
                continue
            ticker = self._normalize_symbol(str(row[ticker_index] or ""))
            price = self._parse_price(row[price_index])
            if ticker and price is not None:
                prices[ticker] = price
        with self._lock:
            self._cache[reference_date] = prices
        return prices

    def _request_table(self, reference_date: date) -> dict[str, object]:
        url = (
            f"{self.base_url}/{self.table_endpoint}/"
            f"{reference_date.isoformat()}/{reference_date.isoformat()}/1/1000"
        )
        request = Request(
            url,
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "IncomeAnalytics/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 404:
                return {
                    "table": {
                        "columns": [{"name": "Code"}, {"name": "Last"}],
                        "values": [],
                    }
                }
            raise MarketDataUnavailable(
                f"B3 BDI indisponivel para {reference_date.isoformat()}: HTTP {error.code}."
            ) from error
        except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            reason = getattr(error, "reason", error)
            raise MarketDataUnavailable(
                f"B3 BDI indisponível para {reference_date.isoformat()}: "
                f"{type(error).__name__}: {reason}."
            ) from error
        if not isinstance(payload, dict):
            raise MarketDataUnavailable("Resposta B3 BDI em formato inválido.")
        return payload

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        return re.sub(r"\s+", "", symbol).upper()

    @staticmethod
    def _normalize_column(value: str) -> str:
        ascii_name = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]", "", ascii_name.lower())

    @staticmethod
    def _column_index(names: list[str], aliases: set[str]) -> int | None:
        return next((index for index, name in enumerate(names) if name in aliases), None)

    @staticmethod
    def _parse_price(value: object) -> Decimal | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text in {"-", "—", "N/A"}:
            return None
        text = text.replace("R$", "").replace(" ", "")
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        try:
            price = Decimal(text)
        except InvalidOperation:
            return None
        return price if price > 0 else None

