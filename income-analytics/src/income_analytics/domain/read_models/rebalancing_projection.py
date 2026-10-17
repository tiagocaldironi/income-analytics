"""Analytical class-level rebalancing summary."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from income_analytics.domain.read_models.allocation_analysis import PortfolioAllocationAnalysis
from income_analytics.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class RebalancingProjection:
    analysis: PortfolioAllocationAnalysis
    total_excess: Money
    total_deficit: Money

    @classmethod
    def from_analysis(cls, analysis: PortfolioAllocationAnalysis) -> "RebalancingProjection":
        excess = sum(
            (max(item.value_deviation.amount, Decimal("0")) for item in analysis.comparisons),
            Decimal("0"),
        )
        deficit = sum(
            (max(-item.value_deviation.amount, Decimal("0")) for item in analysis.comparisons),
            Decimal("0"),
        )
        return cls(analysis=analysis, total_excess=Money(excess), total_deficit=Money(deficit))

    def contribution_only(self, contribution: Money) -> tuple[tuple[str, Money], ...]:
        """Allocate a simulated contribution across current class deficits only."""
        if not contribution.is_positive:
            raise ValueError("O aporte simulado deve ser maior que zero.")
        deficits = [
            (item.asset_class.value, -item.value_deviation.amount)
            for item in self.analysis.comparisons
            if item.value_deviation.amount < 0
        ]
        total = sum((amount for _, amount in deficits), Decimal("0"))
        if total == 0:
            return ()
        usable = min(contribution.amount, total)
        return tuple((name, Money(usable * amount / total)) for name, amount in deficits)
