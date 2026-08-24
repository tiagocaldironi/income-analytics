from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

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
        unit_price=Money(Decimal("30")),
    )

    effects = FinancialEffectFactory.from_event(event)

    assert len(effects) == 1

    assert isinstance(effects[0], PositionEffect)
    assert effects[0].asset == asset
    assert effects[0].quantity_delta == Decimal("100")
    assert effects[0].cost_delta == Money(Decimal("3000"))


def test_should_create_a_position_effect_for_sell() -> None:
    asset = build_asset()
    event = FinancialEvent(
        account_id=uuid4(),
        asset=asset,
        event_type=FinancialEventType.SELL,
        occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
        quantity=Quantity(Decimal("50")),
        unit_price=Money(Decimal("50")),
    )

    effects = FinancialEffectFactory.from_event(event)

    assert len(effects) == 1
    assert isinstance(effects[0], PositionEffect)
    assert effects[0].asset == asset
    assert effects[0].quantity_delta == Decimal("-50")
    assert effects[0].cost_delta is None
    assert effects[0].sale_value == Money(Decimal("2500"))
