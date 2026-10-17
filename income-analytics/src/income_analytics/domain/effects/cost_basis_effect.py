from __future__ import annotations

from dataclasses import dataclass

from income_analytics.domain.effects.financial_effect import FinancialEffect
from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity


@dataclass(frozen=True, slots=True, kw_only=True)
class CostBasisEffect(FinancialEffect):
    """
    Represents the impact of a financial event on an asset's cost basis.
    """

    asset: Asset
    quantity_delta: Quantity
    total_cost_delta: Money
