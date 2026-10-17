"""Methodology and user screening preferences for Magic Formula results.

The screening layer is deliberately applied after canonical eligibility and
ranking. It cannot change financial metrics or global ranks.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable


@dataclass(frozen=True, slots=True)
class MagicFormulaMethodologyPolicy:
    """Frozen methodology settings; personal screening is deliberately excluded."""

    policy_id: str = "MF_BR_2027_V1"
    policy_version: str = "V1"
    structural_exclusion_version: str = "MF_BR_FINANCIAL_EXCLUSIONS_V1"
    structural_exclusions: tuple[str, ...] = (
        "BANKS",
        "INSURERS",
        "BROKERS",
        "FINANCIAL_INTERMEDIATION",
        "REAL_ESTATE_CREDIT",
        "LEASING",
        "RECEIVABLES_SECURITIZATION",
    )
    security_selection: str = "S4"
    security_selection_primary_metric: str = "traded_days_ratio_30d"
    security_selection_tie_breaker: str = "median_daily_financial_volume_30d"
    security_selection_final_tie_breaker: str = "stable_security_identity_key"
    market_type: str = "010"
    liquidity_window_sessions: int = 30
    minimum_traded_sessions: int = 15
    liquidity_threshold: str = "0.50"
    minimum_market_cap_brl: str | None = None
    retail_methodology_exclusion: bool = False
    aviation_methodology_exclusion: bool = False
    utilities_new_exclusion: bool = False
    screening_applied_after_canonical_rank: bool = True
    global_rank_is_immutable_under_screening: bool = True
    activated: bool = True


def methodology_policy_payload(policy: MagicFormulaMethodologyPolicy) -> dict:
    """Canonical V1 definition used by the stable policy fingerprint."""
    return {
        "policy_id": policy.policy_id,
        "policy_version": policy.policy_version,
        "methodology": {
            "structural_exclusion_version": policy.structural_exclusion_version,
            "structural_exclusions": sorted(policy.structural_exclusions),
            "security_selection": {
                "policy": policy.security_selection,
                "primary_metric": policy.security_selection_primary_metric,
                "tie_breaker": policy.security_selection_tie_breaker,
                "final_tie_breaker": policy.security_selection_final_tie_breaker,
                "market_type": policy.market_type,
                "forbidden_inputs": [
                    "price_availability",
                    "earnings_yield",
                    "return_on_capital",
                    "ranking_position",
                    "personal_screening",
                    "portfolio_positions",
                ],
            },
            "liquidity": {
                "policy": "L3",
                "window_sessions": policy.liquidity_window_sessions,
                "minimum_traded_sessions": policy.minimum_traded_sessions,
                "minimum_ratio": policy.liquidity_threshold,
                "volume_is_minimum_threshold": False,
                "rationale": (
                    "Evita negociação excessivamente esporádica, reduzindo preço stale, "
                    "dificuldade de execução, dependência de negócios isolados e baixa "
                    "representatividade do preço; não foi escolhida para maximizar cobertura."
                ),
            },
            "market_cap": {"minimum_brl": policy.minimum_market_cap_brl},
            "structural_sector_rules": {
                "retail_exclusion": policy.retail_methodology_exclusion,
                "aviation_exclusion": policy.aviation_methodology_exclusion,
                "new_utilities_exclusion": policy.utilities_new_exclusion,
            },
            "data_completeness": {
                "missing_data_is_ineligibility": False,
                "rankable_status": "ELIGIBLE_COMPLETE",
                "methodologically_eligible_statuses": [
                    "ELIGIBLE_COMPLETE",
                    "ELIGIBLE_DATA_BLOCKED",
                ],
                "review_statuses_are_rankable": False,
            },
            "screening": {
                "is_methodology": False,
                "applied_after_canonical_rank": policy.screening_applied_after_canonical_rank,
                "global_rank_immutable": policy.global_rank_is_immutable_under_screening,
                "default_exclude_traditional_retail": False,
                "default_exclude_aviation": False,
                "personal_preferences_in_methodology_hash": False,
            },
        },
    }


def methodology_policy_fingerprint(policy: MagicFormulaMethodologyPolicy) -> str:
    canonical = json.dumps(
        methodology_policy_payload(policy),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True, slots=True)
class MagicFormulaScreeningPreferences:
    """Optional display preferences; every default leaves sectors visible."""

    exclude_traditional_retail: bool = False
    exclude_aviation: bool = False
    exclude_wholesale: bool = False
    exclude_cash_and_carry: bool = False
    exclude_distribution: bool = False


DEFAULT_SCREENING_PREFERENCES = MagicFormulaScreeningPreferences()


def screening_exclusion_reason(
    attributes: dict, preferences: MagicFormulaScreeningPreferences
) -> str | None:
    """Return an optional display-filter reason, never an eligibility state."""
    if preferences.exclude_traditional_retail and (
        attributes.get("commerce_category") == "TRADITIONAL_RETAIL"
    ):
        return "USER_FILTER_TRADITIONAL_RETAIL"
    if preferences.exclude_aviation and attributes.get("aviation_related") is True:
        return "USER_FILTER_AVIATION"
    if preferences.exclude_wholesale and attributes.get("commerce_category") == "WHOLESALE":
        return "USER_FILTER_WHOLESALE"
    if preferences.exclude_cash_and_carry and (
        attributes.get("commerce_category") == "CASH_AND_CARRY"
    ):
        return "USER_FILTER_CASH_AND_CARRY"
    if preferences.exclude_distribution and (attributes.get("commerce_category") == "DISTRIBUTION"):
        return "USER_FILTER_DISTRIBUTION"
    return None


def apply_screening_preferences(
    ranked_rows: Iterable[dict],
    preferences: MagicFormulaScreeningPreferences = DEFAULT_SCREENING_PREFERENCES,
) -> list[dict]:
    """Filter ranked rows while preserving global rank and financial metrics."""
    visible: list[dict] = []
    for row in ranked_rows:
        result = dict(row)
        attributes = result.get("screening_attributes", result)
        reason = screening_exclusion_reason(attributes, preferences)
        if reason:
            continue
        result["filtered_position"] = len(visible) + 1
        visible.append(result)
    return visible


def legacy_exception_deprecation_plan() -> dict:
    """Keep the former ASAI3 override readable while removing it from decisions."""
    return {
        "legacy_exception": "ASAI3:ALLOW_RETAIL_EXCLUSION_EXCEPTION",
        "status": "DEPRECATED_COMPATIBILITY_ONLY",
        "migration": (
            "Retain parsing for historical snapshots; stop consulting it in the V8 "
            "method and screening pipeline; remove after old snapshot consumers migrate."
        ),
    }


def methodology_eligibility_state(
    *,
    structural_status: str,
    security_status: str,
    liquidity_status: str,
    data_complete: bool,
) -> str:
    """Classify a company without applying retail, aviation, or other display filters."""
    if structural_status == "INELIGIBLE_STRUCTURAL":
        return "INELIGIBLE_STRUCTURAL"
    if security_status != "RESOLVED":
        return "BUYABLE_SECURITY_REVIEW"
    if liquidity_status == "LIQUIDITY_FAIL":
        return "LIQUIDITY_FAIL"
    if liquidity_status != "LIQUIDITY_PASS":
        return "LIQUIDITY_REVIEW"
    return "ELIGIBLE_COMPLETE" if data_complete else "ELIGIBLE_DATA_BLOCKED"


def liquidity_candidate_status(
    traded_days_ratio: str | Decimal | None,
    *,
    evidence_complete: bool,
    threshold: Decimal = Decimal("0.50"),
) -> str:
    """Apply the candidate L3 rule while distinguishing zero from missing data."""
    if not evidence_complete or traded_days_ratio is None:
        return "LIQUIDITY_REVIEW"
    try:
        ratio = Decimal(str(traded_days_ratio))
    except InvalidOperation:
        return "LIQUIDITY_REVIEW"
    if not ratio.is_finite() or ratio < 0 or ratio > 1:
        return "LIQUIDITY_REVIEW"
    return "LIQUIDITY_PASS" if ratio >= threshold else "LIQUIDITY_FAIL"


def select_security_s4(candidates: Iterable[dict]) -> dict:
    """Apply S4 on valid market-010 candidates with a stable deterministic tie-break."""
    eligible = [
        row
        for row in candidates
        if row.get("valid_listing") is True and row.get("market_type") == "010"
    ]
    if not eligible or any(
        not row.get("liquidity_evidence_complete")
        or row.get("traded_days_ratio_30d") is None
        or row.get("median_daily_financial_volume_30d") is None
        for row in eligible
    ):
        return {"status": "BUYABLE_SECURITY_REVIEW", "selected_security": None}
    selected = min(
        eligible,
        key=lambda row: (
            -Decimal(str(row["traded_days_ratio_30d"])),
            -Decimal(str(row["median_daily_financial_volume_30d"])),
            str(row.get("isin") or "").upper(),
            str(row.get("ticker") or "").upper(),
            str(row.get("security_id") or "").upper(),
        ),
    )
    return {"status": "RESOLVED", "selected_security": selected}
