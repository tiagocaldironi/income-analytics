"""
Internal accumulator used by PortfolioProjector.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from income_analytics.domain.effects.position_effect import PositionEffect
from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.value_objects.money import Money


@dataclass(slots=True)
class PositionAccumulator:
    """
    Mutable accumulator used while projecting a position.
    """

    asset: Asset
    quantity: Decimal = Decimal("0")
    cost: Money = Money.zero()

    def apply(self, effect: PositionEffect) -> None:
        if effect.asset != self.asset:
            raise ValueError("Position effect belongs to another asset.")

        self.quantity += effect.quantity_delta
        self.cost = self.cost + effect.cost_delta

    @property
    def average_price(self) -> Money:
        if self.quantity == Decimal("0"):
            return Money.zero()

        return Money(self.cost.amount / self.quantity)
