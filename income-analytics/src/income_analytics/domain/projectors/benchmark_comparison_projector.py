"""Project a compounded benchmark return without changing portfolio methodology."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from income_analytics.domain.benchmark_rate import BenchmarkRate
from income_analytics.domain.read_models.benchmark_comparison_projection import (
    BenchmarkComparisonProjection,
)


class BenchmarkComparisonProjector:
    @staticmethod
    def project(
        *,
        portfolio_twr: Decimal | None,
        rates: tuple[BenchmarkRate, ...],
        name: str,
        start_date: date,
        end_date: date,
    ) -> BenchmarkComparisonProjection:
        selected = tuple(
            rate
            for rate in rates
            if rate.name.upper() == name.upper() and start_date <= rate.effective_date <= end_date
        )
        if portfolio_twr is None:
            return BenchmarkComparisonProjection(
                start_date=start_date, end_date=end_date, benchmark_name=name,
                portfolio_twr=None, benchmark_return=None, observed_rates=len(selected),
                unavailable_reason="TWR indisponível para o período selecionado.",
            )
        if not selected:
            return BenchmarkComparisonProjection(
                start_date=start_date, end_date=end_date, benchmark_name=name,
                portfolio_twr=portfolio_twr, benchmark_return=None, observed_rates=0,
                unavailable_reason=f"Não há observações de {name.upper()} no período selecionado.",
            )
        compounded = Decimal("1")
        for rate in selected:
            compounded *= Decimal("1") + rate.return_percentage
        return BenchmarkComparisonProjection(
            start_date=start_date, end_date=end_date, benchmark_name=name,
            portfolio_twr=portfolio_twr, benchmark_return=compounded - Decimal("1"),
            observed_rates=len(selected),
        )
