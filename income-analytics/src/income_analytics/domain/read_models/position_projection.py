"""Read model representing a projected position for a single asset."""

from __future__ import annotations

from dataclasses import dataclass

from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity


@dataclass(frozen=True, slots=True, kw_only=True)
class PositionProjection:
    """Represents the projected position of a single asset."""

    asset: Asset
    quantity: Quantity
    cost: Money
    average_price: Money

    @property
    def is_empty(self) -> bool:
        return self.quantity.is_zero
