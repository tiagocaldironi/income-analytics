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
    total_cost: Money
    total_realized_result: Money = Money.zero()
    cash: Money = Money.zero()
    income_received: Money = Money.zero()
    total_contributions: Money = Money.zero()
    total_withdrawals: Money = Money.zero()

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

    @property
    def total_market_value(self) -> Money:
        """Return the sum of the marked-to-market values of all positions."""
        return sum((position.market_value for position in self.positions), Money.zero())

    @property
    def total_unrealized_result(self) -> Money:
        """Return the sum of unrealized results for all positions."""
        return sum((position.unrealized_result for position in self.positions), Money.zero())

    @property
    def total_result(self) -> Money:
        """Return the portfolio's realized, unrealized, and income result combined."""
        return self.total_realized_result + self.total_unrealized_result + self.income_received

    @property
    def portfolio_equity(self) -> Money:
        """Return the total portfolio wealth: cash plus marked-to-market positions."""
        return self.cash + self.total_market_value

    @property
    def net_external_flow(self) -> Money:
        """Return capital added by the investor less capital withdrawn."""
        return self.total_contributions - self.total_withdrawals

    @property
    def has_complete_market_data(self) -> bool:
        """Indicate whether every open position has a manually informed market price."""
        return all(
            position.is_empty or position.current_price is not None
            for position in self.positions
        )
