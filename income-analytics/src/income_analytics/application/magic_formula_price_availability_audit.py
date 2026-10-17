"""Read-only close selection and coverage scenarios for price availability audits."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

POLICIES = {
    "EXACT_DATE_ONLY": 0,
    "WITHIN_1_DAY": 1,
    "WITHIN_3_DAYS": 3,
    "WITHIN_5_DAYS": 5,
    "WITHIN_7_DAYS": 7,
    "WITHIN_30_DAYS": 30,
}


def _class_matches(security: dict) -> bool:
    ticker = security.get("ticker", "")
    isin = security.get("isin", "")
    share_class = security.get("share_class", "")
    suffix_map = {
        "3": ("ON", "CNOR"),
        "4": ("PN", "CNPR"),
        "5": ("PNA", "CNPA"),
        "6": ("PNB", "CNPB"),
    }
    expected = suffix_map.get(ticker[-1:] if ticker else "")
    return bool(expected and len(isin) == 12 and expected == (share_class, isin[7:11]))


def select_close(
    security: dict, records: list[dict], reference_date: str, max_calendar_days: int = 0
) -> dict:
    """Select exact security close on/before date; future rows are never eligible."""
    reference = date.fromisoformat(reference_date)
    if not _class_matches(security):
        return {"status": "REJECTED", "reason": "CLASS_OR_IDENTIFIER_MISMATCH"}
    matches = [
        row
        for row in records
        if row.get("ticker") == security["ticker"]
        and row.get("isin") == security["isin"]
        and row.get("market") == "010"
        and date.fromisoformat(row["date"]) <= reference
        and (reference - date.fromisoformat(row["date"])).days <= max_calendar_days
    ]
    if not matches:
        any_prior = any(
            row.get("ticker") == security["ticker"]
            and row.get("isin") == security["isin"]
            and row.get("market") == "010"
            and date.fromisoformat(row["date"]) <= reference
            for row in records
        )
        return {
            "status": "MISSING",
            "reason": "OUTSIDE_WINDOW" if any_prior else "NO_PREVIOUS_PRICE",
        }
    latest = max(row["date"] for row in matches)
    closes = [row for row in matches if row["date"] == latest]
    if len(closes) != 1:
        return {"status": "AMBIGUOUS", "reason": "DUPLICATE_CLOSE_DATE"}
    row = closes[0]
    return {
        "status": "RESOLVED",
        "reason": None,
        "effective_date": latest,
        "calendar_days_gap": (reference - date.fromisoformat(latest)).days,
        "price": Decimal(row["price"]),
        "ticker": row["ticker"],
        "isin": row["isin"],
        "market": row["market"],
        "source": row.get("source"),
        "security_class": security["share_class"],
    }


def project_scenarios(
    base_complete: int,
    universe_size: int,
    cases: list[dict],
    technical_issuer_ids: set[str] | None = None,
    blocked_unresolved: int = 0,
) -> list[dict]:
    """Count a company only when every missing security has a price in a policy."""
    technical_issuer_ids = technical_issuer_ids or set()
    by_id = {case["issuer_id"]: case for case in cases}
    rows = [
        {
            "scenario": "BASELINE",
            "price_recoveries": 0,
            "security_price_recoveries": 0,
            "complete_companies": base_complete,
            "coverage_percent": round(100 * base_complete / universe_size, 2),
            "remaining_price_blockers": len(cases) + blocked_unresolved,
            "methodology_changed": False,
        }
    ]
    for label, days in POLICIES.items():
        recoverable = {
            issuer_id
            for issuer_id, case in by_id.items()
            if case.get("securities")
            and all(
                select_close(security, security.get("records", []), case["reference_date"], days)[
                    "status"
                ]
                == "RESOLVED"
                for security in case["securities"]
            )
        }
        recovered_security_count = sum(
            select_close(security, security.get("records", []), case["reference_date"], days)[
                "status"
            ]
            == "RESOLVED"
            for case in cases
            for security in case.get("securities", [])
        )
        combined = recoverable | technical_issuer_ids
        # A company-level technical recovery is counted only if the evidence marks
        # every missing class recovered; caller supplies only complete issuer IDs.
        complete_companies = base_complete + len(combined)
        rows.append(
            {
                "scenario": label,
                "price_recoveries": len(recoverable),
                "security_price_recoveries": recovered_security_count,
                "complete_companies": complete_companies,
                "coverage_percent": round(100 * complete_companies / universe_size, 2),
                "remaining_price_blockers": len(cases) + blocked_unresolved - len(combined),
                "methodology_changed": days > 0,
            }
        )
    return rows


def classify_unavailable(evidence: dict) -> str:
    """Prioritize specific evidence; default only to a documented source gap."""
    if evidence.get("accepted_source_price_found"):
        return "LOOKUP_BUG"
    if evidence.get("same_isin_other_ticker_found"):
        return "HISTORICAL_TICKER_LOOKUP_GAP"
    if evidence.get("same_security_other_market_only"):
        return "SECURITY_TYPE_NOT_COVERED"
    if evidence.get("official_alternative_dataset_price_found"):
        return "ALTERNATIVE_B3_DATASET_REQUIRED"
    if evidence.get("corporate_action_break_proven"):
        return "CORPORATE_ACTION_LOOKUP_GAP"
    if evidence.get("not_listed_at_reference"):
        return "LISTING_DATE_GAP"
    if evidence.get("delisted_at_reference"):
        return "DELISTING_DATE_GAP"
    if evidence.get("archive_expected_but_missing"):
        return "DATASET_GAP"
    if evidence.get("official_source_scanned_no_valid_close"):
        return "SOURCE_GAP"
    raise ValueError("CAUSE_NOT_EVIDENCED")


def audit_snapshot_order(rows: list[tuple[int, str, str]]) -> dict:
    """Audit created_at ordering with SQLite's immutable insertion sequence."""
    rowids = [int(rowid) for rowid, _, _ in rows]
    timestamps = [created_at for _, _, created_at in rows]
    duplicate_timestamps = len(timestamps) != len(set(timestamps))
    stable_rowids = len(rowids) == len(set(rowids))
    return {
        "selection_query": "ORDER BY created_at DESC, rowid DESC",
        "stable_tie_breaker": "SQLite immutable insertion rowid",
        "deterministic": stable_rowids,
        "ordering_risk": not stable_rowids,
        "duplicate_timestamps_present": duplicate_timestamps,
        "duplicate_created_at": sorted({t for t in timestamps if timestamps.count(t) > 1}),
    }
