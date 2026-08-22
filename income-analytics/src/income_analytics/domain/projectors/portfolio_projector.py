"""
Projects a PortfolioProjection from a stream of Financial Events.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from uuid import UUID

from income_analytics.domain.effects.cost_basis_effect import CostBasisEffect
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

            position_effect = next(
                (
                    effect
                    for effect in effects
                    if isinstance(effect, PositionEffect)
                ),
                None,
            )

            cost_effect = next(
                (
                    effect
                    for effect in effects
                    if isinstance(effect, CostBasisEffect)
                ),
                None,
            )

            if position_effect is None or cost_effect is None:
                continue

            accumulator = positions.get(position_effect.asset.id)

            if accumulator is None:
                accumulator = PositionAccumulator(asset=position_effect.asset)
                positions[position_effect.asset.id] = accumulator

            accumulator.add_buy(
                quantity=position_effect.quantity_delta,
                invested=cost_effect.total_cost_delta.amount,
            )

        projections: list[PositionProjection] = []

        total = Decimal("0")

        for accumulator in positions.values():

            projections.append(
                PositionProjection(
                    asset=accumulator.asset,
                    quantity=Quantity(accumulator.quantity),
                    average_cost=Money(accumulator.average_cost),
                    invested_amount=accumulator.invested_amount,
                )
            )

            total += accumulator.invested

        projections.sort(key=lambda projection: str(projection.asset.ticker))

        return PortfolioProjection(
            positions=tuple(projections),
            total_invested=Money(total),
        )
