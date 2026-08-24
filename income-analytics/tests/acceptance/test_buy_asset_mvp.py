from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.projectors.portfolio_projector import PortfolioProjector
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from tests.unit.domain.builders import build_asset


def test_investor_accumulates_two_purchases_in_one_position() -> None:
    """An investor sees the consolidated position after two PETR4 purchases."""
    account_id = uuid4()
    asset = build_asset()
    occurred_at = datetime(2026, 1, 10, tzinfo=UTC)

    portfolio = PortfolioProjector.project(
        [
            FinancialEvent(
                account_id=account_id,
                asset=asset,
                event_type=FinancialEventType.BUY,
                occurred_at=occurred_at,
                quantity=Quantity(Decimal("100")),
                unit_price=Money(Decimal("30.00")),
            ),
            FinancialEvent(
                account_id=account_id,
                asset=asset,
                event_type=FinancialEventType.BUY,
                occurred_at=occurred_at,
                quantity=Quantity(Decimal("100")),
                unit_price=Money(Decimal("40.00")),
            ),
        ]
    )

    position = portfolio.positions[0]
    assert position.asset == asset
    assert position.quantity == Quantity(Decimal("200"))
    assert position.cost == Money(Decimal("7000.00"))
    assert position.average_price == Money(Decimal("35.00"))
