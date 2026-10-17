"""Audit-only commerce taxonomy, buyable-security selection and L3 policy."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from income_analytics.application.magic_formula_investable_universe import POLICY

COMMERCE_CATEGORIES = frozenset(
    {
        "TRADITIONAL_RETAIL",
        "WHOLESALE",
        "CASH_AND_CARRY",
        "DISTRIBUTION",
        "COMMERCE_ADJACENT",
        "MIXED_COMMERCE",
        "UNCERTAIN",
    }
)
CONFIDENCE_LEVELS = frozenset({"HIGH", "MEDIUM", "LOW"})
SECURITY_POLICIES = frozenset({"S0", "S1", "S2", "S3", "S4"})


@dataclass(frozen=True, slots=True)
class SecuritySelection:
    status: str
    selected_security: dict | None
    reason: str
    policy_id: str
    criteria: tuple[str, ...]


def commerce_policy_decision(
    category: str,
    confidence: str,
    evidence_source: str | None,
    evidence_reference: str | None,
    *,
    policy=POLICY,
) -> dict:
    """Evidence-backed taxonomy result; uncertain/low confidence remains REVIEW."""
    if category not in COMMERCE_CATEGORIES:
        raise ValueError(f"UNKNOWN_COMMERCE_CATEGORY:{category}")
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError(f"UNKNOWN_CLASSIFICATION_CONFIDENCE:{confidence}")
    if not evidence_source or not evidence_reference or confidence == "LOW":
        return {
            "status": "POLICY_REVIEW",
            "reason": "EVIDENCE_MISSING_OR_LOW_CONFIDENCE",
            "rule": "REFINED_COMMERCE_EVIDENCE_REQUIRED",
        }
    if category in policy.commerce_policy_excluded_categories:
        return {
            "status": "INELIGIBLE_USER_POLICY",
            "reason": "TRADITIONAL_RETAIL_EXCLUSION",
            "rule": "EXCLUDE_TRADITIONAL_RETAIL",
        }
    if category in policy.commerce_policy_review_categories:
        return {
            "status": "POLICY_REVIEW",
            "reason": f"{category}_REQUIRES_POLICY_REVIEW",
            "rule": "COMMERCE_REVIEW_CATEGORY",
        }
    return {
        "status": "PASS",
        "reason": None,
        "rule": f"{category}_PASSES_RETAIL_ONLY_EXCLUSION",
    }


def _metric(candidate: dict, key: str) -> Decimal | None:
    value = candidate.get(key)
    if value is None:
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _stable_identity_key(candidate: dict) -> tuple[str, str, str]:
    return (
        str(candidate.get("isin") or "").upper(),
        str(candidate.get("ticker") or "").upper(),
        str(candidate.get("security_id") or "").upper(),
    )


def _order_key(candidate: dict, policy_id: str) -> tuple:
    ratio = _metric(candidate, "traded_days_ratio_30d")
    volume = _metric(candidate, "median_daily_financial_volume_30d")
    # Descending economic metrics; ascending stable identifier only after ties.
    if policy_id == "S1":
        return (-ratio, *_stable_identity_key(candidate))
    if policy_id == "S2":
        return (-volume, -ratio, *_stable_identity_key(candidate))
    if policy_id == "S3":
        return (-volume, -ratio, *_stable_identity_key(candidate))
    if policy_id == "S4":
        return (-ratio, -volume, *_stable_identity_key(candidate))
    raise ValueError(f"UNORDERED_SECURITY_POLICY:{policy_id}")


def select_buyable_security(
    candidates: Iterable[dict], policy_id: str = "S4", *, policy=POLICY
) -> SecuritySelection:
    """Select by execution evidence only; price availability is never inspected."""
    if policy_id not in SECURITY_POLICIES:
        raise ValueError(f"UNKNOWN_SECURITY_POLICY:{policy_id}")
    criteria = {
        "S1": ("valid_listing", "traded_days_ratio_30d", "stable_security_identity_key"),
        "S2": (
            "valid_listing",
            "median_daily_financial_volume_30d",
            "traded_days_ratio_30d",
            "stable_security_identity_key",
        ),
        "S3": (
            "valid_listing",
            "liquidity_pass_l3",
            "median_daily_financial_volume_30d",
            "stable_security_identity_key",
        ),
        "S4": (
            "valid_listing",
            "traded_days_ratio_30d",
            "median_daily_financial_volume_30d",
            "stable_security_identity_key",
        ),
    }
    if policy_id == "S0":
        return SecuritySelection(
            "BUYABLE_SECURITY_REVIEW", None, "CURRENT_SECURITY_POLICY_UNDEFINED", "S0", ()
        )

    valid = [
        candidate
        for candidate in candidates
        if candidate.get("valid_listing") is True and candidate.get("market_type") == "010"
    ]
    if not valid:
        return SecuritySelection(
            "BUYABLE_SECURITY_REVIEW",
            None,
            "NO_VALID_LISTED_SECURITY",
            policy_id,
            criteria[policy_id],
        )
    if any(
        not candidate.get("liquidity_evidence_complete")
        or _metric(candidate, "traded_days_ratio_30d") is None
        or _metric(candidate, "median_daily_financial_volume_30d") is None
        for candidate in valid
    ):
        return SecuritySelection(
            "BUYABLE_SECURITY_REVIEW",
            None,
            "VALID_SECURITY_LIQUIDITY_COMPARISON_INCOMPLETE",
            policy_id,
            criteria[policy_id],
        )

    if policy_id == "S3":
        passing = [
            candidate
            for candidate in valid
            if _metric(candidate, "traded_days_ratio_30d") >= policy.liquidity_policy_minimum
        ]
        if not passing:
            best_failed = sorted(valid, key=lambda candidate: _order_key(candidate, "S4"))[0]
            return SecuritySelection(
                "LIQUIDITY_FAIL",
                best_failed,
                "NO_VALID_CLASS_PASSES_L3",
                policy_id,
                criteria[policy_id],
            )
        selected = sorted(passing, key=lambda candidate: _order_key(candidate, "S3"))[0]
    else:
        selected = sorted(valid, key=lambda candidate: _order_key(candidate, policy_id))[0]
    return SecuritySelection(
        "RESOLVED",
        selected,
        f"SELECTED_BY_{policy_id}_EXECUTION_RULE",
        policy_id,
        criteria[policy_id],
    )


def selected_security_liquidity(selection: SecuritySelection, *, policy=POLICY) -> str:
    if selection.status == "LIQUIDITY_FAIL":
        return "LIQUIDITY_FAIL"
    if selection.status != "RESOLVED" or selection.selected_security is None:
        return "LIQUIDITY_REVIEW"
    ratio = _metric(selection.selected_security, "traded_days_ratio_30d")
    if ratio is None or not selection.selected_security.get("liquidity_evidence_complete"):
        return "LIQUIDITY_REVIEW"
    return "LIQUIDITY_PASS" if ratio >= policy.liquidity_policy_minimum else "LIQUIDITY_FAIL"


def final_eligibility_state(
    *,
    structural: str,
    user_policy: str,
    security_selection: SecuritySelection,
    data_complete: bool,
) -> str:
    if structural == "INELIGIBLE_STRUCTURAL":
        return "INELIGIBLE_STRUCTURAL"
    if user_policy == "INELIGIBLE_USER_POLICY":
        return "INELIGIBLE_USER_POLICY"
    if user_policy == "POLICY_REVIEW":
        return "POLICY_REVIEW"
    if user_policy != "PASS":
        return "POLICY_REVIEW"
    if security_selection.status == "BUYABLE_SECURITY_REVIEW":
        return "BUYABLE_SECURITY_REVIEW"
    liquidity = selected_security_liquidity(security_selection)
    if liquidity == "LIQUIDITY_FAIL":
        return "LIQUIDITY_FAIL"
    if liquidity == "LIQUIDITY_REVIEW":
        return "LIQUIDITY_REVIEW"
    return "ELIGIBLE_COMPLETE" if data_complete else "ELIGIBLE_DATA_BLOCKED"


def coverage_metrics(rows: Iterable[dict]) -> dict:
    """Separate confirmed, excluded and review states without hiding REVIEW."""
    values = list(rows)
    complete = sum(row["final_status"] == "ELIGIBLE_COMPLETE" for row in values)
    blocked = sum(row["final_status"] == "ELIGIBLE_DATA_BLOCKED" for row in values)
    confirmed = complete + blocked
    review = sum(
        row["final_status"]
        in {
            "POLICY_REVIEW",
            "BUYABLE_SECURITY_REVIEW",
            "LIQUIDITY_REVIEW",
            "IDENTITY_UNRESOLVED",
        }
        for row in values
    )
    ineligible = sum(
        row["final_status"]
        in {
            "INELIGIBLE_STRUCTURAL",
            "INELIGIBLE_USER_POLICY",
            "LIQUIDITY_FAIL",
        }
        for row in values
    )
    potential = confirmed + review
    return {
        "confirmed_eligible": confirmed,
        "confirmed_complete": complete,
        "confirmed_blocked": blocked,
        "confirmed_ineligible": ineligible,
        "review_required": review,
        "potential_eligible_denominator": potential,
        "confirmed_eligible_coverage": Decimal(100) * complete / confirmed
        if confirmed
        else Decimal(0),
        "conservative_coverage": Decimal(100) * complete / potential if potential else Decimal(0),
        "status_sum": len(values),
    }
