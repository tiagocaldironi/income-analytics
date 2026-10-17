from income_analytics.application.magic_formula_point_in_time import (
    select_annual_financial_document,
    validate_point_in_time_snapshot,
)


def test_selects_latest_annual_filed_by_as_of_without_reading_metric_values():
    candidates = [
        {
            "document_type": "DFP",
            "period_end": "2024-12-31",
            "filing_date": "2025-03-01",
            "information_available_date": "2025-03-01",
            "source_id": "dfp24",
            "version": "1",
            "financial_values": {"ey": 0.1},
        },
        {
            "document_type": "DFP",
            "period_end": "2025-12-31",
            "filing_date": "2026-03-01",
            "information_available_date": "2026-03-01",
            "source_id": "dfp25",
            "version": "1",
            "financial_values": {"ey": 999},
        },
    ]
    selected, audit = select_annual_financial_document(candidates, "2025-12-30")
    assert selected["source_id"] == "dfp24"
    assert next(row for row in audit if row["source_id"] == "dfp25")["rejection_reason"] == (
        "POST_AS_OF_INFORMATION"
    )


def test_future_only_document_blocks_company():
    selected, _ = select_annual_financial_document(
        [
            {
                "document_type": "DFP",
                "period_end": "2025-12-31",
                "information_available_date": "2026-03-01",
                "source_id": "future",
            }
        ],
        "2025-12-30",
    )
    assert selected is None


def test_changing_future_financial_values_cannot_change_historical_selection():
    eligible = {
        "document_type": "DFP",
        "period_end": "2024-12-31",
        "information_available_date": "2025-03-01",
        "source_id": "dfp24",
        "financial_values": {"ey": 0.01, "roc": 0.02},
    }
    future = {
        "document_type": "DFP",
        "period_end": "2025-12-31",
        "information_available_date": "2026-03-01",
        "source_id": "dfp25",
        "financial_values": {"ey": 0.03, "roc": 0.04},
    }
    selected_before, _ = select_annual_financial_document([eligible, future], "2025-12-30")
    future["financial_values"] = {"ey": 1_000_000, "roc": -99_000}
    selected_after, _ = select_annual_financial_document([eligible, future], "2025-12-30")
    assert selected_before["source_id"] == selected_after["source_id"] == "dfp24"


def test_interim_is_recorded_but_not_selected_by_annual_contract():
    selected, audit = select_annual_financial_document(
        [
            {
                "document_type": "ITR",
                "period_end": "2025-09-30",
                "information_available_date": "2025-11-01",
                "source_id": "itr",
            }
        ],
        "2025-12-30",
    )
    assert selected is None
    assert audit[0]["rejection_reason"] == "INTERIM_NOT_SUPPORTED_BY_ANNUAL_CONTRACT"


def test_non_year_end_dfp_is_not_annual_under_existing_contract():
    selected, audit = select_annual_financial_document(
        [
            {
                "document_type": "DFP",
                "period_end": "2025-06-30",
                "information_available_date": "2025-09-25",
                "source_id": "dfp-midyear",
            },
            {
                "document_type": "DFP",
                "period_end": "2024-12-31",
                "information_available_date": "2025-03-01",
                "source_id": "dfp-annual",
            },
        ],
        "2025-12-30",
    )
    assert selected["source_id"] == "dfp-annual"
    assert audit[0]["rejection_reason"] == ("NON_ANNUAL_DFP_NOT_SUPPORTED_BY_ACCOUNTING_CONTRACT")


def test_independent_validator_fails_closed_for_missing_or_future_lineage():
    result = validate_point_in_time_snapshot(
        {
            "ranking_as_of_date": "2025-12-30",
            "results": [
                {
                    "selected_security": "PETR4",
                    "point_in_time_lineage": {
                        "financial_information_available_date": "2025-03-01",
                        "shares_information_available_date": "2026-01-01",
                        "price_date": "2025-12-30",
                        "security_valid_from": "1990-01-01",
                        "security_valid_to": None,
                        "security_identity_source": "fixture",
                    },
                },
                {"selected_security": "VALE3"},
            ],
        }
    )
    assert result["status"] == "FAIL"
    assert {item["reason"] for item in result["failures"]} >= {
        "SHARES_INFORMATION_AVAILABLE_DATE_AFTER_AS_OF",
        "LINEAGE_MISSING",
    }
