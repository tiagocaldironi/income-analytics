from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from income_analytics.domain.effects.income_effect import IncomeEffect
from income_analytics.domain.value_objects.money import Money


def test_should_create_income_effect() -> None:
    effect = IncomeEffect(
        financial_event_id=uuid4(),
        asset_id=uuid4(),
        amount=Money(Decimal("120")),
    )

    assert effect.amount == Money(Decimal("120"))


def test_income_effect_should_be_immutable() -> None:
    effect = IncomeEffect(
        financial_event_id=uuid4(),
        asset_id=uuid4(),
        amount=Money(Decimal("120")),
    )

    with pytest.raises(Exception):
        effect.amount = Money(Decimal("10"))