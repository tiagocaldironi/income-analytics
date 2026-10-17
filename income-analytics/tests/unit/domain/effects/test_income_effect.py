from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from income_analytics.domain.effects.income_effect import IncomeEffect
from income_analytics.domain.value_objects.money import Money
from tests.unit.domain.builders import build_asset


def test_should_create_income_effect() -> None:
    effect = IncomeEffect(
        financial_event_id=uuid4(),
        asset=build_asset(),
        amount=Money(Decimal("120")),
    )

    assert effect.amount == Money(Decimal("120"))


def test_income_effect_should_be_immutable() -> None:
    effect = IncomeEffect(
        financial_event_id=uuid4(),
        asset=build_asset(),
        amount=Money(Decimal("120")),
    )

    with pytest.raises(Exception):
        effect.amount = Money(Decimal("10"))
