from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from income_analytics.application.capital_applied import calculate_capital_applied
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.market_price import MarketPrice
from income_analytics.domain.projectors.portfolio_projector import PortfolioProjector
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from tests.unit.domain.builders import build_asset


def _event(asset, kind, quantity, price, day):
    return FinancialEvent(
        account_id=uuid4(),
        asset=asset,
        event_type=kind,
        occurred_at=datetime.combine(day, datetime.min.time(), tzinfo=UTC),
        effective_date=day,
        quantity=Quantity(Decimal(quantity)),
        unit_price=Money(Decimal(price)),
    )


def test_capital_applied_uses_open_position_average_cost_not_market_price():
    asset = build_asset(currency=SimpleNamespace(code="BRL"))
    events = (
        _event(asset, FinancialEventType.BUY, "10", "20", date(2026, 1, 1)),
        _event(asset, FinancialEventType.BUY, "10", "30", date(2026, 1, 2)),
    )
    results = tuple(
        calculate_capital_applied(
            PortfolioProjector.project(
                events,
                market_prices=(
                    MarketPrice(
                        asset=asset,
                        price=Money(price),
                        effective_date=date(2026, 1, 3),
                    ),
                ),
            ),
            base_currency="BRL",
        )
        for price in (Decimal("10"), Decimal("100"))
    )

    assert [result.amount for result in results] == [Decimal("500"), Decimal("500")]
    assert all(result.status == "AVAILABLE" for result in results)


def test_partial_sale_reduces_applied_capital_by_average_cost_not_sale_proceeds():
    asset = build_asset(currency=SimpleNamespace(code="BRL"))
    first = _event(asset, FinancialEventType.BUY, "100", "20", date(2026, 1, 1))
    sale = FinancialEvent(
        account_id=first.account_id,
        asset=asset,
        event_type=FinancialEventType.SELL,
        occurred_at=datetime(2026, 1, 2, tzinfo=UTC),
        effective_date=date(2026, 1, 2),
        quantity=Quantity(Decimal("40")),
        unit_price=Money(Decimal("30")),
    )

    result = calculate_capital_applied(
        PortfolioProjector.project((first, sale)), base_currency="BRL"
    )

    assert result.amount == Decimal("1200")
    assert result.status == "AVAILABLE"


def test_foreign_or_special_model_positions_block_a_misleading_partial_total():
    brl_asset = build_asset(currency=SimpleNamespace(code="BRL"))
    foreign_asset = build_asset(
        ticker=type(brl_asset.ticker)("MCD"),
        name="McDonald's",
        currency=SimpleNamespace(code="USD"),
        asset_class=AssetClass.INTERNATIONAL,
        asset_type=AssetType.STOCK,
    )
    events = (
        _event(brl_asset, FinancialEventType.BUY, "10", "20", date(2026, 1, 1)),
        _event(foreign_asset, FinancialEventType.BUY, "1", "300", date(2026, 1, 1)),
    )

    result = calculate_capital_applied(PortfolioProjector.project(events), base_currency="BRL")

    assert result.status == "PARTIAL"
    assert result.amount is None
    assert result.partial_amount == Decimal("200")
    assert result.incomplete_assets == ("MCD",)
    assert result.incomplete_reasons == (("MCD", "custo não convertido pela taxa histórica"),)
    assert result.included_position_count == 1


def test_no_open_positions_is_reported_as_real_zero():
    result = calculate_capital_applied(PortfolioProjector.project(()), base_currency="BRL")

    assert result.status == "ZERO"
    assert result.amount == Decimal("0")
