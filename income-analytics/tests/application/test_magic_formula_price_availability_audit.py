"""Read-only previous-close policies never alter the production universe."""

from pathlib import Path

import pytest

from income_analytics.application.magic_formula_price_availability_audit import (
    audit_snapshot_order,
    classify_unavailable,
    project_scenarios,
    select_close,
)
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)

REFERENCE = "2025-12-30"
SECURITY = {"ticker": "TEST3", "isin": "BRTESTACNOR1", "share_class": "ON"}


def row(day, *, ticker="TEST3", isin="BRTESTACNOR1", market="010", price="10.00"):
    return {
        "date": day,
        "ticker": ticker,
        "isin": isin,
        "market": market,
        "price": price,
        "source": f"COTAHIST_A2025.ZIP|line={day}",
    }


def test_exact_date_lookup():
    result = select_close(SECURITY, [row("2025-12-30")], REFERENCE)
    assert result["status"] == "RESOLVED" and result["effective_date"] == REFERENCE


def test_previous_trading_date_discovery():
    result = select_close(SECURITY, [row("2025-12-29")], REFERENCE, 1)
    assert result["effective_date"] == "2025-12-29" and result["price"].as_tuple().exponent == -2


def test_no_previous_price():
    assert select_close(SECURITY, [row("2025-12-31")], REFERENCE, 30) == {
        "status": "MISSING",
        "reason": "NO_PREVIOUS_PRICE",
    }


@pytest.mark.parametrize(
    "days,quote_day",
    [
        (1, "2025-12-29"),
        (3, "2025-12-27"),
        (5, "2025-12-25"),
        (7, "2025-12-23"),
        (30, "2025-11-30"),
    ],
)
def test_policy_simulation_thresholds(days, quote_day):
    assert select_close(SECURITY, [row(quote_day)], REFERENCE, days)["status"] == "RESOLVED"


def test_future_price_is_never_selected():
    result = select_close(
        SECURITY, [row("2025-12-31", price="999"), row("2025-12-29", price="10")], REFERENCE, 30
    )
    assert result["effective_date"] == "2025-12-29" and str(result["price"]) == "10"


def test_wrong_isin_is_rejected_by_exact_lookup():
    result = select_close(SECURITY, [row("2025-12-29", isin="BRWRNGACNOR1")], REFERENCE, 7)
    assert result["status"] == "MISSING"


def test_wrong_class_is_rejected():
    result = select_close({**SECURITY, "share_class": "PN"}, [row("2025-12-29")], REFERENCE, 7)
    assert result["reason"] == "CLASS_OR_IDENTIFIER_MISMATCH"


@pytest.mark.parametrize(
    "evidence,expected",
    [
        ({"accepted_source_price_found": True}, "LOOKUP_BUG"),
        ({"same_isin_other_ticker_found": True}, "HISTORICAL_TICKER_LOOKUP_GAP"),
        ({"same_security_other_market_only": True}, "SECURITY_TYPE_NOT_COVERED"),
        ({"official_alternative_dataset_price_found": True}, "ALTERNATIVE_B3_DATASET_REQUIRED"),
        ({"corporate_action_break_proven": True}, "CORPORATE_ACTION_LOOKUP_GAP"),
        ({"not_listed_at_reference": True}, "LISTING_DATE_GAP"),
        ({"delisted_at_reference": True}, "DELISTING_DATE_GAP"),
        ({"archive_expected_but_missing": True}, "DATASET_GAP"),
        ({"official_source_scanned_no_valid_close": True}, "SOURCE_GAP"),
    ],
)
def test_unavailable_cause_classification(evidence, expected):
    assert classify_unavailable(evidence) == expected


def test_coverage_projection_counts_complete_issuers_not_partial_prices():
    cases = [
        {
            "issuer_id": "A",
            "reference_date": REFERENCE,
            "securities": [
                {**SECURITY, "records": [row("2025-12-29")]},
                {"ticker": "TEST4", "isin": "BRTESTACNPR1", "share_class": "PN", "records": []},
            ],
        }
    ]
    result = project_scenarios(185, 307, cases, blocked_unresolved=5)
    one_day = next(item for item in result if item["scenario"] == "WITHIN_1_DAY")
    assert one_day["price_recoveries"] == 0
    assert one_day["complete_companies"] == 185 and one_day["remaining_price_blockers"] == 6


def test_coverage_projection_includes_company_only_after_all_prices():
    cases = [
        {
            "issuer_id": "A",
            "reference_date": REFERENCE,
            "securities": [{**SECURITY, "records": [row("2025-12-29")]}],
        }
    ]
    result = project_scenarios(185, 307, cases, blocked_unresolved=5)
    one_day = next(item for item in result if item["scenario"] == "WITHIN_1_DAY")
    assert one_day["price_recoveries"] == 1 and one_day["complete_companies"] == 186
    assert one_day["remaining_price_blockers"] == 5


def test_dry_run_does_not_persist_universe_snapshot():
    repository = MagicFormulaUniverseRepository(Path("data/magic_formula/universe_snapshots.db"))
    with repository.connection() as connection:
        before = connection.execute(
            "SELECT COUNT(*), MAX(created_at) FROM magic_formula_universe_snapshots"
        ).fetchone()
    project_scenarios(185, 307, [], blocked_unresolved=5)
    with repository.connection() as connection:
        after = connection.execute(
            "SELECT COUNT(*), MAX(created_at) FROM magic_formula_universe_snapshots"
        ).fetchone()
    assert after == before


def test_ranking_stays_blocked_in_saved_snapshot():
    snapshot = MagicFormulaUniverseRepository(
        Path("data/magic_formula/universe_snapshots.db")
    ).latest()
    assert snapshot["ranking_status"] == "INACTIVE"
    assert snapshot["tool_status"] == "VALIDATION_REQUIRED"


def test_snapshot_ordering_audit_resolves_duplicate_timestamp_with_rowid():
    repository = MagicFormulaUniverseRepository(Path("data/magic_formula/universe_snapshots.db"))
    with repository.connection() as connection:
        rows = connection.execute(
            "SELECT rowid, universe_snapshot_id, created_at "
            "FROM magic_formula_universe_snapshots ORDER BY rowid"
        ).fetchall()
    result = audit_snapshot_order(rows)
    assert result["selection_query"] == "ORDER BY created_at DESC, rowid DESC"
    assert result["duplicate_timestamps_present"] is True
    assert result["deterministic"] is True and result["ordering_risk"] is False


def test_csna3_and_v3_recoveries_survive_current_snapshot():
    snapshot = MagicFormulaUniverseRepository(
        Path("data/magic_formula/universe_snapshots.db")
    ).latest()
    expected = {
        "004030": ("CSNA3", "8.94"),
        "020788": ("MBRF3", "19.98"),
        "019100": ("CTAX3", "0.97"),
        "025895": ("WDCN3", "2.63"),
        "020630": ("FIEI3", "14.49"),
        "022055": ("AMAR3", "1.01"),
    }
    for cvm_code, (ticker, price) in expected.items():
        issuer = next(item for item in snapshot["issuers"] if item["cvm_code"] == cvm_code)
        security = next(item for item in issuer["securities"] if item["ticker"] == ticker)
        assert security["price"] == price
        assert security["effective_market_date"] == "2025-12-30"
