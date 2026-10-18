from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.market_price import MarketPrice
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


def test_historical_projection_uses_latest_price_not_after_requested_date() -> None:
    event = create_buy_event()
    valuation_date = date(2026, 1, 10)
    prices = (
        MarketPrice(asset=event.asset, price=Money(Decimal("9")), effective_date=date(2026, 1, 9)),
        MarketPrice(
            asset=event.asset, price=Money(Decimal("11")), effective_date=date(2026, 1, 11)
        ),
    )

    projection = PortfolioProjector.project((event,), market_prices=prices, as_of=valuation_date)

    assert projection.positions[0].current_price == Money(Decimal("9"))


def test_historical_projection_rejects_future_only_price() -> None:
    event = create_buy_event()
    event.asset.update_current_price(Money(Decimal("500")))
    future_price = MarketPrice(
        asset=event.asset, price=Money(Decimal("11")), effective_date=date(2026, 1, 11)
    )

    projection = PortfolioProjector.project(
        (event,), market_prices=(future_price,), as_of=date(2026, 1, 10)
    )

    assert projection.positions[0].current_price is None


def test_historical_projection_rejects_undated_current_asset_price() -> None:
    event = create_buy_event()
    event.asset.update_current_price(Money(Decimal("500")))

    historical = PortfolioProjector.project((event,), as_of=date(2026, 1, 10))
    current = PortfolioProjector.project((event,))

    assert historical.positions[0].current_price is None
    assert current.positions[0].current_price == Money(Decimal("500"))


def test_historical_projection_accepts_price_on_exact_valuation_date() -> None:
    event = create_buy_event()
    exact_price = MarketPrice(
        asset=event.asset, price=Money(Decimal("10")), effective_date=date(2026, 1, 10)
    )

    projection = PortfolioProjector.project(
        (event,), market_prices=(exact_price,), as_of=date(2026, 1, 10)
    )

    assert projection.positions[0].current_price == Money(Decimal("10"))


@pytest.mark.parametrize(
    ("valuation_date", "expected_price"),
    [(date(2026, 1, 8), None), (date(2026, 1, 12), Decimal("11"))],
)
def test_historical_price_lookup_respects_first_and_last_boundaries(
    valuation_date: date, expected_price: Decimal | None
) -> None:
    event = create_buy_event()
    prices = (
        MarketPrice(asset=event.asset, price=Money(Decimal("9")), effective_date=date(2026, 1, 9)),
        MarketPrice(
            asset=event.asset, price=Money(Decimal("11")), effective_date=date(2026, 1, 11)
        ),
    )

    projection = PortfolioProjector.project((event,), market_prices=prices, as_of=valuation_date)

    actual = projection.positions[0].current_price
    assert actual == (Money(expected_price) if expected_price is not None else None)


def test_chronological_timeline_matches_independent_as_of_projection() -> None:
    event = create_buy_event()
    first_date = event.effective_date
    second_date = date(2026, 1, 20)
    third_date = date(2026, 1, 30)
    prices = (
        MarketPrice(asset=event.asset, price=Money(Decimal("31")), effective_date=first_date),
        MarketPrice(asset=event.asset, price=Money(Decimal("32")), effective_date=second_date),
    )
    dates = (first_date, second_date, third_date)

    actual = PortfolioProjector.project_timeline((event,), prices, dates, max_price_age_days=7)
    expected = tuple(
        PortfolioProjector.project_as_of(
            (event,),
            tuple(
                price
                for price in prices
                if price.effective_date <= as_of and (as_of - price.effective_date).days <= 7
            ),
            as_of,
            market_data_available=True,
        )
        for as_of in dates
    )

    assert actual == expected


def test_chronological_timeline_applies_each_event_once(monkeypatch) -> None:
    events = tuple(create_buy_event() for _ in range(12))
    dates = tuple(date(2026, 1, day) for day in range(1, 15))
    original = PortfolioProjector._apply_event
    calls = 0

    def count_applications(state, event) -> None:
        nonlocal calls
        calls += 1
        original(state, event)

    monkeypatch.setattr(PortfolioProjector, "_apply_event", staticmethod(count_applications))

    PortfolioProjector.project_timeline(events, (), dates)

    assert calls == len(events)


def test_projects_sell_with_financial_data_gap_without_inventing_cash_or_result() -> None:
    asset = build_asset()
    buy = FinancialEvent(
        account_id=uuid4(),
        asset=asset,
        event_type=FinancialEventType.BUY,
        occurred_at=datetime(2026, 1, 9, tzinfo=UTC),
        quantity=Quantity(Decimal("50")),
        unit_price=Money(Decimal("10")),
        effective_date=date(2026, 1, 9),
    )
    sell = FinancialEvent(
        account_id=buy.account_id,
        asset=asset,
        event_type=FinancialEventType.SELL,
        occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
        quantity=Quantity(Decimal("31")),
        metadata={"financial_status": "DATA_GAP"},
        effective_date=date(2026, 1, 10),
    )

    portfolio = PortfolioProjector.project([buy, sell])

    assert portfolio.positions[0].quantity == Quantity(Decimal("19"))
    assert portfolio.positions[0].cost == Money(Decimal("190"))
    assert portfolio.positions[0].realized_result == Money.zero()
    assert portfolio.cash == Money(Decimal("-500"))


def test_unmatched_internal_transfer_debit_does_not_block_portfolio_projection() -> None:
    event = FinancialEvent(
        account_id=uuid4(),
        asset=build_asset(),
        event_type=FinancialEventType.SELL,
        occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
        quantity=Quantity(Decimal("5")),
        unit_price=Money(Decimal("10")),
        effective_date=date(2026, 1, 10),
        metadata={"capital_flow_type": "INTERNAL_TRANSFER"},
    )

    portfolio = PortfolioProjector.project([event])

    assert portfolio.positions == ()
    assert portfolio.cash == Money.zero()


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


def test_history_sweep_does_not_use_a_future_quote_or_asset_price_fallback() -> None:
    asset = build_asset()
    asset.update_current_price(Money(Decimal("99")))
    buy = FinancialEvent(
        account_id=uuid4(),
        asset=asset,
        event_type=FinancialEventType.BUY,
        occurred_at=datetime(2026, 1, 5, tzinfo=UTC),
        effective_date=date(2026, 1, 5),
        quantity=Quantity(Decimal("1")),
        unit_price=Money(Decimal("10")),
    )
    future_quote = MarketPrice(
        asset=asset,
        price=Money(Decimal("20")),
        effective_date=date(2026, 1, 10),
    )

    history = PortfolioProjector.history((buy,), (future_quote,))

    assert history.snapshots[0].effective_date == date(2026, 1, 5)
    assert history.snapshots[0].portfolio.positions[0].current_price is None
    assert history.snapshots[1].portfolio.positions[0].current_price == Money(Decimal("20"))
