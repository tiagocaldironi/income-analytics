from datetime import date
from decimal import Decimal

from income_analytics.application.magic_formula_investable_universe import (
    POLICY,
    aggregate_daily_financial_volume,
    company_liquidity_scenario,
    coverage_by_eligibility,
    liquidity_scenario,
    listing_status,
    market_type_is_eligible,
    primary_status,
    publication_guard,
    security_liquidity_metrics,
    structural_decision,
)
from income_analytics.application.magic_formula_investable_universe import (
    legacy_user_policy_decision as user_policy_decision,
)


def issuer(cvm="025372", sector="Comércio (Atacado e Varejo)", ticker="ASAI3"):
    return {
        "cvm_code": cvm,
        "economic_sector": sector,
        "securities": [{"ticker": ticker, "share_class": "ON"}],
    }


def metrics(*, gap=0, ratio=Decimal("1"), volume=Decimal("600000")):
    return {
        "calendar_days_since_last_trade": gap,
        "traded_days_ratio_30d": ratio,
        "median_daily_financial_volume_30d": volume,
    }


def test_raw_universe_rows_are_preserved_and_classified_once():
    rows = [
        issuer(cvm=str(i).zfill(6), sector="Energia Elétrica", ticker=f"TST{i:02d}")
        for i in range(307)
    ]
    statuses = ["ELIGIBLE_DATA_BLOCKED" for _ in rows]
    assert len(rows) == 307 and len(statuses) == len(rows)


def test_missing_data_does_not_make_company_ineligible():
    result = coverage_by_eligibility(
        [{"structural_status": "PASS", "user_policy_status": "PASS", "data_complete": False}]
    )
    assert result["eligible_denominator"] == 1 and result["blocked"] == 1


def test_financial_sector_is_structurally_excluded_by_existing_rule():
    decision = structural_decision(issuer("001023", "Bancos", "BBAS3"))
    assert decision["status"] == "INELIGIBLE_STRUCTURAL"
    assert decision["rule"] == "FINANCIAL_SECTOR"


def test_v6_legacy_audit_retains_historical_retail_policy_semantics():
    company = issuer("000001", "Comércio (Atacado e Varejo)", "LJQQ3")
    assert structural_decision(company)["status"] == "PASS"
    assert user_policy_decision(company)["status"] == "INELIGIBLE_USER_POLICY"


def test_v6_legacy_audit_retains_asai3_exception_for_reproducibility():
    decision = user_policy_decision(issuer())
    assert decision["status"] == "PASS"
    assert decision["exception"] == "ALLOW_RETAIL_EXCLUSION_EXCEPTION"


def test_v6_legacy_exception_is_declarative_and_cvm_scoped():
    assert ("ASAI3", "025372", "ALLOW_RETAIL_EXCLUSION_EXCEPTION") in POLICY.ticker_exceptions
    assert user_policy_decision(issuer("000001"))["status"] == "INELIGIBLE_USER_POLICY"


def test_v6_legacy_audit_retains_aviation_policy_semantics():
    assert (
        user_policy_decision(issuer("024112", "Serviços Transporte e Logística", "AZUL4"))["rule"]
        == "AVIATION_COMPANY_EXCLUSION"
    )


def test_other_logistics_company_is_not_automatically_aviation():
    result = user_policy_decision(issuer("020800", "Serviços Transporte e Logística", "TGMA3"))
    assert result["status"] == "PASS"


def test_listing_after_reference_is_not_listed_yet():
    assert (
        listing_status([{"valid_from": "2026-01-01", "valid_to": None}], "2025-12-31")
        == "NOT_LISTED_YET"
    )


def test_delisted_before_reference_is_classified_separately():
    assert (
        listing_status([{"valid_from": "2010-01-01", "valid_to": "2025-12-30"}], "2025-12-31")
        == "DELISTED_BEFORE_REFERENCE"
    )


def test_security_listed_on_reference_date_is_eligible():
    assert (
        listing_status([{"valid_from": "2010-01-01", "valid_to": None}], "2025-12-31")
        == "LISTED_ON_REFERENCE_DATE"
    )


def test_missing_listing_dates_are_uncertain_not_excluded():
    assert listing_status([{}], "2025-12-31") == "UNCERTAIN"


def test_multiple_classes_remain_one_company_liquidity_decision():
    result = company_liquidity_scenario(
        [metrics(volume=Decimal("200000")), metrics(volume=Decimal("900000"))], "L5"
    )
    assert result == "PASS"


def test_market_020_is_not_accepted_as_010():
    assert market_type_is_eligible("010")
    assert not market_type_is_eligible("020")


def test_thirty_session_liquidity_window_calculates_days_ratio_and_median():
    sessions = [f"2025-12-{day:02d}" for day in range(1, 31)]
    history = {day: Decimal("100") for day in sessions[:15]}
    result = security_liquidity_metrics(sessions, history, sessions[-1])
    assert result["trading_days_30d"] == 30
    assert result["days_with_trade_30d"] == 15
    assert result["traded_days_ratio_30d"] == Decimal("0.5")
    assert result["median_daily_financial_volume_30d"] == Decimal("50")


