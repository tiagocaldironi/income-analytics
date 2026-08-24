"""
Factory responsible for translating Financial Events into Financial Effects.
"""

from __future__ import annotations

from income_analytics.domain.effects.financial_effect import FinancialEffect
from income_analytics.domain.effects.position_effect import PositionEffect
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.financial_event_type import FinancialEventType


class FinancialEffectFactory:
    """
    Creates Financial Effects from Financial Events.

    This factory is responsible for translating immutable financial facts
    into immutable financial effects that will later be processed by the
    business engines.
    """

    @classmethod
    def from_event(
        cls,
        event: FinancialEvent,
    ) -> tuple[FinancialEffect, ...]:
        """
        Creates the financial effects associated with a financial event.
        """

        match event.event_type:
            case FinancialEventType.BUY:
                return cls._buy(event)

            case FinancialEventType.SELL:
                return cls._sell(event)

            case _:
                raise ValueError(
                    f"Unsupported financial event type: {event.event_type}"
                )

    @staticmethod
    def _buy(
        event: FinancialEvent,
    ) -> tuple[FinancialEffect, ...]:

        if event.asset is None or event.quantity is None:
            raise ValueError("BUY event must be valid before effects are created.")

        return (
            PositionEffect(
                financial_event_id=event.id,
                asset=event.asset,
                quantity_delta=event.quantity.value,
                cost_delta=event.total_amount,
            ),
        )

    @staticmethod
    def _sell(event: FinancialEvent) -> tuple[FinancialEffect, ...]:
        if event.asset is None or event.quantity is None:
            raise ValueError("SELL event must be valid before effects are created.")

        return (
            PositionEffect(
                financial_event_id=event.id,
                asset=event.asset,
                quantity_delta=-event.quantity.value,
                sale_value=event.total_amount,
            ),
        )
