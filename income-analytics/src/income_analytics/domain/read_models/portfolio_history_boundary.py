"""Quality and provenance for the first observable portfolio state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Iterable

from income_analytics.domain.entities.financial_event import FinancialEvent


class OpeningStateStatus(StrEnum):
    """Confidence attached to a reconstructed part of the opening state."""

    CONFIRMED = "CONFIRMED"
    DERIVED = "DERIVED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True, kw_only=True)
class OpeningCapital:
    """The opening state carried across a portfolio history boundary."""

    opening_positions_status: OpeningStateStatus
    opening_cash_status: OpeningStateStatus
    opening_cash: Decimal | None
    opening_equity_status: OpeningStateStatus
    opening_equity: Decimal | None

    @property
    def has_reliable_equity(self) -> bool:
        reliable = {OpeningStateStatus.CONFIRMED, OpeningStateStatus.DERIVED}
        return (
            self.opening_positions_status in reliable
            and self.opening_cash_status in reliable
            and self.opening_equity_status in reliable
            and self.opening_equity is not None
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioHistoryBoundary:
    """The boundary between observed events and an unobserved earlier history.

    This is a read model, not a financial event. In particular, it never creates
    a deposit to balance transactions that predate the available cash ledger.
    """

    boundary_date: date | None
    source: str
    confidence: OpeningStateStatus
    opening_capital: OpeningCapital

    @property
    def opening_positions_status(self) -> OpeningStateStatus:
        return self.opening_capital.opening_positions_status

    @property
    def opening_cash_status(self) -> OpeningStateStatus:
        return self.opening_capital.opening_cash_status

    @property
    def opening_cash(self) -> Decimal | None:
        return self.opening_capital.opening_cash

    @property
    def opening_equity_status(self) -> OpeningStateStatus:
        return self.opening_capital.opening_equity_status

    @property
    def opening_equity(self) -> Decimal | None:
        return self.opening_capital.opening_equity

    @property
    def has_reliable_opening_equity(self) -> bool:
        reliable = {OpeningStateStatus.CONFIRMED, OpeningStateStatus.DERIVED}
        return self.confidence in reliable and self.opening_capital.has_reliable_equity

    def as_payload(self) -> dict[str, object]:
        return {
            "boundary_date": self.boundary_date,
            "source": self.source,
            "confidence": self.confidence.value,
            "opening_positions_status": self.opening_positions_status.value,
            "opening_cash_status": self.opening_cash_status.value,
            "opening_cash": self.opening_cash,
            "opening_equity_status": self.opening_equity_status.value,
            "opening_equity": self.opening_equity,
            "opening_equity_reliable": self.has_reliable_opening_equity,
            "opening_capital": {
                "opening_positions_status": self.opening_positions_status.value,
                "opening_cash_status": self.opening_cash_status.value,
                "opening_cash": self.opening_cash,
                "opening_equity_status": self.opening_equity_status.value,
                "opening_equity": self.opening_equity,
            },
        }

    @classmethod
    def from_observed_events(
        cls, events: Iterable[FinancialEvent]
    ) -> PortfolioHistoryBoundary:
        """Describe available history without claiming its first event is inception."""
        observed = tuple(events)
        if not observed:
            return cls(
                boundary_date=None,
                source="NO_OBSERVED_FINANCIAL_EVENTS",
                confidence=OpeningStateStatus.UNKNOWN,
                opening_capital=OpeningCapital(
                    opening_positions_status=OpeningStateStatus.UNKNOWN,
                    opening_cash_status=OpeningStateStatus.UNKNOWN,
                    opening_cash=None,
                    opening_equity_status=OpeningStateStatus.UNKNOWN,
                    opening_equity=None,
                ),
            )
        return cls(
            boundary_date=min(event.effective_date for event in observed),
            source="FIRST_OBSERVED_FINANCIAL_EVENT",
            confidence=OpeningStateStatus.PARTIAL,
            opening_capital=OpeningCapital(
                opening_positions_status=OpeningStateStatus.PARTIAL,
                opening_cash_status=OpeningStateStatus.UNKNOWN,
                opening_cash=None,
                opening_equity_status=OpeningStateStatus.PARTIAL,
                opening_equity=None,
            ),
        )

    @classmethod
    def confirmed(
        cls,
        *,
        boundary_date: date,
        source: str,
        opening_cash: Decimal,
        opening_equity: Decimal,
    ) -> PortfolioHistoryBoundary:
        """Build a boundary from an explicitly supplied, trusted opening state."""
        return cls(
            boundary_date=boundary_date,
            source=source,
            confidence=OpeningStateStatus.CONFIRMED,
            opening_capital=OpeningCapital(
                opening_positions_status=OpeningStateStatus.CONFIRMED,
                opening_cash_status=OpeningStateStatus.CONFIRMED,
                opening_cash=opening_cash,
                opening_equity_status=OpeningStateStatus.CONFIRMED,
                opening_equity=opening_equity,
            ),
        )
