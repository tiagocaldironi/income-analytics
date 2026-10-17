from decimal import Decimal

from income_analytics.application.magic_formula_investable_universe import user_policy_decision
from income_analytics.application.magic_formula_screening import (
    DEFAULT_SCREENING_PREFERENCES,
    MagicFormulaScreeningPreferences,
    apply_screening_preferences,
    liquidity_candidate_status,
    methodology_eligibility_state,
    select_security_s4,
)


def test_retail_and_aviation_are_methodologically_eligible_by_default():
    for attributes in (
        {"commerce_category": "TRADITIONAL_RETAIL", "aviation_related": False},
        {"commerce_category": "", "aviation_related": True},
        {"commerce_category": "UNCERTAIN", "aviation_related": False},
    ):
        assert (
            methodology_eligibility_state(
                structural_status="PASS",
                security_status="RESOLVED",
                liquidity_status="LIQUIDITY_PASS",
                data_complete=True,
            )
            == "ELIGIBLE_COMPLETE"
        )
        assert apply_screening_preferences([{"screening_attributes": attributes}])


def test_default_preferences_do_not_exclude_retail_or_aviation():
    assert DEFAULT_SCREENING_PREFERENCES.exclude_traditional_retail is False
    assert DEFAULT_SCREENING_PREFERENCES.exclude_aviation is False


def test_optional_sector_filters_preserve_metrics_and_global_rank():
    rows = [
        {
            "global_rank": 1,
            "ey": Decimal("0.20"),
            "roc": Decimal("0.30"),
            "screening_attributes": {
                "commerce_category": "DISTRIBUTION",
                "aviation_related": False,
            },
        },
        {
            "global_rank": 2,
            "ey": Decimal("0.19"),
            "roc": Decimal("0.29"),
            "screening_attributes": {
                "commerce_category": "TRADITIONAL_RETAIL",
                "aviation_related": False,
            },
        },
        {
            "global_rank": 3,
            "ey": Decimal("0.18"),
            "roc": Decimal("0.28"),
            "screening_attributes": {"commerce_category": "", "aviation_related": True},
        },
    ]
    visible = apply_screening_preferences(
        rows,
        MagicFormulaScreeningPreferences(exclude_traditional_retail=True, exclude_aviation=True),
    )
    assert len(visible) == 1
    assert visible[0]["global_rank"] == 1
    assert visible[0]["filtered_position"] == 1
    assert visible[0]["ey"] == Decimal("0.20")
    assert visible[0]["roc"] == Decimal("0.30")
    assert rows[1]["global_rank"] == 2 and rows[2]["global_rank"] == 3


def test_asai3_cash_and_carry_does_not_need_eligibility_exception():
    row = {"ticker": "ASAI3", "screening_attributes": {"commerce_category": "CASH_AND_CARRY"}}
    assert apply_screening_preferences([row]) == [{**row, "filtered_position": 1}]
    assert (
        user_policy_decision(
            {
                "cvm_code": "025372",
                "economic_sector": "Comércio (Atacado e Varejo)",
                "securities": [{"ticker": "ASAI3"}],
            }
        )["status"]
        == "PASS"
    )


def test_financial_exclusion_remains_structural():
    assert (
        methodology_eligibility_state(
            structural_status="INELIGIBLE_STRUCTURAL",
            security_status="RESOLVED",
            liquidity_status="LIQUIDITY_PASS",
            data_complete=True,
        )
        == "INELIGIBLE_STRUCTURAL"
    )


def test_l3_uses_thirty_session_ratio_and_distinguishes_zero_from_missing():
    assert (
        liquidity_candidate_status(Decimal(15) / Decimal(30), evidence_complete=True)
        == "LIQUIDITY_PASS"
    )
    assert (
        liquidity_candidate_status(Decimal(14) / Decimal(30), evidence_complete=True)
        == "LIQUIDITY_FAIL"
    )
    assert liquidity_candidate_status(Decimal("0"), evidence_complete=True) == "LIQUIDITY_FAIL"
    assert liquidity_candidate_status(None, evidence_complete=False) == "LIQUIDITY_REVIEW"


def test_s4_prioritizes_trade_frequency_then_volume_and_stable_identity():
    candidates = [
        {
            "ticker": "PN1",
            "isin": "BRPN1",
            "valid_listing": True,
            "market_type": "010",
            "liquidity_evidence_complete": True,
            "traded_days_ratio_30d": "0.8",
            "median_daily_financial_volume_30d": "100",
            "price_available": False,
            "ey": 999,
        },
        {
            "ticker": "ON1",
            "isin": "BRON1",
            "valid_listing": True,
            "market_type": "010",
            "liquidity_evidence_complete": True,
            "traded_days_ratio_30d": "0.8",
            "median_daily_financial_volume_30d": "200",
            "price_available": True,
            "ey": 0,
        },
    ]
    assert select_security_s4(candidates)["selected_security"]["ticker"] == "ON1"


def test_s4_review_stays_review_when_any_valid_class_lacks_comparison():
    candidates = [
        {
            "ticker": "ON1",
            "isin": "BRON1",
            "valid_listing": True,
            "market_type": "010",
            "liquidity_evidence_complete": True,
            "traded_days_ratio_30d": "0.8",
            "median_daily_financial_volume_30d": "200",
        },
        {
            "ticker": "PN1",
            "isin": "",
            "valid_listing": True,
            "market_type": "010",
            "liquidity_evidence_complete": False,
            "traded_days_ratio_30d": None,
            "median_daily_financial_volume_30d": None,
        },
    ]
    assert select_security_s4(candidates) == {
        "status": "BUYABLE_SECURITY_REVIEW",
        "selected_security": None,
    }


def test_market_020_never_substitutes_for_market_010():
    candidate = {
        "ticker": "ON1",
        "isin": "BRON1",
        "valid_listing": True,
        "market_type": "020",
        "liquidity_evidence_complete": True,
        "traded_days_ratio_30d": "1",
        "median_daily_financial_volume_30d": "100",
    }
    assert select_security_s4([candidate])["status"] == "BUYABLE_SECURITY_REVIEW"


def test_stable_tie_break_is_deterministic_and_price_independent():
    candidates = [
        {
            "ticker": "ZETA3",
            "isin": "BRZETA",
            "valid_listing": True,
            "market_type": "010",
            "liquidity_evidence_complete": True,
            "traded_days_ratio_30d": "0.5",
            "median_daily_financial_volume_30d": "100",
            "price_available": True,
        },
        {
            "ticker": "ALFA3",
            "isin": "BRALFA",
            "valid_listing": True,
            "market_type": "010",
            "liquidity_evidence_complete": True,
            "traded_days_ratio_30d": "0.5",
            "median_daily_financial_volume_30d": "100",
            "price_available": False,
        },
    ]
    first = select_security_s4(candidates)["selected_security"]
    second = select_security_s4(list(reversed(candidates)))["selected_security"]
    assert first["ticker"] == second["ticker"] == "ALFA3"
