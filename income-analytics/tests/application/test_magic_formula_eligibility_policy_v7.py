from decimal import Decimal

import pytest

from income_analytics.application.magic_formula_eligibility_policy_v7 import (
    commerce_policy_decision,
    coverage_metrics,
    final_eligibility_state,
    select_buyable_security,
    selected_security_liquidity,
)


@pytest.mark.parametrize(
    ("category", "confidence", "expected"),
    [
        ("TRADITIONAL_RETAIL", "HIGH", "INELIGIBLE_USER_POLICY"),
        ("WHOLESALE", "HIGH", "PASS"),
        ("CASH_AND_CARRY", "HIGH", "PASS"),
        ("DISTRIBUTION", "HIGH", "PASS"),
        ("COMMERCE_ADJACENT", "HIGH", "PASS"),
        ("MIXED_COMMERCE", "MEDIUM", "POLICY_REVIEW"),
        ("UNCERTAIN", "LOW", "POLICY_REVIEW"),
        ("TRADITIONAL_RETAIL", "LOW", "POLICY_REVIEW"),
    ],
)
def test_v7_legacy_commerce_taxonomy_policy_outcomes(category, confidence, expected):
    result = commerce_policy_decision(
        category, confidence, "CVM FCA", "ID_DOC=123;Descricao_Atividade"
    )
    assert result["status"] == expected


def test_v7_legacy_commerce_decision_requires_evidence_reference():
    result = commerce_policy_decision("TRADITIONAL_RETAIL", "HIGH", None, None)
    assert result["status"] == "POLICY_REVIEW"
    assert result["reason"] == "EVIDENCE_MISSING_OR_LOW_CONFIDENCE"


def test_v7_legacy_asai_cash_and_carry_audit_decision():
    result = commerce_policy_decision(
        "CASH_AND_CARRY", "HIGH", "CVM FCA", "CVM=025372;ID_DOC=146509"
    )
    assert result["status"] == "PASS"


def candidate(
    ticker,
    ratio="0.5",
    volume="100",
    *,
    price_available=True,
    valid=True,
    market_type="010",
    complete=True,
    isin=None,
):
    return {
        "ticker": ticker,
        "isin": isin or f"BR{ticker}",
        "security_id": f"BR:{ticker}",
        "valid_listing": valid,
        "market_type": market_type,
        "liquidity_evidence_complete": complete,
        "traded_days_ratio_30d": ratio,
        "median_daily_financial_volume_30d": volume,
        "price_available": price_available,
    }


def test_single_security_resolves():
    result = select_buyable_security([candidate("ON1")], "S4")
    assert result.status == "RESOLVED"
    assert result.selected_security["ticker"] == "ON1"


def test_s1_highest_frequency_wins():
    result = select_buyable_security(
        [candidate("PN1", "0.6", "1000"), candidate("ON1", "0.8", "10")], "S1"
    )
    assert result.selected_security["ticker"] == "ON1"


def test_s2_highest_median_volume_wins():
    result = select_buyable_security(
        [candidate("ON1", "0.9", "100"), candidate("PN1", "0.5", "900")], "S2"
    )
    assert result.selected_security["ticker"] == "PN1"


def test_s3_selects_only_l3_passing_classes_then_volume():
    result = select_buyable_security(
        [candidate("ON1", "0.49", "10000"), candidate("PN1", "0.5", "500")], "S3"
    )
    assert result.selected_security["ticker"] == "PN1"


def test_s4_frequency_then_volume_then_stable_key():
    result = select_buyable_security(
        [candidate("PN1", "0.5", "200"), candidate("ON1", "0.5", "200")], "S4"
    )
    assert result.selected_security["ticker"] == "ON1"
    assert result.reason == "SELECTED_BY_S4_EXECUTION_RULE"


def test_price_availability_does_not_change_selection():
    candidates = [
        candidate("ON1", "0.8", "10", price_available=False),
        candidate("PN1", "0.6", "1000"),
    ]
    result = select_buyable_security(candidates, "S4")
    assert result.selected_security["ticker"] == "ON1"
    assert result.selected_security["price_available"] is False


def test_lower_liquidity_class_cannot_win_because_it_has_a_price():
    candidates = [
        candidate("ON1", "0.8", "10", price_available=False),
        candidate("PN1", "0.2", "1000", price_available=True),
    ]
    result = select_buyable_security(candidates, "S4")
    assert result.selected_security["ticker"] == "ON1"


