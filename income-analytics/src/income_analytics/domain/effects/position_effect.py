from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from income_analytics.domain.effects.financial_effect import FinancialEffect


@dataclass(frozen=True, slots=True, kw_only=True)
class PositionEffect(FinancialEffect):
    """
    Represents a change in an asset position.
    """

    asset_id: UUID
    quantity_delta: Decimal