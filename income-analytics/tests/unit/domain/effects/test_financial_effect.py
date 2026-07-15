from __future__ import annotations

from uuid import uuid4

from income_analytics.domain.effects.financial_effect import FinancialEffect


def test_should_create_financial_effect() -> None:
    event_id = uuid4()

    effect = FinancialEffect(
        financial_event_id=event_id,
    )

    assert effect.financial_event_id == event_id