def test_unit_is_one_security_candidate_not_duplicate_components():
    result = select_buyable_security([candidate("UNIT1", "0.7", "200", isin="BRUNIT")], "S4")
    assert result.selected_security["ticker"] == "UNIT1"


def test_invalid_security_is_rejected():
    result = select_buyable_security([candidate("OLD1", valid=False)], "S4")
    assert result.status == "BUYABLE_SECURITY_REVIEW"
    assert result.reason == "NO_VALID_LISTED_SECURITY"


def test_deterministic_tie_uses_stable_identity_key_only_after_economic_tie():
    result = select_buyable_security(
        [
            candidate("SEC2", "0.5", "100", isin="ZISIN"),
            candidate("SEC1", "0.5", "100", isin="AISIN"),
        ],
        "S4",
    )
    assert result.selected_security["ticker"] == "SEC1"


def test_selector_does_not_require_or_consume_rank_values():
    result = select_buyable_security(
        [candidate("ON1", "0.8", "10") | {"ey_rank": 1, "roc_rank": 1}], "S4"
    )
    assert result.selected_security["ticker"] == "ON1"
    assert "ranking" not in result.reason.lower()


def test_selection_is_idempotent():
    candidates = [candidate("ON1", "0.8", "100"), candidate("PN1", "0.7", "900")]
    a = select_buyable_security(candidates, "S4")
    b = select_buyable_security(candidates, "S4")
    assert a == b


def test_unknown_security_policy_s0_remains_review():
    result = select_buyable_security([candidate("ON1")], "S0")
    assert result.status == "BUYABLE_SECURITY_REVIEW"
    assert result.reason == "CURRENT_SECURITY_POLICY_UNDEFINED"


def test_incomplete_liquidity_for_any_valid_class_keeps_selection_in_review():
    result = select_buyable_security(
        [candidate("ON1", "0.8", "1000"), candidate("PN1", complete=False)], "S4"
    )
    assert result.status == "BUYABLE_SECURITY_REVIEW"


def test_s3_all_classes_below_threshold_is_liquidity_fail():
    result = select_buyable_security(
        [candidate("ON1", "0.49", "100"), candidate("PN1", "0.2", "50")], "S3"
    )
    assert result.status == "LIQUIDITY_FAIL"
    assert result.selected_security["ticker"] == "ON1"


def test_market_020_is_never_a_buyable_010_candidate():
    result = select_buyable_security([candidate("ONF1", market_type="020")], "S4")
    assert result.status == "BUYABLE_SECURITY_REVIEW"


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [("0.5", "LIQUIDITY_PASS"), ("0.49", "LIQUIDITY_FAIL"), ("0.51", "LIQUIDITY_PASS")],
)
def test_l3_threshold(ratio, expected):
    selection = select_buyable_security([candidate("ON1", ratio, "0")], "S4")
    assert selected_security_liquidity(selection) == expected


def test_liquidity_missing_evidence_is_review():
    selection = select_buyable_security([candidate("ON1", complete=False)], "S4")
    assert selected_security_liquidity(selection) == "LIQUIDITY_REVIEW"


def test_another_issuer_class_cannot_rescue_selected_security():
    selection = select_buyable_security(
        [candidate("ON1", "0.2", "10"), candidate("PN1", "0.9", "10000")], "S4"
    )
    assert selection.selected_security["ticker"] == "PN1"
    # The selected PN passes; a failing non-selected class is not the issuer result.
    assert selected_security_liquidity(selection) == "LIQUIDITY_PASS"
    failing = select_buyable_security([candidate("ON1", "0.2", "10")], "S4")
    assert selected_security_liquidity(failing) == "LIQUIDITY_FAIL"


def test_price_missing_does_not_imply_liquidity_failure():
    selection = select_buyable_security([candidate("ON1", "0.8", "0", price_available=False)], "S4")
    assert selected_security_liquidity(selection) == "LIQUIDITY_PASS"


def test_volume_is_not_a_minimum_liquidity_policy():
    selection = select_buyable_security([candidate("ON1", "0.5", "0")], "S4")
    assert selected_security_liquidity(selection) == "LIQUIDITY_PASS"


def test_volume_is_only_used_as_selection_tie_breaker_in_s4():
    result = select_buyable_security(
        [candidate("ON1", "0.5", "10"), candidate("PN1", "0.5", "20")], "S4"
    )
    assert result.selected_security["ticker"] == "PN1"


