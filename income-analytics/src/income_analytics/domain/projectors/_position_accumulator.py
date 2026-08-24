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
    realized_result: Money = Money.zero()

    def apply(self, effect: PositionEffect) -> None:
        if effect.asset != self.asset:
            raise ValueError("Position effect belongs to another asset.")

        if effect.quantity_delta > Decimal("0"):
            self._apply_buy(effect)
            return

        self._apply_sell(effect)

    def _apply_buy(self, effect: PositionEffect) -> None:
        if effect.cost_delta is None:
            raise ValueError("A buy position effect requires a cost delta.")

        self.quantity += effect.quantity_delta
        self.cost = self.cost + effect.cost_delta

    def _apply_sell(self, effect: PositionEffect) -> None:
        quantity_sold = -effect.quantity_delta
        if quantity_sold > self.quantity:
            raise ValueError("Cannot sell more than the current position quantity.")
        if effect.sale_value is None:
            raise ValueError("A sell position effect requires a sale value.")

        cost_of_sale = Money(quantity_sold * self.average_price.amount)
        self.quantity -= quantity_sold
        self.cost = self.cost - cost_of_sale
        self.realized_result = self.realized_result + (effect.sale_value - cost_of_sale)

        if self.quantity == Decimal("0"):
            self.cost = Money.zero()

    @property
    def average_price(self) -> Money:
        if self.quantity == Decimal("0"):
            return Money.zero()

        return Money(self.cost.amount / self.quantity)
