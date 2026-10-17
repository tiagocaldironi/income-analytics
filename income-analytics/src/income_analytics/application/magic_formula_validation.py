"""Explicit validation gate for normalized Magic Formula fundamentals."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum


class CompanyValidationStatus(StrEnum):
    NOT_VALIDATED = "NOT_VALIDATED"
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class CompanyNormalizationValidation:
    issuer_id: str
    reference_date: str
    adapter_version: str
    metric: str
    expected_value: Decimal
    actual_value: Decimal
    difference: Decimal
    status: CompanyValidationStatus
    notes: str | None
    validated_at: datetime

    @classmethod
    def compare(
        cls,
        *,
        issuer_id: str,
        reference_date: str,
        adapter_version: str,
        metric: str,
        expected_value: Decimal,
        actual_value: Decimal,
        tolerance: Decimal = Decimal("0"),
        notes: str | None = None,
    ) -> "CompanyNormalizationValidation":
        difference = actual_value - expected_value
        status = (
            CompanyValidationStatus.PASS
            if abs(difference) <= tolerance
            else CompanyValidationStatus.FAIL
        )
        return cls(
            issuer_id,
            reference_date,
            adapter_version,
            metric,
            expected_value,
            actual_value,
            difference,
            status,
            notes,
            datetime.now(UTC),
        )
