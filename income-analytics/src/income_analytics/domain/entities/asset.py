"""Entity that represents the master data of a financial asset."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.value_objects.ticker import Ticker

if TYPE_CHECKING:
    from income_analytics.domain.entities.currency import Currency
    from income_analytics.domain.entities.institution import Institution


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Asset:
    """Master data for a tradable financial asset."""

    ticker: Ticker
    name: str
    asset_type: AssetType
    currency: Currency
    institution: Institution
    isin: str | None = None
    id: UUID = field(default_factory=uuid4)
    active: bool = True
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        if not isinstance(self.ticker, Ticker):
            raise TypeError("Asset ticker must be a Ticker.")
        if not isinstance(self.name, str):
            raise TypeError("Asset name must be a string.")

        name = self.name.strip()
        if not name:
            raise ValueError("Asset name cannot be empty.")
        if len(name) > 200:
            raise ValueError("Asset name cannot have more than 200 characters.")
        if not isinstance(self.asset_type, AssetType):
            raise TypeError("Asset type must be an AssetType.")
        if self.currency is None:
            raise ValueError("Asset currency is required.")
        if self.institution is None:
            raise ValueError("Asset institution is required.")
        if self.isin is not None:
            if not isinstance(self.isin, str) or not self.isin.strip():
                raise ValueError("Asset ISIN must be a non-empty string when provided.")
        if not isinstance(self.id, UUID):
            raise TypeError("Asset id must be a UUID.")
        if not isinstance(self.active, bool):
            raise TypeError("Asset active flag must be a bool.")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("Asset timestamps must be timezone-aware.")
        if self.updated_at < self.created_at:
            raise ValueError("Asset updated_at cannot be before created_at.")

        self.name = name
        if self.isin is not None:
            self.isin = self.isin.strip().upper()

    def deactivate(self) -> None:
        """Deactivate this asset without deleting its historical master data."""

        if self.active:
            self.active = False
            self.updated_at = _now_utc()
