from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from income_analytics.domain.effects.cost_basis_effect import CostBasisEffect
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from tests.unit.domain.builders import build_asset


def test_should_create_cost_basis_effect() -> None:
    effect = CostBasisEffect(
        financial_event_id=uuid4(),
        asset=build_asset(),
        quantity_delta=Quantity(Decimal("100")),
        total_cost_delta=Money(Decimal("1000")),
    )

    assert effect.total_cost_delta == Money(Decimal("1000"))
