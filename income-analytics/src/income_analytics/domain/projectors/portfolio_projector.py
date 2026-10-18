"""
Projects a PortfolioProjection from a stream of Financial Events.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from income_analytics.domain.effects.cash_effect import CashEffect
from income_analytics.domain.effects.income_effect import IncomeEffect
from income_analytics.domain.effects.position_effect import PositionEffect
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.capital_flow_type import CapitalFlowType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.market_price import MarketPrice
from income_analytics.domain.projectors._position_accumulator import (
    PositionAccumulator,
)
from income_analytics.domain.read_models.portfolio_history import (
    PortfolioHistory,
    PortfolioSnapshot,
)
from income_analytics.domain.read_models.portfolio_projection import (
    PortfolioProjection,
)
from income_analytics.domain.read_models.position_projection import (
    PositionProjection,
)
from income_analytics.domain.services.financial_effect_factory import (
    FinancialEffectFactory,
)
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity


@dataclass(slots=True)
class _PortfolioProjectionState:
    positions: dict[UUID, PositionAccumulator] = field(default_factory=dict)
    income_by_asset: dict[UUID, Money] = field(default_factory=dict)
    cash: Money = field(default_factory=Money.zero)
    cash_by_currency: dict[str, Money] = field(default_factory=dict)
    total_contributions: Money = field(default_factory=Money.zero)
    total_withdrawals: Money = field(default_factory=Money.zero)


class PortfolioProjector:
    """
    Builds a PortfolioProjection from Financial Events.
    """

    @classmethod
    def project(
        cls,
        events: Iterable[FinancialEvent],
        *,
        market_prices: Iterable[MarketPrice] = (),
        as_of: date | None = None,
        allow_asset_price_fallback: bool = True,
        market_data_available: bool | None = None,
    ) -> PortfolioProjection:
        """Build a projection from the events and prices available as of a date."""
        ordered_events = sorted(
            (event for event in events if as_of is None or event.effective_date <= as_of),
            # Python's sort is stable: when imported/legacy events share the
            # same registered_at precision, preserve their source order rather
            # than inventing an execution order from random UUIDs.
            key=lambda event: (event.effective_date, event.registered_at),
        )
        market_price_stream = tuple(market_prices)
        available_prices = tuple(
            price for price in market_price_stream if as_of is None or price.effective_date <= as_of
        )
        current_prices = cls._current_prices(available_prices)
        has_market_data = (
            bool(market_price_stream) if market_data_available is None else market_data_available
        )

        state = _PortfolioProjectionState()
        for event in ordered_events:
            cls._apply_event(state, event)
        return cls._build_projection(
            state,
            current_prices,
            has_market_data=has_market_data,
            # Asset.current_price has no point-in-time evidence. It is valid
            # for a current projection only, never for a dated valuation.
            allow_asset_price_fallback=allow_asset_price_fallback and as_of is None,
        )

    @classmethod
    def project_timeline(
        cls,
        events: Iterable[FinancialEvent],
        market_prices: Iterable[MarketPrice],
        effective_dates: Iterable[date],
        *,
        allow_asset_price_fallback: bool = False,
        market_data_available: bool | None = None,
        max_price_age_days: int | None = None,
    ) -> tuple[PortfolioProjection, ...]:
        """Project ordered as-of snapshots while replaying each event once."""
        event_stream = tuple(events)
        price_stream = tuple(market_prices)
        ordered_events = sorted(
            event_stream, key=lambda event: (event.effective_date, event.registered_at)
        )
        ordered_prices = sorted(
            price_stream, key=lambda price: (price.effective_date, price.registered_at)
        )
        has_market_data = (
            bool(price_stream) if market_data_available is None else market_data_available
        )
        event_index = 0
        price_index = 0
        state = _PortfolioProjectionState()
        latest_prices: dict[UUID, MarketPrice] = {}
        snapshots: list[PortfolioProjection] = []
        for as_of in sorted(set(effective_dates)):
            while (
                event_index < len(ordered_events)
                and ordered_events[event_index].effective_date <= as_of
            ):
                cls._apply_event(state, ordered_events[event_index])
                event_index += 1
            while (
                price_index < len(ordered_prices)
                and ordered_prices[price_index].effective_date <= as_of
            ):
                price = ordered_prices[price_index]
                latest_prices[price.asset.id] = price
                price_index += 1
            current_prices = {
                asset_id: price.price
                for asset_id, price in latest_prices.items()
                if max_price_age_days is None
                or (as_of - price.effective_date).days <= max_price_age_days
            }
            snapshots.append(
                cls._build_projection(
                    state,
                    current_prices,
                    has_market_data=has_market_data,
                    allow_asset_price_fallback=allow_asset_price_fallback,
                )
            )
        return tuple(snapshots)

    @staticmethod
    def _apply_event(state: _PortfolioProjectionState, event: FinancialEvent) -> None:
        # Historical B3 exports can begin after an asset was already held.
        # An unmatched custody transfer debit is not a cash sale and is skipped.
        if (
            event.event_type is FinancialEventType.SELL
            and event.asset is not None
            and event.quantity is not None
            and event.quantity.value
            > state.positions.get(event.asset.id, PositionAccumulator(asset=event.asset)).quantity
            and (
                event.financial_status == "DATA_GAP"
                or event.capital_flow_type is CapitalFlowType.INTERNAL_TRANSFER
            )
        ):
            return
        if event.event_type is FinancialEventType.DEPOSIT:
            state.total_contributions += event.total_amount
        elif event.event_type is FinancialEventType.WITHDRAWAL:
            state.total_withdrawals += event.total_amount
        for effect in FinancialEffectFactory.from_event(event):
            if isinstance(effect, CashEffect):
                state.cash += effect.amount
                currency = effect.currency_code.upper()
                state.cash_by_currency[currency] = (
                    state.cash_by_currency.get(currency, Money.zero()) + effect.amount
                )
            elif isinstance(effect, IncomeEffect):
                state.income_by_asset[effect.asset.id] = (
                    state.income_by_asset.get(effect.asset.id, Money.zero()) + effect.amount
                )
            elif isinstance(effect, PositionEffect):
                accumulator = state.positions.get(effect.asset.id)
                if accumulator is None:
                    accumulator = PositionAccumulator(asset=effect.asset)
                    state.positions[effect.asset.id] = accumulator
                accumulator.apply(effect)

    @classmethod
    def _build_projection(
        cls,
        state: _PortfolioProjectionState,
        current_prices: dict[UUID, Money],
        *,
        has_market_data: bool,
        allow_asset_price_fallback: bool,
    ) -> PortfolioProjection:
        projections: list[PositionProjection] = []

        total = Money.zero()
        total_realized_result = Money.zero()
        total_income_received = Money.zero()

        for accumulator in state.positions.values():
            projections.append(
                PositionProjection(
                    asset=accumulator.asset,
                    quantity=Quantity(accumulator.quantity),
                    cost=accumulator.cost,
                    average_price=accumulator.average_price,
                    realized_result=accumulator.realized_result,
                    current_price=cls._current_price(
                        accumulator.asset.id,
                        current_prices,
                        use_asset_price=(not has_market_data and allow_asset_price_fallback),
                        asset_price=accumulator.asset.current_price,
                    ),
                    income_received=state.income_by_asset.get(accumulator.asset.id, Money.zero()),
                )
            )

            total += accumulator.cost
            total_realized_result += accumulator.realized_result
            total_income_received += state.income_by_asset.get(accumulator.asset.id, Money.zero())

        projections.sort(key=lambda projection: str(projection.asset.ticker))

        return PortfolioProjection(
            positions=tuple(projections),
            total_cost=total,
            total_realized_result=total_realized_result,
            cash=state.cash,
            income_received=total_income_received,
            total_contributions=state.total_contributions,
            total_withdrawals=state.total_withdrawals,
            cash_by_currency=tuple(sorted(state.cash_by_currency.items())),
        )

    @classmethod
    def project_as_of(
        cls,
        events: Iterable[FinancialEvent],
        market_prices: Iterable[MarketPrice],
        as_of: date,
        *,
        allow_asset_price_fallback: bool = True,
        market_data_available: bool | None = None,
    ) -> PortfolioProjection:
        """Build the state of a portfolio at the end of an effective date."""
        return cls.project(
            events,
            market_prices=market_prices,
            as_of=as_of,
            allow_asset_price_fallback=allow_asset_price_fallback,
            market_data_available=market_data_available,
        )

    @classmethod
    def history(
        cls,
        events: Iterable[FinancialEvent],
        market_prices: Iterable[MarketPrice],
    ) -> PortfolioHistory:
        """Derive a snapshot for each financial-event or market-price date."""
        event_stream = tuple(events)
        price_stream = tuple(market_prices)
        effective_dates = sorted(
            {event.effective_date for event in event_stream}
            | {price.effective_date for price in price_stream}
        )
        portfolios = cls.project_timeline(event_stream, price_stream, effective_dates)
        snapshots: list[PortfolioSnapshot] = []
        for effective_date, portfolio in zip(effective_dates, portfolios, strict=True):
            snapshots.append(
                PortfolioSnapshot(
                    effective_date=effective_date,
                    portfolio=portfolio,
                )
            )
        return PortfolioHistory(snapshots=tuple(snapshots))

    @staticmethod
    def _current_prices(market_prices: Iterable[MarketPrice]) -> dict[UUID, Money]:
        current_prices: dict[UUID, Money] = {}
        for market_price in sorted(
            market_prices,
            key=lambda price: (price.effective_date, price.registered_at),
        ):
            current_prices[market_price.asset.id] = market_price.price
        return current_prices

    @staticmethod
    def _current_price(
        asset_id: UUID,
        current_prices: dict[UUID, Money],
        *,
        use_asset_price: bool,
        asset_price: Money | None,
    ) -> Money | None:
        if asset_id in current_prices:
            return current_prices[asset_id]
        return asset_price if use_asset_price else None
