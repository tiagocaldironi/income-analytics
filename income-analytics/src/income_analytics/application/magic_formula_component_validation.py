"""Strict component-level QA for independently-built Magic Formula goldens."""
# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class ComponentValidationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class ComponentValidation:
    metric: str
    expected: Decimal | None
    actual: Decimal | None
    difference: Decimal | None
    status: ComponentValidationStatus
    evidence_reference: str | None


@dataclass(frozen=True, slots=True)
class ComponentValidationResult:
    comparisons: tuple[ComponentValidation, ...]
    status: ComponentValidationStatus


class MagicFormulaComponentValidator:
    """Validate fixture completeness and snapshot values without recalculation."""

    _metric_keys = (
        "ebit",
        "cash_and_equivalents",
        "financial_debt_short_term",
        "financial_debt_long_term",
        "financial_debt_total",
        "operating_current_assets",
        "operating_current_liabilities",
        "net_working_capital",
        "net_fixed_assets",
        "invested_capital",
        "net_debt",
        "market_cap",
        "enterprise_value",
        "earnings_yield",
        "return_on_capital",
    )

    def validate(
        self,
        *,
        fixture: dict[str, object],
        snapshot_metrics: dict[str, object] | None,
        snapshot_lineage: list[dict[str, object]] | None,
    ) -> ComponentValidationResult:
        if snapshot_metrics is None:
            return ComponentValidationResult(
                (
                    ComponentValidation(
                        "snapshot_readback", None, None, None, ComponentValidationStatus.FAIL, None
                    ),
                ),
                ComponentValidationStatus.FAIL,
            )
        expected = fixture.get("expected")
        accounting = fixture.get("accounting")
        if (
            not isinstance(expected, dict)
            or not isinstance(accounting, dict)
            or not fixture.get("lineage_complete")
        ):
            return ComponentValidationResult(
                (
                    ComponentValidation(
                        "fixture_completeness",
                        None,
                        None,
                        None,
                        ComponentValidationStatus.REVIEW_REQUIRED,
                        None,
                    ),
                ),
                ComponentValidationStatus.REVIEW_REQUIRED,
            )
        comparisons = [
            self._compare(
                metric,
                expected.get(metric),
                self._actual_metric(metric, snapshot_metrics),
                None,
            )
            for metric in self._metric_keys
        ]
        comparisons.extend(self._lineage_checks(accounting, snapshot_lineage or []))
        overall = (
            ComponentValidationStatus.FAIL
            if any(item.status is ComponentValidationStatus.FAIL for item in comparisons)
            else ComponentValidationStatus.REVIEW_REQUIRED
            if any(item.status is ComponentValidationStatus.REVIEW_REQUIRED for item in comparisons)
            else ComponentValidationStatus.PASS
        )
        return ComponentValidationResult(tuple(comparisons), overall)

    @staticmethod
    def _actual_metric(metric: str, values: dict[str, object]) -> object:
        if metric == "financial_debt_total" and metric not in values:
            return Decimal(str(values["financial_debt_short_term"])) + Decimal(
                str(values["financial_debt_long_term"])
            )
        return values.get(metric)

    @staticmethod
    def _compare(
        metric: str, expected: object, actual: object, evidence: str | None
    ) -> ComponentValidation:
        if expected is None or actual is None:
            return ComponentValidation(
                metric,
                None if expected is None else Decimal(str(expected)),
                None if actual is None else Decimal(str(actual)),
                None,
                ComponentValidationStatus.FAIL,
                evidence,
            )
        wanted, found = Decimal(str(expected)), Decimal(str(actual))
        return ComponentValidation(
            metric,
            wanted,
            found,
            found - wanted,
            ComponentValidationStatus.PASS if wanted == found else ComponentValidationStatus.FAIL,
            evidence,
        )

    @staticmethod
    def _lineage_checks(
        accounting: dict[str, object], lineage: list[dict[str, object]]
    ) -> list[ComponentValidation]:
        actual_by_key = {
            (str(item.get("metric")), str(item.get("account_code"))): item
            for item in lineage
            if isinstance(item, dict)
        }
        checks: list[ComponentValidation] = []
        for metric, evidence in accounting.items():
            if not isinstance(evidence, dict):
                continue
            for component in evidence.get("components", []):
                if not isinstance(component, dict):
                    continue
                key = (metric, str(component.get("account_code")))
                actual = actual_by_key.get(key)
                reference = str(component.get("source_reference") or "") or None
                if not reference or not component.get("rule_id", evidence.get("rule_id")):
                    checks.append(
                        ComponentValidation(
                            f"lineage:{metric}:{key[1]}",
                            None,
                            None,
                            None,
                            ComponentValidationStatus.REVIEW_REQUIRED,
                            reference,
                        )
                    )
                    continue
                if actual is None:
                    checks.append(
                        ComponentValidation(
                            f"lineage:{metric}:{key[1]}",
                            None,
                            None,
                            None,
                            ComponentValidationStatus.REVIEW_REQUIRED,
                            reference,
                        )
                    )
                    continue
                wanted = Decimal(str(component["normalized_expected_value"]))
                found = Decimal(str(actual.get("normalized_value")))
                checks.append(
                    ComponentValidation(
                        f"lineage:{metric}:{key[1]}",
                        wanted,
                        found,
                        found - wanted,
                        ComponentValidationStatus.PASS
                        if wanted == found
                        else ComponentValidationStatus.FAIL,
                        reference,
                    )
                )
        return checks
