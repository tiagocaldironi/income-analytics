"""Application boundary for normalized market price providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketPriceObservation:
    symbol: str
    price: Decimal
    currency_code: str
    effective_date: date
    source: str
    price_timestamp: datetime | None = None
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    provider_attempts: tuple[tuple[str, str, str | None], ...] = ()


class MarketDataUnavailable(Exception):
    pass


class MarketDataProvider(Protocol):
    def latest_price(self, symbol: str) -> MarketPriceObservation: ...

    def price_on(self, symbol: str, effective_date: date) -> MarketPriceObservation: ...


class BatchMarketDataProvider(MarketDataProvider, Protocol):
    """Optional provider capability; callers retain the single-quote fallback."""

    def latest_prices(self, symbols: tuple[str, ...]) -> dict[str, MarketPriceObservation]: ...


class MarketEvidenceStatus(StrEnum):
    VALID = "VALID"
    INSUFFICIENT_MARKET_DATA = "INSUFFICIENT_MARKET_DATA"


@dataclass(frozen=True, slots=True, kw_only=True)
class CotahistPriceEvidence:
    """One B3 close together with enough data to locate its raw record."""

    ticker: str
    requested_reference_date: date
    effective_date: date | None
    price: Decimal | None
    currency: str | None
    source: str
    source_file: str | None
    record_reference: str | None
    status: MarketEvidenceStatus
    reason: str | None = None
    isin: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.status is MarketEvidenceStatus.VALID


class CotahistEvidenceProvider(Protocol):
    def price_evidence_on(
        self, symbol: str, requested_reference_date: date
    ) -> CotahistPriceEvidence: ...
