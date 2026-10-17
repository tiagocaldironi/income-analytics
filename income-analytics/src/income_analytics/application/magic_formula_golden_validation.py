"""Independent expected-vs-snapshot validation for Magic Formula evidence."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class GoldenMetricStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class GoldenMetricComparison:
    metric: str
    expected: Decimal
    actual: Decimal | None
    difference: Decimal | None
    status: GoldenMetricStatus
    evidence: str


class IndependentGoldenValidator:
    """Compares externally reconstructed Decimal expecteds to persisted metrics."""

    @staticmethod
    def compare(
        *, expected: dict[str, Decimal], actual: dict[str, object], evidence: dict[str, str]
    ) -> tuple[GoldenMetricComparison, ...]:
        comparisons = []
        for metric, value in expected.items():
            raw_actual = actual.get(metric)
            actual_value = Decimal(str(raw_actual)) if raw_actual is not None else None
            difference = None if actual_value is None else actual_value - value
            comparisons.append(
                GoldenMetricComparison(
                    metric,
                    value,
                    actual_value,
                    difference,
                    GoldenMetricStatus.PASS if difference == Decimal("0") else GoldenMetricStatus.FAIL,
                    evidence[metric],
                )
            )
        return tuple(comparisons)
