from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from income_analytics.domain.effects.financial_effect import FinancialEffect
from income_analytics.domain.entities.asset import Asset


@dataclass(frozen=True, slots=True, kw_only=True)
class PositionEffect(FinancialEffect):
    """
    Represents a change in an asset position.
    """

    asset: Asset
    quantity_delta: Decimal
