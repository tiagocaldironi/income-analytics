"""
Internal accumulator used by PortfolioProjector.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.value_objects.money import Money


@dataclass(slots=True)
class PositionAccumulator:
    """
    Mutable accumulator used while projecting a position.
    """

    asset: Asset
    quantity: Decimal = Decimal("0")
    invested: Decimal = Decimal("0")

    def add_buy(
        self,
        quantity: Decimal,
        invested: Decimal,
    ) -> None:
        self.quantity += quantity
        self.invested += invested

    @property
    def average_cost(self) -> Decimal:
        if self.quantity == Decimal("0"):
            return Decimal("0")

        return self.invested / self.quantity

    @property
    def invested_amount(self) -> Money:
        return Money(self.invested)
