"""Read model representing a projected position for a single asset."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

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
    realized_result: Money = Money.zero()
    current_price: Money | None = None
    income_received: Money = Money.zero()

    @property
    def is_empty(self) -> bool:
        return self.quantity.is_zero

    @property
    def market_value(self) -> Money:
        if self.current_price is None:
            return Money.zero()
        return Money(self.quantity.value * self.current_price.amount)

    @property
    def unrealized_result(self) -> Money:
        if self.current_price is None or self.is_empty:
            return Money.zero()
        return self.market_value - self.cost

    @property
    def unrealized_return_percentage(self) -> Decimal:
        if self.current_price is None or self.cost.is_zero:
            return Decimal("0")
        return self.unrealized_result.amount / self.cost.amount * Decimal("100")

    @property
    def total_result(self) -> Money:
        """Return the asset's realized, unrealized, and income result combined."""
        return self.realized_result + self.unrealized_result + self.income_received
