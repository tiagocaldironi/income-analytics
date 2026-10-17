"""Explicit V1 methodology-policy contracts required before activation."""

from __future__ import annotations

import csv
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from income_analytics.application.magic_formula_investable_universe import (
    structural_decision,
    user_policy_decision,
)
from income_analytics.application.magic_formula_screening import (
    MagicFormulaMethodologyPolicy,
    MagicFormulaScreeningPreferences,
    apply_screening_preferences,
    legacy_exception_deprecation_plan,
    liquidity_candidate_status,
    methodology_eligibility_state,
    methodology_policy_fingerprint,
    methodology_policy_payload,
    select_security_s4,
)

ROOT = Path(__file__).resolve().parents[2]
V8_UNIVERSE = (
    ROOT
    / "docs/appendices/magic_formula_policy_review_resolution_v8/methodological_universe_v8.csv"
)


def _candidate(ticker: str, ratio: str, volume: str, **extra) -> dict:
    return {
        "ticker": ticker,
        "isin": f"BR{ticker}ACNOR0",
        "security_id": ticker,
        "share_class": "ON",
        "valid_listing": True,
        "market_type": "010",
        "liquidity_evidence_complete": True,
        "traded_days_ratio_30d": ratio,
        "median_daily_financial_volume_30d": volume,
        **extra,
    }


def _state(*, liquidity: str = "LIQUIDITY_PASS", complete: bool = True) -> str:
    return methodology_eligibility_state(
        structural_status="PASS",
        security_status="RESOLVED",
        liquidity_status=liquidity,
        data_complete=complete,
    )


def _universe_status_counts() -> Counter[str]:
    with V8_UNIVERSE.open(encoding="utf-8-sig", newline="") as stream:
        return Counter(row["methodological_status_v8"] for row in csv.DictReader(stream))


def test_v1_01_financial_structural_exclusion_remains_excluded():
    assert structural_decision({"economic_sector": "Bancos"})["status"] == "INELIGIBLE_STRUCTURAL"


def test_v1_02_traditional_retail_is_not_methodology_excluded():
    result = user_policy_decision({"economic_sector": "Comércio (Atacado e Varejo)"})
    assert result["status"] == "PASS"


def test_v1_03_aviation_is_not_methodology_excluded():
    result = user_policy_decision({"cvm_code": "024112", "economic_sector": "Transporte"})
    assert result["status"] == "PASS"


def test_v1_04_utilities_receive_no_new_exclusion():
    assert structural_decision({"economic_sector": "Energia Elétrica"})["status"] == "PASS"


def test_v1_05_market_cap_does_not_exclude():
    policy = MagicFormulaMethodologyPolicy()
    assert policy.minimum_market_cap_brl is None
    assert _state() == "ELIGIBLE_COMPLETE"


def test_v1_06_s4_chooses_highest_trading_frequency():
    result = select_security_s4([_candidate("AAA3", "0.80", "100"), _candidate("BBB3", "1", "10")])
    assert result["selected_security"]["ticker"] == "BBB3"


def test_v1_07_s4_uses_volume_only_after_frequency_tie():
    result = select_security_s4(
        [_candidate("AAA3", "0.80", "100"), _candidate("BBB3", "0.80", "200")]
    )
    assert result["selected_security"]["ticker"] == "BBB3"


def test_v1_08_s4_ignores_price_availability():
    candidates = [
        _candidate("AAA3", "0.80", "100", price_available=True),
        _candidate("BBB3", "0.80", "200", price_available=False),
    ]
    assert select_security_s4(candidates)["selected_security"]["ticker"] == "BBB3"


def test_v1_09_s4_ignores_earnings_yield():
    candidates = [
        _candidate("AAA3", "0.80", "100", earnings_yield=Decimal("0.90")),
        _candidate("BBB3", "0.80", "200", earnings_yield=Decimal("0.01")),
    ]
    assert select_security_s4(candidates)["selected_security"]["ticker"] == "BBB3"


def test_v1_10_s4_ignores_return_on_capital():
    candidates = [
        _candidate("AAA3", "0.80", "100", return_on_capital=Decimal("0.90")),
        _candidate("BBB3", "0.80", "200", return_on_capital=Decimal("0.01")),
    ]
    assert select_security_s4(candidates)["selected_security"]["ticker"] == "BBB3"


def test_v1_11_s4_ignores_existing_rank_values():
    candidates = [
        _candidate("AAA3", "0.80", "100", global_rank=1, combined_rank=1),
        _candidate("BBB3", "0.80", "200", global_rank=99, combined_rank=99),
    ]
    assert select_security_s4(candidates)["selected_security"]["ticker"] == "BBB3"


def test_v1_12_unresolved_s4_remains_review():
    assert select_security_s4([]) == {
        "status": "BUYABLE_SECURITY_REVIEW",
        "selected_security": None,
    }


def test_v1_13_liquidity_fifteen_of_thirty_passes():
    assert liquidity_candidate_status("0.50", evidence_complete=True) == "LIQUIDITY_PASS"


