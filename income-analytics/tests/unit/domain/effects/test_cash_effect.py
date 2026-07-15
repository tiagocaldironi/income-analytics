from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from income_analytics.domain.effects.cash_effect import CashEffect
from income_analytics.domain.value_objects.money import Money


def test_should_create_cash_effect() -> None:
    effect = CashEffect(
        financial_event_id=uuid4(),
        account_id=uuid4(),
        amount=Money(Decimal("100")),
    )

    assert effect.amount == Money(Decimal("100"))


def test_cash_effect_should_be_immutable() -> None:
    effect = CashEffect(
        financial_event_id=uuid4(),
        account_id=uuid4(),
        amount=Money(Decimal("100")),
    )

    with pytest.raises(Exception):
        effect.amount = Money(Decimal("10"))