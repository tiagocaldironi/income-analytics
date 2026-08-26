"""
Represents an immutable financial event.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.entities.entity import Entity
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity


def now_utc() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(UTC)


@dataclass(slots=True, eq=False, kw_only=True)
class FinancialEvent(Entity):
    """
    Represents an immutable financial fact.

    A FinancialEvent records something that happened in the financial
    history of an investment account.

    Financial Events never calculate business rules.
    They are interpreted later by Business Engines.
    """

    account_id: UUID
    event_type: FinancialEventType
    occurred_at: datetime

    effective_date: date = date(2026, 1, 1)

    asset: Asset | None = None

    quantity: Quantity | None = None

    unit_price: Money | None = None

    amount: Money | None = None

    description: str | None = None

    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )

    registered_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        super().__post_init__()

        if self.occurred_at.tzinfo is None:
            raise ValueError(
                "occurred_at must be timezone-aware."
            )

        if self.registered_at.tzinfo is None:
            raise ValueError(
                "registered_at must be timezone-aware."
            )

        if self.registered_at < self.occurred_at:
            raise ValueError(
                "registered_at cannot be earlier than occurred_at."
            )

        if self.asset is not None and not isinstance(self.asset, Asset):
            raise TypeError(
                "asset must be an Asset instance when provided."
            )

        if not isinstance(self.effective_date, date):
            raise TypeError("effective_date must be a date instance.")

        if self.event_type in (FinancialEventType.BUY, FinancialEventType.SELL):
            self._validate_trade()

        if self.event_type is FinancialEventType.DIVIDEND:
            self._validate_dividend()

        if self.event_type in (
            FinancialEventType.DEPOSIT,
            FinancialEventType.WITHDRAWAL,
        ):
            self._validate_external_flow()

        if not isinstance(self.metadata, Mapping):
            raise TypeError(
                "metadata must implement Mapping."
            )

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )

    def _validate_trade(self) -> None:
        event_name = self.event_type.value
        if self.asset is None:
            raise ValueError(f"{event_name} event requires an asset.")

        if self.quantity is None or not self.quantity.is_positive:
            raise ValueError(f"{event_name} event requires a positive quantity.")

        if self.unit_price is None or not self.unit_price.is_positive:
            raise ValueError(f"{event_name} event requires a positive unit price.")

    def _validate_dividend(self) -> None:
        if self.asset is None:
            raise ValueError("DIVIDEND event requires an asset.")
        if self.amount is None or not self.amount.is_positive:
            raise ValueError("O valor do provento deve ser maior que zero.")

    def _validate_external_flow(self) -> None:
        if self.asset is not None:
            raise ValueError(f"{self.event_type.value} event must not have an asset.")
        if self.amount is None or not self.amount.is_positive:
            label = "aporte" if self.event_type is FinancialEventType.DEPOSIT else "retirada"
            raise ValueError(f"O valor da {label} deve ser maior que zero.")

    @property
    def total_amount(self) -> Money:
        """Return the financial total derived from quantity and unit price."""
        if self.event_type in (
            FinancialEventType.DIVIDEND,
            FinancialEventType.DEPOSIT,
            FinancialEventType.WITHDRAWAL,
        ):
            if self.amount is None:
                raise ValueError("Event does not have an amount.")
            return self.amount

        if self.quantity is None or self.unit_price is None:
            raise ValueError("Event does not have enough data to calculate its total.")

        return Money(self.quantity.value * self.unit_price.amount)

