from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from income_analytics.domain.effects.financial_effect import FinancialEffect
from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class PositionEffect(FinancialEffect):
    """
    Represents a change in an asset position.
    """

    asset: Asset
    quantity_delta: Decimal
    cost_delta: Money | None = None
    sale_value: Money | None = None

    def __post_init__(self) -> None:
        super().__post_init__()

        if self.quantity_delta == Decimal("0"):
            raise ValueError("Position effect quantity delta cannot be zero.")

        if self.quantity_delta > Decimal("0"):
            if self.cost_delta is None or not self.cost_delta.is_positive:
                raise ValueError("A buy position effect requires a positive cost delta.")
            if self.sale_value is not None:
                raise ValueError("A buy position effect cannot have a sale value.")
            return

        if self.sale_value is None or not self.sale_value.is_positive:
            raise ValueError("A sell position effect requires a positive sale value.")
        if self.cost_delta is not None:
            raise ValueError("Sell cost is calculated from the current position average.")
