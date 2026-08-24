"""
Projects a PortfolioProjection from a stream of Financial Events.
"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from income_analytics.domain.effects.position_effect import PositionEffect
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.projectors._position_accumulator import (
    PositionAccumulator,
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
    ) -> PortfolioProjection:

        positions: dict[UUID, PositionAccumulator] = {}

        for event in events:

            effects = FinancialEffectFactory.from_event(event)

            for effect in effects:
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

        for accumulator in positions.values():

            projections.append(
                PositionProjection(
                    asset=accumulator.asset,
                    quantity=Quantity(accumulator.quantity),
                cost=accumulator.cost,
                average_price=accumulator.average_price,
                realized_result=accumulator.realized_result,
                )
            )

            total += accumulator.cost
            total_realized_result += accumulator.realized_result

        projections.sort(key=lambda projection: str(projection.asset.ticker))

        return PortfolioProjection(
            positions=tuple(projections),
            total_cost=total,
            total_realized_result=total_realized_result,
        )
