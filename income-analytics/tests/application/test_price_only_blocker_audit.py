"""Investigation must distinguish discovery leads from proven recoveries."""

import importlib.util
from pathlib import Path
from zipfile import ZipFile

SPEC = importlib.util.spec_from_file_location(
    "price_blocker_audit",
    Path(__file__).resolve().parents[2] / "scripts/audit_magic_formula_price_only_blockers.py",
)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_non_trading_reference_date_searches_entire_policy_window(tmp_path, monkeypatch):
    def record(day, ticker, market="010"):
        row = bytearray(b" " * 245)
        row[:2] = b"01"
        row[2:10] = day.encode()
        row[12:24] = ticker.ljust(12).encode()
        row[24:27] = market.encode()
        row[27:39] = b"SAMPLE      "
        return bytes(row) + b"\n"

    archive = tmp_path / "quotes.zip"
    with ZipFile(archive, "w") as file:
        file.writestr(
            "quotes.TXT",
            b"".join(
                [
                    record("20251230", "TEST3"),
                    record("20251224", "TEST4"),
                    record("20251223", "OLDX3"),
                    record("20260102", "NEXT3"),
                    record("20251230", "TEST3F"),
                    record("20251230", "OTHR3", "020"),
                ]
            ),
        )
    monkeypatch.setattr(audit, "ARCHIVE", archive)
    assert audit.official_daily_names("2025-12-31") == {"SAMPLE": {"TEST3", "TEST4"}}


def test_available_share_class_is_not_counted_as_unknown_blocker():
    security = {"ticker": "TEST4", "cotahist_records": [{"effective_date": "2025-12-30"}]}
    assert audit.classification(security, "2025-12-31")[0] == "AVAILABLE"


def test_missing_window_and_unknown_identity_are_distinct():
    security = {"ticker": "TEST3", "cotahist_records": [{"effective_date": "2025-12-23"}]}
    assert audit.classification(security, "2025-12-31")[0] == "SOURCE_MISSING_DATE"
    security["ticker"] = "12345"
    assert audit.classification(security, "2025-12-31")[0] == "UNKNOWN"


def test_future_record_cannot_prove_availability_or_historical_source_gap():
    security = {"ticker": "TEST3", "cotahist_records": [{"effective_date": "2026-01-02"}]}
    assert audit.classification(security, "2025-12-31")[0] == "UNKNOWN"


def test_similar_name_is_never_a_verified_mapping():
    leads = audit.candidate_names("SAMPLE", {"SAMPLE": {"TEST3"}})
    assert leads[0]["status"] == "UNVERIFIED_DISCOVERY_LEAD"
