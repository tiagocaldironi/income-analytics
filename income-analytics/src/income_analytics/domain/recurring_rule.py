"""A persisted instruction to create future financial events when due."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from income_analytics.domain.enums.financial_event_type import FinancialEventType


class RecurrenceFrequency(StrEnum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


@dataclass(frozen=True, slots=True, kw_only=True)
class RecurringRule:
    event_type: FinancialEventType
    amount: Decimal
    next_execution_date: date
    frequency: RecurrenceFrequency
    asset_id: UUID | None = None
    end_execution_date: date | None = None
    active: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.event_type not in {
            FinancialEventType.DEPOSIT,
            FinancialEventType.WITHDRAWAL,
            FinancialEventType.DIVIDEND,
        }:
            raise ValueError("Only cash flows and dividends may be recurring.")
        if self.amount <= 0:
            raise ValueError("Recurring amount must be greater than zero.")
        if self.event_type is FinancialEventType.DIVIDEND and self.asset_id is None:
            raise ValueError("Recurring dividends require an asset.")
        if self.event_type is not FinancialEventType.DIVIDEND and self.asset_id is not None:
            raise ValueError("External recurring flows cannot have an asset.")

    def advance(self) -> "RecurringRule":
        months = {
            RecurrenceFrequency.MONTHLY: 1,
            RecurrenceFrequency.QUARTERLY: 3,
            RecurrenceFrequency.YEARLY: 12,
        }[self.frequency]
        year = self.next_execution_date.year + (self.next_execution_date.month - 1 + months) // 12
        month = (self.next_execution_date.month - 1 + months) % 12 + 1
        from calendar import monthrange

        day = min(self.next_execution_date.day, monthrange(year, month)[1])
        next_execution_date = date(year, month, day)
        return RecurringRule(
            id=self.id,
            event_type=self.event_type,
            amount=self.amount,
            asset_id=self.asset_id,
            frequency=self.frequency,
            next_execution_date=next_execution_date,
            end_execution_date=self.end_execution_date,
            active=self.active
            and (self.end_execution_date is None or next_execution_date <= self.end_execution_date),
        )
