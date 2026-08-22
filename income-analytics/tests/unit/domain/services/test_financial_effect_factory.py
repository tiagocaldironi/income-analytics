from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from income_analytics.domain.effects.cash_effect import CashEffect
from income_analytics.domain.effects.cost_basis_effect import CostBasisEffect
from income_analytics.domain.effects.position_effect import PositionEffect
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.services.financial_effect_factory import (
    FinancialEffectFactory,
)
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from tests.unit.domain.builders import build_asset


def test_should_create_effects_for_buy() -> None:
    asset = build_asset()
    event = FinancialEvent(
        account_id=uuid4(),
        asset=asset,
        event_type=FinancialEventType.BUY,
        occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
        quantity=Quantity(Decimal("100")),
        unit_price=Money(Decimal("10")),
        total_amount=Money(Decimal("1000")),
    )

    effects = FinancialEffectFactory.from_event(event)

    assert len(effects) == 3

    assert isinstance(effects[0], PositionEffect)
    assert isinstance(effects[1], CashEffect)
    assert isinstance(effects[2], CostBasisEffect)
    assert effects[0].asset == asset
    assert effects[2].asset == asset