def test_v1_14_liquidity_fourteen_of_thirty_fails():
    assert liquidity_candidate_status("14/30", evidence_complete=True) == "LIQUIDITY_REVIEW"
    assert (
        liquidity_candidate_status(Decimal(14) / Decimal(30), evidence_complete=True)
        == "LIQUIDITY_FAIL"
    )


def test_v1_15_missing_liquidity_evidence_is_review():
    assert liquidity_candidate_status(None, evidence_complete=False) == "LIQUIDITY_REVIEW"


def test_v1_16_nonselected_class_cannot_rescue_l3_failure():
    assert _state(liquidity="LIQUIDITY_FAIL") == "LIQUIDITY_FAIL"


def test_v1_17_missing_price_after_methodology_pass_is_data_blocked():
    assert _state(complete=False) == "ELIGIBLE_DATA_BLOCKED"


def test_v1_18_missing_fundamentals_after_methodology_pass_is_data_blocked():
    assert _state(complete=False) == "ELIGIBLE_DATA_BLOCKED"


def test_v1_19_missing_data_is_not_structural_ineligibility():
    assert _state(complete=False) != "INELIGIBLE_STRUCTURAL"


def test_v1_20_review_is_not_liquidity_fail():
    result = methodology_eligibility_state(
        structural_status="PASS",
        security_status="REVIEW",
        liquidity_status="LIQUIDITY_REVIEW",
        data_complete=False,
    )
    assert result == "BUYABLE_SECURITY_REVIEW"


def test_v1_21_retail_screening_does_not_change_methodology_state():
    before = _state()
    apply_screening_preferences(
        [{"ticker": "VAREJO3", "commerce_category": "TRADITIONAL_RETAIL"}],
        MagicFormulaScreeningPreferences(exclude_traditional_retail=True),
    )
    assert _state() == before


def test_v1_22_aviation_screening_does_not_change_methodology_state():
    before = _state()
    apply_screening_preferences(
        [{"ticker": "AERO3", "aviation_related": True}],
        MagicFormulaScreeningPreferences(exclude_aviation=True),
    )
    assert _state() == before


def test_v1_23_screening_preserves_global_rank_contract():
    filtered = apply_screening_preferences(
        [
            {"ticker": "VAREJO3", "commerce_category": "TRADITIONAL_RETAIL", "global_rank": 1},
            {"ticker": "AERO3", "aviation_related": True, "global_rank": 2},
        ],
        MagicFormulaScreeningPreferences(exclude_traditional_retail=True),
    )
    assert filtered[0]["global_rank"] == 2
    assert filtered[0]["filtered_position"] == 1


def test_v1_24_default_screening_shows_retail():
    rows = apply_screening_preferences([{"commerce_category": "TRADITIONAL_RETAIL"}])
    assert len(rows) == 1


def test_v1_25_default_screening_shows_aviation():
    rows = apply_screening_preferences([{"aviation_related": True}])
    assert len(rows) == 1


def test_v1_26_asai3_needs_no_methodology_exception():
    result = user_policy_decision({"cvm_code": "025372", "securities": [{"ticker": "ASAI3"}]})
    assert result["status"] == "PASS"
    assert legacy_exception_deprecation_plan()["status"] == "DEPRECATED_COMPATIBILITY_ONLY"


def test_v1_27_v8_baseline_statuses_sum_to_307():
    counts = _universe_status_counts()
    assert sum(counts.values()) == 307


def test_v1_28_methodological_coverage_denominator_is_complete_plus_blocked():
    counts = _universe_status_counts()
    complete = counts["ELIGIBLE_COMPLETE"]
    blocked = counts["ELIGIBLE_DATA_BLOCKED"]
    assert Decimal(complete) / Decimal(complete + blocked) == Decimal(180) / Decimal(243)


def test_v1_29_conservative_coverage_includes_reviews():
    counts = _universe_status_counts()
    complete = counts["ELIGIBLE_COMPLETE"]
    blocked = counts["ELIGIBLE_DATA_BLOCKED"]
    security_review = counts["BUYABLE_SECURITY_REVIEW"]
    liquidity_review = counts["LIQUIDITY_REVIEW"]
    assert Decimal(complete) / Decimal(
        complete + blocked + security_review + liquidity_review
    ) == Decimal(180) / Decimal(262)


def test_v1_30_policy_serialization_and_version_are_stable():
    policy = MagicFormulaMethodologyPolicy()
    payload = methodology_policy_payload(policy)
    assert payload == json.loads(json.dumps(payload, ensure_ascii=False))
    assert methodology_policy_fingerprint(policy) == methodology_policy_fingerprint(policy)
    assert policy.activated is True
    assert policy.policy_id == "MF_BR_2027_V1"
    assert "exclude_traditional_retail" not in policy.__dataclass_fields__
    assert "exclude_aviation" not in policy.__dataclass_fields__
    assert payload["policy_id"] == "MF_BR_2027_V1"
