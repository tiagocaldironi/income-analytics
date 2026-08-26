"""
Projects a PortfolioProjection from a stream of Financial Events.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from uuid import UUID

from income_analytics.domain.effects.cash_effect import CashEffect
from income_analytics.domain.effects.income_effect import IncomeEffect
from income_analytics.domain.effects.position_effect import PositionEffect
from income_analytics.domain.entities.financial_event import FinancialEvent
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
    ) -> PortfolioProjection:
        """Build a projection from the events and prices available as of a date."""
        ordered_events = sorted(
            (
                event
                for event in events
                if as_of is None or event.effective_date <= as_of
            ),
            key=lambda event: (event.effective_date, event.registered_at, event.id),
        )
        market_price_stream = tuple(market_prices)
        available_prices = tuple(
            price
            for price in market_price_stream
            if as_of is None or price.effective_date <= as_of
        )
        current_prices = cls._current_prices(available_prices)
        has_market_data = bool(market_price_stream)

        positions: dict[UUID, PositionAccumulator] = {}
        income_by_asset: dict[UUID, Money] = {}
        cash = Money.zero()
        total_contributions = Money.zero()
        total_withdrawals = Money.zero()

        for event in ordered_events:

            if event.event_type is FinancialEventType.DEPOSIT:
                total_contributions += event.total_amount
            elif event.event_type is FinancialEventType.WITHDRAWAL:
                total_withdrawals += event.total_amount

            effects = FinancialEffectFactory.from_event(event)

            for effect in effects:
                if isinstance(effect, CashEffect):
                    cash += effect.amount
                    continue

                if isinstance(effect, IncomeEffect):
                    income_by_asset[effect.asset.id] = (
                        income_by_asset.get(effect.asset.id, Money.zero()) + effect.amount
                    )
                    continue

                if not isinstance(effect, PositionEffect):
                    continue

                accumulator = positions.get(effect.asset.id)

                if accumulator is None:
                    accumulator = PositionAccumulator(asset=effect.asset)
                    positions[effect.asset.id] = accumulator

                accumulator.apply(effect)

        projections: list[PositionProjection] = []

        total = Money.zero()
        total_realized_result = Money.zero()
        total_income_received = Money.zero()

        for accumulator in positions.values():

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
                    use_asset_price=not has_market_data,
                    asset_price=accumulator.asset.current_price,
                ),
                income_received=income_by_asset.get(accumulator.asset.id, Money.zero()),
                )
            )

            total += accumulator.cost
            total_realized_result += accumulator.realized_result
            total_income_received += income_by_asset.get(accumulator.asset.id, Money.zero())

        projections.sort(key=lambda projection: str(projection.asset.ticker))

        return PortfolioProjection(
            positions=tuple(projections),
            total_cost=total,
            total_realized_result=total_realized_result,
            cash=cash,
            income_received=total_income_received,
            total_contributions=total_contributions,
            total_withdrawals=total_withdrawals,
        )

    @classmethod
    def project_as_of(
        cls,
        events: Iterable[FinancialEvent],
        market_prices: Iterable[MarketPrice],
        as_of: date,
    ) -> PortfolioProjection:
        """Build the state of a portfolio at the end of an effective date."""
        return cls.project(events, market_prices=market_prices, as_of=as_of)

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
        return PortfolioHistory(
            snapshots=tuple(
                PortfolioSnapshot(
                    effective_date=effective_date,
                    portfolio=cls.project_as_of(
                        event_stream,
                        price_stream,
                        effective_date,
                    ),
                )
                for effective_date in effective_dates
            )
        )

    @staticmethod
    def _current_prices(market_prices: Iterable[MarketPrice]) -> dict[UUID, Money]:
        current_prices: dict[UUID, Money] = {}
        for market_price in sorted(
            market_prices,
            key=lambda price: (price.effective_date, price.registered_at, price.id),
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