def test_30_session_ratio_denominator_is_precomputed_as_candidate_metric():
    result = select_buyable_security([candidate("ON1", Decimal(15) / Decimal(30), "0")], "S4")
    assert result.selected_security["traded_days_ratio_30d"] == Decimal("0.5")


def test_l3_policy_does_not_activate_volume_or_market_cap_rules():
    from income_analytics.application.magic_formula_investable_universe import POLICY

    assert POLICY.liquidity_policy_activated is False
    assert POLICY.minimum_market_cap_policy_enabled is False
    assert POLICY.security_selection_policy_activated is False


def test_coverage_counts_complete_and_blocked_as_confirmed_eligible():
    result = coverage_metrics(
        [{"final_status": "ELIGIBLE_COMPLETE"}, {"final_status": "ELIGIBLE_DATA_BLOCKED"}]
    )
    assert result["confirmed_eligible"] == 2
    assert result["confirmed_complete"] == 1
    assert result["confirmed_blocked"] == 1
    assert result["confirmed_eligible_coverage"] == Decimal("50")


def test_blocked_eligible_stays_in_denominator():
    result = coverage_metrics(
        [{"final_status": "ELIGIBLE_COMPLETE"}, {"final_status": "ELIGIBLE_DATA_BLOCKED"}]
    )
    assert result["confirmed_eligible"] == 2


def test_liquidity_fail_is_confirmed_ineligible():
    result = coverage_metrics(
        [{"final_status": "ELIGIBLE_COMPLETE"}, {"final_status": "LIQUIDITY_FAIL"}]
    )
    assert result["confirmed_ineligible"] == 1
    assert result["confirmed_eligible"] == 1


def test_v7_legacy_user_policy_exclusion_leaves_historical_denominator():
    result = coverage_metrics(
        [{"final_status": "ELIGIBLE_COMPLETE"}, {"final_status": "INELIGIBLE_USER_POLICY"}]
    )
    assert result["confirmed_eligible"] == 1
    assert result["confirmed_ineligible"] == 1


def test_review_is_included_in_conservative_denominator():
    result = coverage_metrics(
        [{"final_status": "ELIGIBLE_COMPLETE"}, {"final_status": "LIQUIDITY_REVIEW"}]
    )
    assert result["potential_eligible_denominator"] == 2
    assert result["conservative_coverage"] == Decimal("50")


def test_missing_data_does_not_create_exclusion():
    selection = select_buyable_security([candidate("ON1", "0.8", "100")], "S4")
    state = final_eligibility_state(
        structural="PASS",
        user_policy="PASS",
        security_selection=selection,
        data_complete=False,
    )
    assert state == "ELIGIBLE_DATA_BLOCKED"


def test_coverage_is_a_readout_and_does_not_change_policy_or_selection():
    selection = select_buyable_security([candidate("ON1", "0.8", "100")], "S4")
    before = selection
    coverage_metrics([{"final_status": "ELIGIBLE_COMPLETE"}])
    assert select_buyable_security([candidate("ON1", "0.8", "100")], "S4") == before


def test_v7_legacy_policy_review_precedes_security_and_data_status():
    selection = select_buyable_security([candidate("ON1")], "S4")
    assert (
        final_eligibility_state(
            structural="PASS",
            user_policy="POLICY_REVIEW",
            security_selection=selection,
            data_complete=False,
        )
        == "POLICY_REVIEW"
    )


def test_buyable_security_review_is_a_separate_final_state():
    selection = select_buyable_security([], "S4")
    assert (
        final_eligibility_state(
            structural="PASS", user_policy="PASS", security_selection=selection, data_complete=False
        )
        == "BUYABLE_SECURITY_REVIEW"
    )


@pytest.mark.parametrize(
    ("target_ticker", "alternate_ticker", "alternate_ratio", "alternate_volume", "expected"),
    [
        ("EMAE3", "EMAE4", "1", "213043.5", "EMAE4"),
        ("MTSA3", "MTSA4", "1", "114887", "MTSA4"),
        ("JOPA4", "JOPA3", "0.1", "0", "JOPA3"),
    ],
)
def test_v6_real_no_trade_issuers_select_only_by_buyable_security_metrics(
    target_ticker, alternate_ticker, alternate_ratio, alternate_volume, expected
):
    result = select_buyable_security(
        [
            candidate(target_ticker, "0", "0", price_available=True),
            candidate(alternate_ticker, alternate_ratio, alternate_volume, price_available=False),
        ],
        "S4",
    )
    assert result.selected_security["ticker"] == expected
    assert result.selected_security["price_available"] is False
