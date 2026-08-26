from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from income_analytics.domain.effects.financial_effect import FinancialEffect
from income_analytics.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class CashEffect(FinancialEffect):
    """
    Represents a cash movement.
    """

    account_id: UUID
    amount: Money
