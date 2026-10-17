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


def buy(asset: object, account_id: object, price: str, quantity: str = "100") -> FinancialEvent:
    return FinancialEvent(
        account_id=account_id,  # type: ignore[arg-type]
        asset=asset,  # type: ignore[arg-type]
        event_type=FinancialEventType.BUY,
        occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
        quantity=Quantity(Decimal(quantity)),
        unit_price=Money(Decimal(price)),
    )


def sell(asset: object, account_id: object, price: str, quantity: str) -> FinancialEvent:
    return FinancialEvent(
        account_id=account_id,  # type: ignore[arg-type]
        asset=asset,  # type: ignore[arg-type]
        event_type=FinancialEventType.SELL,
        occurred_at=datetime(2026, 1, 11, tzinfo=UTC),
        quantity=Quantity(Decimal(quantity)),
        unit_price=Money(Decimal(price)),
    )


def initial_buys() -> tuple[object, object, list[FinancialEvent]]:
    account_id = uuid4()
    asset = build_asset()
    return asset, account_id, [buy(asset, account_id, "30"), buy(asset, account_id, "40")]


@pytest.mark.parametrize(
    ("sale_price", "expected_result"),
    [("50", "750"), ("20", "-750")],
)
def test_partial_sale_realizes_profit_or_loss(
    sale_price: str,
    expected_result: str,
) -> None:
    asset, account_id, events = initial_buys()

    portfolio = PortfolioProjector.project(events + [sell(asset, account_id, sale_price, "50")])

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("150"))
    assert position.cost == Money(Decimal("5250"))
    assert position.average_price == Money(Decimal("35"))
    assert position.realized_result == Money(Decimal(expected_result))


def test_selling_the_entire_position_keeps_cost_and_average_price_at_zero() -> None:
    asset, account_id, events = initial_buys()

    portfolio = PortfolioProjector.project(events + [sell(asset, account_id, "50", "200")])

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("0"))
    assert position.cost == Money.zero()
    assert position.average_price == Money.zero()
    assert position.realized_result == Money(Decimal("3000"))


def test_rejects_sale_larger_than_current_position() -> None:
    asset, account_id, _ = initial_buys()

    with pytest.raises(ValueError, match="more than"):
        PortfolioProjector.project(
            [buy(asset, account_id, "30"), sell(asset, account_id, "40", "101")]
        )


def test_buy_after_sale_updates_average_and_preserves_realized_result() -> None:
    asset, account_id, events = initial_buys()

    portfolio = PortfolioProjector.project(
        events
        + [
            sell(asset, account_id, "50", "50"),
            buy(asset, account_id, "60", "50"),
        ]
    )

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("200"))
    assert position.cost == Money(Decimal("8250"))
    assert position.average_price == Money(Decimal("41.25"))
    assert position.realized_result == Money(Decimal("750"))
