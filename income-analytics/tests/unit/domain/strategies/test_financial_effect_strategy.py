from __future__ import annotations

import pytest

from income_analytics.domain.strategies.financial_effect_strategy import (
    FinancialEffectStrategy,
)


def test_financial_effect_strategy_should_be_abstract() -> None:
    with pytest.raises(TypeError):
        FinancialEffectStrategy()