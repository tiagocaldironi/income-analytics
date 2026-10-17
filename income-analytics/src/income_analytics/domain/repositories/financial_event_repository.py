"""Financial-event persistence contract."""

from typing import Protocol

from income_analytics.domain.entities.financial_event import FinancialEvent


class FinancialEventRepository(Protocol):
    def save(self, event: FinancialEvent) -> None: ...

    def list(self) -> tuple[FinancialEvent, ...]: ...
