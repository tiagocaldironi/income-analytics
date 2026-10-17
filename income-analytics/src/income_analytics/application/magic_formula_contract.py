"""Canonical Magic Formula identity, evidence and eligibility contracts.

Resolution is a projection of persisted snapshot/QA evidence, never an input flag.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from uuid import UUID

from income_analytics.application.cvm_magic_formula_normalization import ADAPTER_VERSION

METHODOLOGY_VERSION = "MAGIC_FORMULA_STOCKS_V1"
GOLDEN_SCHEMA_VERSION = "MAGIC_FORMULA_GOLDEN_V2"
DIMENSIONS = (
    "accounting",
    "security",
    "capital",
    "market",
    "market_cap",
    "derived",
    "lineage",
    "snapshot_readback",
)
FINANCIAL_METRICS = (
    "ebit",
    "cash_and_equivalents",
    "financial_debt_short_term",
    "financial_debt_long_term",
    "operating_current_assets",
    "operating_current_liabilities",
    "net_fixed_assets",
    "market_cap",
    "net_debt",
    "net_working_capital",
    "invested_capital",
    "enterprise_value",
    "earnings_yield",
    "return_on_capital",
)


class ValidationStatus(StrEnum):
    NOT_VALIDATED = "NOT_VALIDATED"
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf8")
    ).hexdigest()


def snapshot_digest(snapshot: dict) -> str:
    """Validation state may evolve; financial artifact and identity may not."""
    return digest(
        {
            key: snapshot[key]
            for key in (
                "id",
                "issuer_id",
                "financial_reference_date",
                "market_reference_date",
                "adapter_version",
                "methodology_version",
                "statement_type",
                "statement_scope",
                "normalization_status",
                "metrics_json",
                "lineage_json",
            )
        }
    )


def canonical_identity(cvm_code: str, cnpj: str) -> tuple[str, str]:
    if not cvm_code.isdigit():
        raise ValueError("INVALID_CVM_CODE")
    code = str(int(cvm_code)).zfill(6)
    tax_id = "".join(c for c in cnpj if c.isdigit())
    if int(code) <= 0 or len(tax_id) != 14:
        raise ValueError("INVALID_ISSUER_IDENTITY")
    return code, tax_id


def golden_contract_errors(fixture: dict) -> tuple[str, ...]:
    if not isinstance(fixture, dict):
        return ("MALFORMED_GOLDEN",)
    errors = []
    if fixture.get("schema_version") != GOLDEN_SCHEMA_VERSION:
        errors.append("GOLDEN_SCHEMA_MISMATCH")
    if fixture.get("methodology_version") != METHODOLOGY_VERSION:
        errors.append("METHODOLOGY_VERSION_MISMATCH")
    if fixture.get("fixture_status") != "READY_FOR_VALIDATION":
        errors.append("GOLDEN_NOT_READY")
    issuer = fixture.get("issuer", {})
    if not isinstance(issuer, dict):
        issuer = {}
    try:
        UUID(issuer["issuer_id"])
        canonical_identity(issuer["cvm_code"], issuer["cnpj"])
    except (KeyError, ValueError, TypeError, AttributeError):
        errors.append("INVALID_ISSUER_IDENTITY")
    reference = fixture.get("reference", {})
    if not isinstance(reference, dict):
        reference = {}
    try:
        date.fromisoformat(fixture["reference_date"])
        if fixture["reference_date"] != reference["financial_reference_date"]:
            errors.append("REFERENCE_DATE_MISMATCH")
    except (KeyError, ValueError, TypeError):
        errors.append("REFERENCE_DATE_MISMATCH")
    if reference.get("adapter_version") != ADAPTER_VERSION:
        errors.append("ADAPTER_VERSION_MISMATCH")
    for section in ("accounting", "security", "capital", "prices", "expected"):
        if not fixture.get(section):
            errors.append(f"MISSING_{section.upper()}")
    return tuple(errors)


@dataclass(frozen=True)
class DimensionDecision:
    dimension: str
    status: ValidationStatus
    evidence: tuple[str, ...]


def final_qa_status(dimensions: tuple[DimensionDecision, ...]) -> ValidationStatus:
    if len(dimensions) != len(DIMENSIONS) or {d.dimension for d in dimensions} != set(DIMENSIONS):
        return ValidationStatus.REVIEW_REQUIRED
    if any(d.status == ValidationStatus.FAIL for d in dimensions):
        return ValidationStatus.FAIL
    if any(d.status != ValidationStatus.PASS or not d.evidence for d in dimensions):
        return ValidationStatus.REVIEW_REQUIRED
    return ValidationStatus.PASS


@dataclass(frozen=True)
class EligibilityDecision:
    eligible: bool
    issuer_status: str
    reasons: tuple[str, ...]
    snapshot_id: str | None
    qa_decision_id: str | None


def is_ranking_eligible(
    *,
    issuer_id: str,
    reference_date: str,
    snapshot: dict | None,
    qa: dict | None,
    fixture: dict | None,
) -> EligibilityDecision:
    """The sole resolution/eligibility policy, called with repository read-back."""
    reasons = []
    if fixture is None:
        reasons.append("MISSING_GOLDEN")
    elif golden_contract_errors(fixture):
        reasons.append("INVALID_GOLDEN")
    if snapshot is None:
        reasons.append("MISSING_VALIDATED_SNAPSHOT")
    if qa is None:
        reasons.append("MISSING_FORMAL_QA")
    if snapshot is not None:
        if snapshot.get("issuer_id") != issuer_id:
            reasons.append("ISSUER_MISMATCH")
        if snapshot.get("validation_status") != ValidationStatus.PASS:
            reasons.append("SNAPSHOT_NOT_VALIDATED")
        if snapshot.get("adapter_version") != ADAPTER_VERSION:
            reasons.append("ADAPTER_VERSION_MISMATCH")
        if snapshot.get("methodology_version") != METHODOLOGY_VERSION:
            reasons.append("METHODOLOGY_VERSION_MISMATCH")
        try:
            date.fromisoformat(reference_date)
            if any(
                snapshot.get(k) != reference_date
                for k in (
                    "financial_reference_date",
                    "market_reference_date",
                )
            ):
                reasons.append("REFERENCE_DATE_MISMATCH")
        except (ValueError, TypeError):
            reasons.append("REFERENCE_DATE_MISMATCH")
        if qa is not None:
            try:
                fingerprint = snapshot_digest(snapshot)
            except (KeyError, TypeError, ValueError):
                fingerprint = None
            if (
                any(
                    qa.get(q) != snapshot.get(s)
                    for q, s in (
                        ("snapshot_id", "id"),
                        ("issuer_id", "issuer_id"),
                        ("adapter_version", "adapter_version"),
                        ("reference_date", "financial_reference_date"),
                    )
                )
                or fingerprint is None
                or qa.get("snapshot_digest") != fingerprint
            ):
                reasons.append("QA_SNAPSHOT_MISMATCH")
            try:
                dims = tuple(
                    DimensionDecision(
                        d["dimension"],
                        ValidationStatus(d["status"]),
                        tuple(d["evidence"]),
                    )
                    for d in qa.get("dimensions", [])
                )
            except (KeyError, TypeError, ValueError):
                dims = ()
            if qa.get("final_status") != "PASS" or final_qa_status(dims) != ValidationStatus.PASS:
                reasons.append("QA_NOT_PASS")
            if fixture is None or qa.get("fixture_hash") != digest(fixture):
                reasons.append("QA_GOLDEN_MISMATCH")
        if fixture is not None and (
            fixture.get("issuer", {}).get("issuer_id") != issuer_id
            or fixture.get("reference_date") != snapshot.get("financial_reference_date")
        ):
            reasons.append("GOLDEN_SNAPSHOT_MISMATCH")
    # Resolution describes validated evidence, not economic attractiveness.
    resolved = not reasons
    if not resolved:
        reasons.append("ISSUER_NOT_RESOLVED")
    if snapshot is not None:
        try:
            values = json.loads(snapshot["metrics_json"])
            amounts = {k: Decimal(str(values[k])) for k in FINANCIAL_METRICS}
            valid = all(v.is_finite() for v in amounts.values()) and all(
                amounts[k] > 0
                for k in (
                    "ebit",
                    "market_cap",
                    "enterprise_value",
                    "invested_capital",
                    "earnings_yield",
                    "return_on_capital",
                )
            )
            valid = valid and snapshot.get("normalization_status") == "VALID"
            valid = valid and snapshot.get("statement_scope") == "CONSOLIDATED"
            # ITR is not annual EBIT/TTM under the approved methodology.
            valid = valid and snapshot.get("statement_type") == "DFP"
        except (KeyError, ValueError, TypeError, InvalidOperation):
            valid = False
        if not valid:
            reasons.append("FINANCIAL_INELIGIBILITY")
    return EligibilityDecision(
        not reasons,
        "RESOLVED" if resolved else "NOT_RESOLVED",
        tuple(dict.fromkeys(reasons)),
        snapshot.get("id") if snapshot else None,
        qa.get("id") if qa else None,
    )


def canonicalize_golden(fixture: dict, issuer: dict) -> dict:
    """Version legacy envelopes without changing expected amounts or raw locators."""
    from copy import deepcopy

    result = deepcopy(fixture)
    if result.get("schema_version") == GOLDEN_SCHEMA_VERSION:
        if result["issuer"]["issuer_id"] != issuer["issuer_id"]:
            raise ValueError("GOLDEN_ISSUER_MISMATCH")
        return result
    code, tax_id = canonical_identity(issuer["cvm_code"], issuer["cnpj"])
    if str(int(result["issuer"]["cvm_code"])).zfill(6) != code:
        raise ValueError("GOLDEN_CVM_MISMATCH")
    result["legacy_fixture_hash"] = digest(fixture)
    result["legacy_issuer_id"] = result["issuer"]["issuer_id"]
    result["issuer"] = {
        k: issuer[k]
        for k in (
            "issuer_id",
            "cvm_code",
            "cnpj",
            "display_name",
            "slug",
        )
    }
    result["schema_version"] = GOLDEN_SCHEMA_VERSION
    result["methodology_version"] = METHODOLOGY_VERSION
    result["reference_date"] = result["reference"]["financial_reference_date"]
    result["fixture_status"] = result.pop("evidence_status", "READY_FOR_VALIDATION")
    result["security"] = []
    for cap in result["capital"]["securities"]:
        cap["legacy_issuer_id"] = cap["issuer_id"]
        cap["issuer_id"] = issuer["issuer_id"]
        security = {
            k: cap.get(k)
            for k in (
                "issuer_id",
                "security_id",
                "ticker",
                "share_class",
                "fca_source",
                "fca_source_reference",
                "fca_form_id",
                "valid_from",
                "valid_to",
            )
        }
        security["cnpj"] = tax_id
        result["security"].append(security)
    return result
