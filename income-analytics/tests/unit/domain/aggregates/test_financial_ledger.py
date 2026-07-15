from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from income_analytics.domain.aggregates.financial_ledger import FinancialLedger
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.events.financial_event_registered import (
    FinancialEventRegistered,
)
from income_analytics.domain.events.ledger_created import LedgerCreated
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity


def create_event(
    *,
    account_id=None,
    occurred_at=None,
) -> FinancialEvent:
    account_id = account_id or uuid4()

    return FinancialEvent(
        account_id=account_id,
        asset_id=uuid4(),
        event_type=FinancialEventType.BUY,
        occurred_at=occurred_at
        or datetime(2026, 1, 10, tzinfo=UTC),
        quantity=Quantity(Decimal("100")),
        unit_price=Money(Decimal("10")),
        total_amount=Money(Decimal("1000")),
    )


def test_should_create_ledger() -> None:
    account_id = uuid4()

    ledger = FinancialLedger.create(account_id)

    assert ledger.account_id == account_id
    assert ledger.size == 0


def test_should_register_ledger_created_domain_event() -> None:
    ledger = FinancialLedger.create(uuid4())

    assert len(ledger.domain_events) == 1
    assert isinstance(ledger.domain_events[0], LedgerCreated)


def test_should_append_financial_event() -> None:
    account_id = uuid4()

    ledger = FinancialLedger.create(account_id)
    ledger.clear_domain_events()

    event = create_event(account_id=account_id)

    ledger.append(event)

    assert ledger.size == 1
    assert ledger.events[0] == event


def test_should_reject_duplicate_events() -> None:
    account_id = uuid4()

    ledger = FinancialLedger.create(account_id)

    event = create_event(account_id=account_id)

    ledger.append(event)

    with pytest.raises(ValueError):
        ledger.append(event)


def test_should_reject_event_from_another_account() -> None:
    ledger = FinancialLedger.create(uuid4())

    another_event = create_event(account_id=uuid4())

    with pytest.raises(ValueError):
        ledger.append(another_event)


def test_should_keep_events_ordered() -> None:
    account_id = uuid4()

    ledger = FinancialLedger.create(account_id)

    event_2 = create_event(
        account_id=account_id,
        occurred_at=datetime(2026, 2, 10, tzinfo=UTC),
    )

    event_1 = create_event(
        account_id=account_id,
        occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
    )

    ledger.append(event_2)
    ledger.append(event_1)

    assert ledger.events[0] == event_1
    assert ledger.events[1] == event_2


def test_should_return_immutable_event_stream() -> None:
    account_id = uuid4()

    ledger = FinancialLedger.create(account_id)

    events = ledger.events

    assert isinstance(events, tuple)
    assert len(events) == 0


def test_should_register_financial_event_registered() -> None:
    account_id = uuid4()

    ledger = FinancialLedger.create(account_id)
    ledger.clear_domain_events()

    event = create_event(account_id=account_id)

    ledger.append(event)

    assert len(ledger.domain_events) == 1
    assert isinstance(
        ledger.domain_events[0],
        FinancialEventRegistered,
    )


def test_should_clear_domain_events() -> None:
    ledger = FinancialLedger.create(uuid4())

    assert ledger.has_domain_events

    ledger.clear_domain_events()

    assert not ledger.has_domain_events
    assert ledger.domain_events == ()


def test_should_replay_events_in_order() -> None:
    account_id = uuid4()

    ledger = FinancialLedger.create(account_id)

    event_2 = create_event(
        account_id=account_id,
        occurred_at=datetime(2026, 3, 10, tzinfo=UTC),
    )

    event_1 = create_event(
        account_id=account_id,
        occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
    )

    ledger.append(event_2)
    ledger.append(event_1)

    replay = ledger.replay()

    assert replay[0] == event_1
    assert replay[1] == event_2