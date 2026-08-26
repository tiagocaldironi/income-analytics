from __future__ import annotations

from dataclasses import dataclass

from income_analytics.domain.effects.financial_effect import FinancialEffect
from income_analytics.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class FxEffect(FinancialEffect):
    """
    Represents a foreign exchange gain or loss.
    """

    original_amount: Money
    converted_amount: Money
