from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from tests.unit.domain.builders import build_asset


def test_sell_derives_its_total_from_quantity_and_unit_price() -> None:
    event = FinancialEvent(
        account_id=uuid4(),
        asset=build_asset(),
        event_type=FinancialEventType.SELL,
        occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
        quantity=Quantity(Decimal("50")),
        unit_price=Money(Decimal("50.00")),
    )

    assert event.total_amount == Money(Decimal("2500.00"))


@pytest.mark.parametrize(
    ("quantity", "unit_price"),
    [
        (Decimal("0"), Decimal("50")),
        (Decimal("50"), Decimal("0")),
        (Decimal("50"), Decimal("-50")),
    ],
)
def test_sell_rejects_non_positive_quantity_or_price(
    quantity: Decimal,
    unit_price: Decimal,
) -> None:
    with pytest.raises(ValueError):
        FinancialEvent(
            account_id=uuid4(),
            asset=build_asset(),
            event_type=FinancialEventType.SELL,
            occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
            quantity=Quantity(quantity),
            unit_price=Money(unit_price),
        )


def test_quantity_rejects_a_negative_sell_quantity() -> None:
    with pytest.raises(ValueError, match="negative"):
        Quantity(Decimal("-1"))


def test_sell_rejects_an_absent_asset() -> None:
    with pytest.raises(ValueError, match="asset"):
        FinancialEvent(
            account_id=uuid4(),
            event_type=FinancialEventType.SELL,
            occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
            quantity=Quantity(Decimal("50")),
            unit_price=Money(Decimal("50")),
        )
