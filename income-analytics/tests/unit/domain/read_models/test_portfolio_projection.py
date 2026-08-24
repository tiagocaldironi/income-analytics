from __future__ import annotations

from decimal import Decimal

import pytest

from income_analytics.domain.read_models.portfolio_projection import (
    PortfolioProjection,
)
from income_analytics.domain.read_models.position_projection import (
    PositionProjection,
)
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from tests.unit.domain.builders import build_asset


def create_position() -> PositionProjection:
    return PositionProjection(
        asset=build_asset(),
        quantity=Quantity(Decimal("100")),
        cost=Money(Decimal("3000")),
        average_price=Money(Decimal("30")),
    )


def test_should_create_portfolio_projection() -> None:
    portfolio = PortfolioProjection(
        positions=(create_position(),),
        total_cost=Money(Decimal("3000")),
    )

    assert portfolio.position_count == 1
    assert portfolio.total_cost == Money(Decimal("3000"))


def test_should_create_empty_portfolio() -> None:
    portfolio = PortfolioProjection(
        positions=(),
        total_cost=Money.zero(),
    )

    assert portfolio.is_empty
    assert portfolio.position_count == 0


def test_should_be_immutable() -> None:
    portfolio = PortfolioProjection(
        positions=(create_position(),),
        total_cost=Money(Decimal("3000")),
    )

    with pytest.raises(Exception):
        portfolio.total_invested = Money.zero()
