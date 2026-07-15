"""
Represents an immutable financial event.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

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

    asset_id: UUID | None = None

    quantity: Quantity | None = None

    unit_price: Money | None = None

    total_amount: Money | None = None

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

        if not isinstance(self.metadata, Mapping):
            raise TypeError(
                "metadata must implement Mapping."
            )

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )

  