from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.projectors.portfolio_projector import PortfolioProjector
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from tests.unit.domain.builders import build_asset


def trade(
    event_type: FinancialEventType,
    asset: Asset,
    account_id: UUID,
    quantity: str,
    unit_price: str,
) -> FinancialEvent:
    return FinancialEvent(
        account_id=account_id,
        asset=asset,
        event_type=event_type,
        occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
        quantity=Quantity(Decimal(quantity)),
        unit_price=Money(Decimal(unit_price)),
    )


def project(
    operations: list[tuple[FinancialEventType, str, str]],
) -> tuple[Asset, PortfolioProjection]:
    asset = build_asset()
    account_id = uuid4()
    events = [
        trade(event_type, asset, account_id, quantity, unit_price)
        for event_type, quantity, unit_price in operations
    ]
    return asset, PortfolioProjector.project(events)


def test_buy_reduces_cash_without_realizing_a_result() -> None:
    _, portfolio = project([(FinancialEventType.BUY, "100", "30")])

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("100"))
    assert position.cost == Money(Decimal("3000"))
    assert portfolio.cash == Money(Decimal("-3000"))
    assert position.realized_result == Money.zero()


def test_cash_flow_is_separate_from_realized_result() -> None:
    asset, portfolio = project(
        [
            (FinancialEventType.BUY, "100", "30"),
            (FinancialEventType.SELL, "50", "50"),
        ]
    )

    position = portfolio.positions[0]
    assert position.asset == asset
    assert position.quantity == Quantity(Decimal("50"))
    assert position.cost == Money(Decimal("1500"))
    assert position.average_price == Money(Decimal("30"))
    assert portfolio.cash == Money(Decimal("-500"))
    assert position.realized_result == Money(Decimal("1000"))


def test_two_buys_and_a_sale_accumulate_cash_correctly() -> None:
    _, portfolio = project(
        [
            (FinancialEventType.BUY, "100", "30"),
            (FinancialEventType.BUY, "100", "40"),
            (FinancialEventType.SELL, "50", "50"),
        ]
    )

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("150"))
    assert position.cost == Money(Decimal("5250"))
    assert position.average_price == Money(Decimal("35"))
    assert portfolio.cash == Money(Decimal("-4500"))
    assert portfolio.total_realized_result == Money(Decimal("750"))


@pytest.mark.parametrize(
    ("sale_price", "expected_cash", "expected_result"),
    [("50", "2000", "2000"), ("20", "-1000", "-1000")],
)
def test_total_sale_updates_cash_and_realized_result(
    sale_price: str,
    expected_cash: str,
    expected_result: str,
) -> None:
    _, portfolio = project(
        [
            (FinancialEventType.BUY, "100", "30"),
            (FinancialEventType.SELL, "100", sale_price),
        ]
    )

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("0"))
    assert position.cost == Money.zero()
    assert portfolio.cash == Money(Decimal(expected_cash))
    assert position.realized_result == Money(Decimal(expected_result))


def test_buy_after_sale_updates_cash_without_resetting_realized_result() -> None:
    _, portfolio = project(
        [
            (FinancialEventType.BUY, "100", "30"),
            (FinancialEventType.SELL, "50", "50"),
            (FinancialEventType.BUY, "50", "60"),
        ]
    )

    position = portfolio.positions[0]
    assert position.quantity == Quantity(Decimal("100"))
    assert position.cost == Money(Decimal("4500"))
    assert position.average_price == Money(Decimal("45"))
    assert portfolio.cash == Money(Decimal("-3500"))
    assert position.realized_result == Money(Decimal("1000"))
