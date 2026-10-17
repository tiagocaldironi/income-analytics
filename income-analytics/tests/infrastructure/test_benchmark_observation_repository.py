from datetime import date
from decimal import Decimal

from income_analytics.application.benchmark_data import BenchmarkObservation
from income_analytics.infrastructure.sqlite_repositories import SqliteBenchmarkObservationRepository


def test_benchmark_observation_upsert_is_idempotent_for_same_date() -> None:
    repository = SqliteBenchmarkObservationRepository()
    observation = BenchmarkObservation(
        benchmark="TESTIDEMPOTENT",
        effective_date=date(2026, 1, 2),
        value=Decimal("100"),
        nature="INDEX_LEVEL",
        source="b3",
    )
    corrected = BenchmarkObservation(
        benchmark="TESTIDEMPOTENT",
        effective_date=date(2026, 1, 2),
        value=Decimal("101"),
        nature="INDEX_LEVEL",
        source="b3",
    )

    repository.save(observation)
    repository.save(corrected)

    saved = repository.list("TESTIDEMPOTENT")
    assert len(saved) == 1
    assert saved[0].value == Decimal("101")