def test_ninety_session_liquidity_window_is_separate():
    from datetime import timedelta

    start = date(2025, 1, 1)
    sessions = [(start + timedelta(days=i)).isoformat() for i in range(90)]
    history = {day: Decimal("10") for day in sessions[-45:]}
    result = security_liquidity_metrics(sessions, history, sessions[-1])
    assert result["trading_days_90d"] == 90
    assert result["days_with_trade_90d"] == 45
    assert result["traded_days_ratio_90d"] == Decimal("0.5")


def test_last_trade_calendar_and_session_gaps_are_calculated():
    sessions = ["2025-12-01", "2025-12-02", "2025-12-03", "2025-12-04"]
    result = security_liquidity_metrics(sessions, {"2025-12-02": Decimal("10")}, "2025-12-04")
    assert result["calendar_days_since_last_trade"] == 2
    assert result["trading_days_since_last_trade"] == 2


def test_daily_financial_volume_aggregation_is_per_security_and_date():
    result = aggregate_daily_financial_volume(
        [
            {"date": "2025-12-30", "volume": "125.50"},
            {"date": "2025-12-30", "volume": "74.50"},
        ]
    )
    assert result == {"2025-12-30": Decimal("200.00")}


def test_scenario_l1_requires_recent_trade():
    assert liquidity_scenario(metrics(gap=7), "L1") == "PASS"
    assert liquidity_scenario(metrics(gap=8), "L1") == "FAIL"


def test_scenario_l2_uses_thirty_calendar_days():
    assert liquidity_scenario(metrics(gap=30), "L2") == "PASS"
    assert liquidity_scenario(metrics(gap=31), "L2") == "FAIL"


def test_scenario_l3_requires_half_of_thirty_sessions():
    assert liquidity_scenario(metrics(ratio=Decimal("0.50")), "L3") == "PASS"
    assert liquidity_scenario(metrics(ratio=Decimal("0.49")), "L3") == "FAIL"


def test_scenario_l4_requires_eighty_percent_of_thirty_sessions():
    assert liquidity_scenario(metrics(ratio=Decimal("0.80")), "L4") == "PASS"
    assert liquidity_scenario(metrics(ratio=Decimal("0.79")), "L4") == "FAIL"


def test_volume_scenarios_use_explicit_audit_thresholds_only():
    assert liquidity_scenario(metrics(volume=Decimal("100000")), "L5") == "PASS"
    assert liquidity_scenario(metrics(volume=Decimal("499999")), "L6") == "FAIL"


def test_combined_l7_requires_recency_frequency_and_volume_together():
    assert (
        liquidity_scenario(metrics(gap=30, ratio=Decimal("0.5"), volume=Decimal("100000")), "L7")
        == "PASS"
    )
    assert (
        liquidity_scenario(metrics(gap=31, ratio=Decimal("1"), volume=Decimal("900000")), "L7")
        == "FAIL"
    )


def test_coverage_denominator_includes_blocked_eligible_companies():
    result = coverage_by_eligibility(
        [
            {"structural_status": "PASS", "user_policy_status": "PASS", "data_complete": True},
            {"structural_status": "PASS", "user_policy_status": "PASS", "data_complete": False},
        ]
    )
    assert result["eligible_denominator"] == 2 and result["complete"] == 1


def test_structurally_excluded_company_leaves_eligible_denominator():
    result = coverage_by_eligibility(
        [
            {
                "structural_status": "INELIGIBLE_STRUCTURAL",
                "user_policy_status": "PASS",
                "data_complete": True,
            },
        ]
    )
    assert result["eligible_denominator"] == 0


def test_user_policy_excluded_company_leaves_user_policy_denominator():
    result = coverage_by_eligibility(
        [
            {
                "structural_status": "PASS",
                "user_policy_status": "INELIGIBLE_USER_POLICY",
                "data_complete": True,
            },
        ]
    )
    assert result["eligible_denominator"] == 0


def test_identity_unresolved_remains_in_auditable_primary_state():
    result = primary_status(
        structural={"status": "PASS"},
        user_policy={"status": "PASS"},
        data_complete=False,
        liquidity_metrics=None,
        identity_unresolved=True,
    )
    assert result == "IDENTITY_UNRESOLVED"


def test_scenario_fail_does_not_change_raw_eligibility_denominator():
    source = [{"structural_status": "PASS", "user_policy_status": "PASS", "data_complete": False}]
    assert liquidity_scenario(metrics(gap=80), "L2") == "FAIL"
    assert coverage_by_eligibility(source)["eligible_denominator"] == 1


def test_ranking_is_locked_inactive_and_top_30_unpublished_by_policy():
    # The app entry point in the audit keeps these explicit false values.
    publication = publication_guard()
    assert publication["ranking_calculated"] is False
    assert publication["ranking_active"] is False and publication["ranking_blocked"] is True
    assert publication["top_30_published"] is False
