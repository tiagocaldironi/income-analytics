from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.projectors.portfolio_projector import PortfolioProjector
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from tests.unit.domain.builders import build_asset


def create_buy_event() -> FinancialEvent:
    return FinancialEvent(
        account_id=uuid4(),
        asset=build_asset(),
        event_type=FinancialEventType.BUY,
        occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
        quantity=Quantity(Decimal("100")),
        unit_price=Money(Decimal("30")),
    )


def test_projects_a_buy_from_event_to_portfolio_position() -> None:
    event = create_buy_event()

    portfolio = PortfolioProjector.project([event])

    position = portfolio.positions[0]
    assert position.asset == event.asset
    assert position.quantity == Quantity(Decimal("100"))
    assert position.cost == Money(Decimal("3000"))
    assert position.average_price == Money(Decimal("30"))
    assert portfolio.total_cost == Money(Decimal("3000"))


@pytest.mark.parametrize(
    ("quantity", "unit_price"),
    [
        (Decimal("0"), Decimal("30")),
        (Decimal("100"), Decimal("0")),
    ],
)
def test_rejects_non_positive_buy_values(
    quantity: Decimal,
    unit_price: Decimal,
) -> None:
    with pytest.raises(ValueError):
        FinancialEvent(
            account_id=uuid4(),
            asset=build_asset(),
            event_type=FinancialEventType.BUY,
            occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
            quantity=Quantity(quantity),
            unit_price=Money(unit_price),
        )


def test_rejects_buy_without_an_asset() -> None:
    with pytest.raises(ValueError, match="asset"):
        FinancialEvent(
            account_id=uuid4(),
            event_type=FinancialEventType.BUY,
            occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
            quantity=Quantity(Decimal("100")),
            unit_price=Money(Decimal("30")),
        )
