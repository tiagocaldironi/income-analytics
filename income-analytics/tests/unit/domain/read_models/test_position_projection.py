from __future__ import annotations

from decimal import Decimal

import pytest

from income_analytics.domain.read_models.position_projection import (
    PositionProjection,
)
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from income_analytics.domain.value_objects.ticker import Ticker
from tests.unit.domain.builders import build_asset


def test_should_create_position_projection() -> None:
    asset = build_asset()
    projection = PositionProjection(
        asset=asset,
        quantity=Quantity(Decimal("100")),
        average_cost=Money(Decimal("30")),
        invested_amount=Money(Decimal("3000")),
    )

    assert projection.asset.ticker == Ticker("PETR4")
    assert projection.quantity == Quantity(Decimal("100"))
    assert projection.average_cost == Money(Decimal("30"))
    assert projection.invested_amount == Money(Decimal("3000"))


def test_should_identify_non_empty_position() -> None:
    projection = PositionProjection(
        asset=build_asset(),
        quantity=Quantity(Decimal("100")),
        average_cost=Money(Decimal("30")),
        invested_amount=Money(Decimal("3000")),
    )

    assert projection.is_empty is False


def test_should_identify_empty_position() -> None:
    projection = PositionProjection(
        asset=build_asset(),
        quantity=Quantity(Decimal("0")),
        average_cost=Money(Decimal("0")),
        invested_amount=Money(Decimal("0")),
    )

    assert projection.is_empty is True


def test_should_be_immutable() -> None:
    projection = PositionProjection(
        asset=build_asset(),
        quantity=Quantity(Decimal("100")),
        average_cost=Money(Decimal("30")),
        invested_amount=Money(Decimal("3000")),
    )

    with pytest.raises(Exception):
        projection.quantity = Quantity(Decimal("50"))
