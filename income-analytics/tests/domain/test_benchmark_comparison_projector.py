from datetime import date
from decimal import Decimal

from income_analytics.domain.benchmark_rate import BenchmarkRate
from income_analytics.domain.projectors.benchmark_comparison_projector import (
    BenchmarkComparisonProjector,
)


def test_compounds_benchmark_rates_and_compares_with_twr() -> None:
    result = BenchmarkComparisonProjector.project(
        portfolio_twr=Decimal("0.25"),
        rates=(
            BenchmarkRate(
                name="CDI", effective_date=date(2026, 1, 2), return_percentage=Decimal("0.10")
            ),
            BenchmarkRate(
                name="CDI", effective_date=date(2026, 1, 3), return_percentage=Decimal("0.10")
            ),
        ),
        name="CDI",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result.benchmark_return == Decimal("0.2100")
    assert result.difference == Decimal("0.0400")


def test_reports_when_the_selected_benchmark_has_no_observations() -> None:
    result = BenchmarkComparisonProjector.project(
        portfolio_twr=Decimal("0.10"),
        rates=(),
        name="CDI",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result.benchmark_return is None
    assert result.unavailable_reason == "Não há observações de CDI no período selecionado."
