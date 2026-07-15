from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from income_analytics.domain.effects.fx_effect import FxEffect
from income_analytics.domain.value_objects.money import Money


def test_should_create_fx_effect() -> None:
    effect = FxEffect(
        financial_event_id=uuid4(),
        original_amount=Money(Decimal("100")),
        converted_amount=Money(Decimal("530")),
    )

    assert effect.original_amount == Money(Decimal("100"))
    assert effect.converted_amount == Money(Decimal("530"))