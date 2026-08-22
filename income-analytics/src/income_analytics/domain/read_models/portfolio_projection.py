"""
Read Model representing the projected portfolio.

A PortfolioProjection is built from the Financial Ledger and contains
the consolidated positions of an investment account.
"""

from __future__ import annotations

from dataclasses import dataclass

from income_analytics.domain.read_models.position_projection import (
    PositionProjection,
)
from income_analytics.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioProjection:
    """
    Represents the current projected portfolio.
    """

    positions: tuple[PositionProjection, ...]
    total_invested: Money

    @property
    def position_count(self) -> int:
        """
        Returns the number of projected positions.
        """
        return len(self.positions)

    @property
    def is_empty(self) -> bool:
        """
        Indicates whether the portfolio contains positions.
        """
        return self.position_count == 0