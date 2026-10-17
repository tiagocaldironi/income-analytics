from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class FinancialEventRegistered(DomainEvent):
    ledger_id: UUID
    account_id: UUID
    financial_event_id: UUID
    event_type: FinancialEventType
