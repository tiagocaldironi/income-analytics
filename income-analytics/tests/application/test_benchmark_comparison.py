from datetime import date
from decimal import Decimal

from income_analytics.application.benchmark_comparison import build_performance_comparison
from income_analytics.application.benchmark_data import BenchmarkObservation
from income_analytics.domain.benchmark_rate import BenchmarkRate
from income_analytics.domain.read_models.performance_projection import PerformanceProjection
from income_analytics.domain.value_objects.money import Money


def projection(
    start: date, end: date, twr: Decimal | None = Decimal("0.08")
) -> PerformanceProjection:
    return PerformanceProjection(
        start_date=start,
        end_date=end,
        beginning_equity=Money(Decimal("100")),
        ending_equity=Money(Decimal("108")) if twr is not None else None,
        total_contributions=Money.zero(),
        total_withdrawals=Money.zero(),
        twr=twr,
        xirr=None,
        coverage_ratio=Decimal("1"),
        performance_status="AVAILABLE",
    )


def test_comparison_composes_periodic_rates_and_normalizes_series_at_zero() -> None:
    start, first, end = date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)
    observations = {
        "IBOV": (
            BenchmarkObservation(
                benchmark="IBOV",
                effective_date=first,
                value=Decimal("100"),
                nature="INDEX_LEVEL",
                source="b3",
            ),
            BenchmarkObservation(
                benchmark="IBOV",
                effective_date=end,
                value=Decimal("110"),
                nature="INDEX_LEVEL",
                source="b3",
            ),
        ),
        "IPCA": (
            BenchmarkObservation(
                benchmark="IPCA",
                effective_date=first,
                value=Decimal("0.01"),
                nature="INFLATION_RATE",
                source="bcb",
            ),
            BenchmarkObservation(
                benchmark="IPCA",
                effective_date=end,
                value=Decimal("0.02"),
                nature="INFLATION_RATE",
                source="bcb",
            ),
        ),
    }
    result = build_performance_comparison(
        start_date=start,
        end_date=end,
        rates=(
            BenchmarkRate(name="CDI", effective_date=first, return_percentage=Decimal("0.01")),
            BenchmarkRate(name="CDI", effective_date=end, return_percentage=Decimal("0.01")),
        ),
        observations=observations,
        performance_at=lambda low, high: projection(low, high),
    )

    by_code = {item["code"]: item for item in result["benchmarks"]}
    assert by_code["CDI"]["return"] == Decimal("0.0201")
    assert by_code["IBOV"]["return"] == Decimal("0.1")
    assert by_code["IPCA"]["return"] == Decimal("0.0302")
    assert by_code["IBOV"]["excess_return"] == Decimal("-0.02")
    assert result["series"][0]["portfolio"] == 0
    assert result["series"][0]["cdi"] == 0
    assert result["coverage"] == {"ratio": Decimal("1"), "status": "GOOD"}


def test_comparison_keeps_an_unavailable_benchmark_independent() -> None:
    end = date(2026, 1, 31)
    result = build_performance_comparison(
        start_date=date(2026, 1, 1),
        end_date=end,
        rates=(),
        observations={},
        performance_at=lambda low, high: projection(low, high),
    )

    by_code = {item["code"]: item for item in result["benchmarks"]}
    assert result["portfolio"]["return"] == Decimal("0.08")
    assert by_code["IFIX"]["status"] == "UNAVAILABLE"
    assert by_code["IFIX"]["return"] is None


def test_stale_index_is_labeled_without_invalidating_portfolio() -> None:
    start, last = date(2026, 1, 1), date(2026, 1, 2)
    result = build_performance_comparison(
        start_date=start,
        end_date=date(2026, 1, 31),
        rates=(),
        observations={
            "IBOV": (
                BenchmarkObservation(
                    benchmark="IBOV",
                    effective_date=last,
                    value=Decimal("100"),
                    nature="INDEX_LEVEL",
                    source="b3",
                ),
            )
        },
        performance_at=lambda low, high: projection(low, high),
    )

    by_code = {item["code"]: item for item in result["benchmarks"]}
    assert result["portfolio"]["return"] == Decimal("0.08")
    assert by_code["IBOV"]["status"] == "STALE"
    assert by_code["IBOV"]["last_observation"] == last
