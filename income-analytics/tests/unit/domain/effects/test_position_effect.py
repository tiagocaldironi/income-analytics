from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from income_analytics.domain.effects.position_effect import PositionEffect
from tests.unit.domain.builders import build_asset


def test_should_create_position_effect() -> None:
    effect = PositionEffect(
        financial_event_id=uuid4(),
        asset=build_asset(),
        quantity_delta=Decimal("100"),
    )

    assert effect.quantity_delta == Decimal("100")


def test_position_effect_should_be_immutable() -> None:
    effect = PositionEffect(
        financial_event_id=uuid4(),
        asset=build_asset(),
        quantity_delta=Decimal("100"),
    )

    with pytest.raises(Exception):
        effect.quantity_delta = Decimal("50")


def test_two_position_effects_should_be_equal() -> None:
    event_id = uuid4()
    asset = build_asset()

    left = PositionEffect(
        financial_event_id=event_id,
        asset=asset,
        quantity_delta=Decimal("10"),
    )

    right = PositionEffect(
        financial_event_id=event_id,
        asset=asset,
        quantity_delta=Decimal("10"),
    )

    assert left == right
