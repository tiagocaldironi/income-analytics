from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from income_analytics.domain.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class LedgerCreated(DomainEvent):
    """
    Raised when a Financial Ledger is created.
    """

    ledger_id: UUID
    account_id: UUID