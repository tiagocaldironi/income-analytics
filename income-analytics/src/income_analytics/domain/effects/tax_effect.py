from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from income_analytics.domain.effects.financial_effect import FinancialEffect
from income_analytics.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class TaxEffect(FinancialEffect):
    """
    Represents a taxable financial consequence.
    """

    account_id: UUID
    taxable_amount: Money
