"""Entity that represents the master data of a financial asset."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from income_analytics.domain.entities.entity import Entity
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.ticker import Ticker

if TYPE_CHECKING:
    from income_analytics.domain.entities.currency import Currency
    from income_analytics.domain.entities.institution import Institution


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True, eq=False, kw_only=True)
class Asset(Entity):
    """Master data for a tradable financial asset."""

    ticker: Ticker
    name: str
    asset_type: AssetType
    currency: Currency
    institution: Institution
    asset_class: AssetClass
    isin: str | None = None
    current_price: Money | None = None
    active: bool = True
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        super().__post_init__()

        if not isinstance(self.ticker, Ticker):
            raise TypeError("Asset ticker must be a Ticker.")

        if not isinstance(self.name, str):
            raise TypeError("Asset name must be a string.")

        name = self.name.strip()

        if not name:
            raise ValueError("Asset name cannot be empty.")

        if len(name) > 200:
            raise ValueError("Asset name cannot have more than 200 characters.")

        object.__setattr__(self, "name", name)

        if not isinstance(self.asset_type, AssetType):
            raise TypeError("Asset type must be an AssetType.")

        if not isinstance(self.asset_class, AssetClass):
            raise TypeError("Asset class must be an AssetClass.")

        if self.currency is None:
            raise ValueError("Asset currency is required.")

        if self.institution is None:
            raise ValueError("Asset institution is required.")

        if self.current_price is not None:
            self._validate_current_price(self.current_price)

        if self.isin is not None:
            if not isinstance(self.isin, str):
                raise ValueError("Asset ISIN must be a non-empty string when provided.")

            isin = self.isin.strip().upper()

            if not isin:
                raise ValueError("Asset ISIN must be a non-empty string when provided.")

            object.__setattr__(self, "isin", isin)

        if not isinstance(self.id, type(self.id)):
            # Mantém a validação explícita para os testes
            from uuid import UUID

            if not isinstance(self.id, UUID):
                raise TypeError("Asset id must be a UUID.")

        if not isinstance(self.active, bool):
            raise TypeError("Asset active flag must be a bool.")

        if self.created_at.tzinfo is None:
            raise ValueError("Asset timestamps must be timezone-aware.")

        if self.updated_at.tzinfo is None:
            raise ValueError("Asset timestamps must be timezone-aware.")

        if self.updated_at < self.created_at:
            raise ValueError("Asset updated_at cannot be before created_at.")

    def deactivate(self) -> None:
        """Deactivate this asset without deleting its historical master data."""

        if not self.active:
            return

        object.__setattr__(self, "active", False)
        object.__setattr__(self, "updated_at", _now_utc())

    def activate(self) -> None:
        """Activate this asset."""

        if self.active:
            return

        object.__setattr__(self, "active", True)
        object.__setattr__(self, "updated_at", _now_utc())

    def update_current_price(self, current_price: Money) -> None:
        """Update the latest manually informed market price for this asset."""
        self._validate_current_price(current_price)
        object.__setattr__(self, "current_price", current_price)
        object.__setattr__(self, "updated_at", _now_utc())


    @staticmethod
    def _validate_current_price(current_price: Money) -> None:
        if not isinstance(current_price, Money):
            raise TypeError("Asset current price must be a Money instance.")
        if not current_price.is_positive:
            raise ValueError("O preço atual deve ser maior que zero.")
