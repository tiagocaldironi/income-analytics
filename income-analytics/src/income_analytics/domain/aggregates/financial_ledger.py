"""
Aggregate Root representing the immutable financial ledger of an account.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from income_analytics.domain.aggregates.aggregate_root import AggregateRoot
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.events.financial_event_registered import (
    FinancialEventRegistered,
)
from income_analytics.domain.events.ledger_created import LedgerCreated


@dataclass(slots=True, eq=False, kw_only=True)
class FinancialLedger(AggregateRoot):
    """
    Aggregate Root that owns the immutable Financial Event stream.
    """

    account_id: UUID

    _events: list[FinancialEvent] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    @classmethod
    def create(cls, account_id: UUID) -> "FinancialLedger":
        """
        Factory method for creating a new Financial Ledger.
        """

        ledger = cls(account_id=account_id)

        ledger.add_domain_event(
            LedgerCreated(
                ledger_id=ledger.id,
                account_id=account_id,
            )
        )

        return ledger

    def append(self, event: FinancialEvent) -> None:
        """
        Appends a Financial Event to the ledger.
        """

        if event.account_id != self.account_id:
            raise ValueError(
                "Financial Event belongs to another account."
            )

        if self.contains(event.id):
            raise ValueError(
                "Financial Event already registered."
            )

        self._events.append(event)

        self._events.sort(key=lambda e: (e.occurred_at, e.registered_at, e.id))

        self.add_domain_event(
            FinancialEventRegistered(
                ledger_id=self.id,
                account_id=self.account_id,
                financial_event_id=event.id,
                event_type=event.event_type,
            )
        )

    def contains(self, event_id: UUID) -> bool:
        """
        Returns True if the event already exists.
        """

        return any(event.id == event_id for event in self._events)

    @property
    def events(self) -> tuple[FinancialEvent, ...]:
        """
        Returns an immutable view of the event stream.
        """

        return tuple(self._events)

    @property
    def size(self) -> int:
        """
        Number of registered events.
        """

        return len(self._events)

    def replay(self) -> tuple[FinancialEvent, ...]:
        """
        Returns the ordered event stream.

        Business Engines consume this stream.
        """

        return self.events