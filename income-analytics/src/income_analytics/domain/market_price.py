"""Dated manually informed market data for an asset."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketPrice:
    """A market price observation used to value an asset as of a date."""

    asset: Asset
    price: Money
    effective_date: date
    id: UUID = field(default_factory=uuid4)
    registered_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not isinstance(self.asset, Asset):
            raise TypeError("Market price asset must be an Asset instance.")
        if not isinstance(self.price, Money):
            raise TypeError("Market price must be a Money instance.")
        if not self.price.is_positive:
            raise ValueError("O preço atual deve ser maior que zero.")
        if not isinstance(self.effective_date, date):
            raise TypeError("Market price effective date must be a date instance.")
        if self.registered_at.tzinfo is None:
            raise ValueError("Market price registered_at must be timezone-aware.")
