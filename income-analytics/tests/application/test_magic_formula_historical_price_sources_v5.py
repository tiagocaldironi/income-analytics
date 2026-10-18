"""V5 source-expansion and immutable snapshot selection regressions."""

import sqlite3
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

import pytest

from income_analytics.application.magic_formula_universe import coverage
from income_analytics.infrastructure.magic_formula_historical_price_sources import (
    build_price_provenance,
    compare_source_prices,
    exact_price_candidate,
    scan_cotahist_archive,
)
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)

IDENTITY = {
    "ticker": "TEST3",
    "isin": "BRTESTACNOR1",
    "security_class": "ON",
    "issuer_confirmed": True,
    "identity_source": "B3-directory|cvm=000001|isin=BRTESTACNOR1",
}


def cotahist_row(
    *,
    date="20251230",
    ticker="TEST3",
    isin="BRTESTACNOR1",
    market="010",
    spec="ON NM",
    price="0000000012345",
):
    row = bytearray(b" " * 245)
    row[:2] = b"01"
    row[2:10] = date.encode("ascii")
    row[12:24] = ticker.encode("ascii").ljust(12)
    row[24:27] = market.encode("ascii")
    row[39:49] = spec.encode("ascii").ljust(10)
    row[108:121] = price.encode("ascii")
    row[230:242] = isin.encode("ascii")
    return bytes(row) + b"\n"


def archive(path, *rows):
    with ZipFile(path, "w") as output:
        output.writestr(path.stem + ".TXT", b"00HEADER\n" + b"".join(rows) + b"99TRAILER\n")


def snapshot(snapshot_id, created_at):
    issuers = []
    return {
        "universe_snapshot_id": snapshot_id,
        "reference_date": "2025-12-31",
        "universe_policy_version": "test-v1",
        "created_at": created_at,
        "universe_type": "CANDIDATE_PUBLISHABLE_UNIVERSE",
        "issuers": issuers,
        "coverage": coverage(issuers),
        "tool_status": "VALIDATION_REQUIRED",
        "ranking_status": "INACTIVE",
    }


def test_cotahist_scan_matches_exact_ticker_or_isin_and_records_manifest(tmp_path):
    path = tmp_path / "COTAHIST_A2021.ZIP"
    archive(path, cotahist_row(ticker="OLD3"))
    rows, manifest = scan_cotahist_archive(
        path,
        [IDENTITY],
        source_url="https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2021.ZIP",
        retrieved_at="2026-10-12T00:00:00+00:00",
    )
    result = rows["TEST3|BRTESTACNOR1"]
    assert len(result) == 1 and result[0]["isin_match"] is True
    assert result[0]["ticker_match"] is False
    assert result[0]["price_field"] == "PREULT" and result[0]["price"] == "123.45"
    assert manifest["year"] == 2021 and manifest["scan_complete"] is True
    assert manifest["source"] == "B3" and len(manifest["sha256"]) == 64
    assert manifest["download_reference_location"].endswith("COTAHIST_A2021.ZIP")


def test_ticker_match_with_wrong_isin_cannot_supply_price():
    record = {
        "ticker": "TEST3",
        "isin": "BRWRNGACNOR0",
        "security_class": "ON",
        "market_type": "010",
        "date": "2025-12-30",
        "price": "12.34",
    }
    result = exact_price_candidate(IDENTITY, [record], "2025-12-30")
    assert result == {"status": "MISSING", "reason": "NO_MATCHING_ISIN"}


def test_correct_isin_with_historical_ticker_is_validated_by_identity():
    record = {
        "ticker": "OLD3",
        "isin": IDENTITY["isin"],
        "security_class": "ON",
        "market_type": "010",
        "date": "2025-12-30",
        "price": "12.34",
        "source_dataset": "B3_COTAHIST",
        "source_record_identifier": "COTAHIST_A2025.ZIP|COTAHIST_A2025.TXT|line=3",
    }
    assert exact_price_candidate(IDENTITY, [record], "2025-12-30")["status"] == "CANDIDATE"


def test_wrong_class_is_rejected_even_when_ticker_is_present():
    wrong_class = {**IDENTITY, "security_class": "PN"}
    assert (
        exact_price_candidate(wrong_class, [], "2025-12-30")["reason"] == "CLASS_OR_ISIN_MISMATCH"
    )
    wrong_spec = {
        "ticker": "TEST3",
        "isin": IDENTITY["isin"],
        "security_class": "PN",
        "market_type": "010",
        "date": "2025-12-30",
        "price": "12.34",
    }
    assert exact_price_candidate(IDENTITY, [wrong_spec], "2025-12-30")["reason"] == "CLASS_MISMATCH"


def test_fractional_market_020_is_never_accepted_as_010():
    record = {
        "ticker": "TEST3",
        "isin": IDENTITY["isin"],
        "security_class": "ON",
        "market_type": "020",
        "date": "2025-12-30",
        "price": "12.34",
    }
    result = exact_price_candidate(IDENTITY, [record], "2025-12-30")
    assert result == {"status": "MISSING", "reason": "PRICE_EXISTS_BUT_POLICY_INCOMPATIBLE"}


def test_historical_or_future_record_cannot_replace_exact_reference_date():
    record = {
        "ticker": "TEST3",
        "isin": IDENTITY["isin"],
        "security_class": "ON",
        "market_type": "010",
        "date": "2022-06-30",
        "price": "10.00",
    }
    future = {**record, "date": "2026-01-02", "price": "99.99"}
    for row in (record, future):
        result = exact_price_candidate(IDENTITY, [row], "2025-12-30")
        assert result == {"status": "MISSING", "reason": "PRICE_EXISTS_BUT_POLICY_INCOMPATIBLE"}


def test_source_conflicts_are_reported_without_selecting_a_winner():
    same = compare_source_prices("12.34", "12.34")
    assert same["status"] == "CONSISTENT" and same["abs_diff"] == "0.00"
    conflict = compare_source_prices("12.34", "12.40")
    assert conflict["status"] == "SOURCE_CONFLICT"
    assert Decimal(conflict["pct_diff"]) > 0


def test_high_confidence_provenance_is_complete_and_fail_closed():
    record = {
        "ticker": "TEST3",
        "isin": IDENTITY["isin"],
        "security_class": "ON",
        "market_type": "010",
        "date": "2025-12-30",
        "price": "12.34",
        "source_dataset": "B3_COTAHIST",
        "source_record_identifier": "COTAHIST_A2025.ZIP|COTAHIST_A2025.TXT|line=3",
    }
    provenance = build_price_provenance(
        IDENTITY, record, reference_date="2025-12-30", retrieved_at="2026-10-12T00:00:00Z"
    )
    assert provenance["identity_confidence"] == provenance["price_confidence"] == "HIGH"
    assert provenance["source_field"] == "PREULT" and provenance["market_type"] == "010"
    assert provenance["isin"] == IDENTITY["isin"] and provenance["reference_date"] == "2025-12-30"
    assert "source_record_identifier" in provenance
    with pytest.raises(ValueError, match="ISSUER_IDENTITY_PROVENANCE_REQUIRED"):
        build_price_provenance(
            {**IDENTITY, "issuer_confirmed": False},
            record,
            reference_date="2025-12-30",
            retrieved_at="2026-10-12T00:00:00Z",
        )


def test_no_price_is_not_synthesized_as_zero():
    result = exact_price_candidate(IDENTITY, [], "2025-12-30")
    assert result["status"] == "MISSING" and "price" not in result


def test_same_timestamp_selects_later_inserted_and_preserves_old_snapshot(tmp_path):
    repository = MagicFormulaUniverseRepository(tmp_path / "snapshots.db")
    repository.initialize()
    first = snapshot("z-published-first", "2026-10-12T20:00:00+00:00")
    second = snapshot("a-published-second", "2026-10-12T20:00:00+00:00")
    repository.save(first)
    repository.save(second)
    assert repository.latest()["universe_snapshot_id"] == "a-published-second"
    assert repository.read("z-published-first") == first
    with repository.connection() as connection:
        tie_count = connection.execute(
            "SELECT COUNT(*) FROM magic_formula_universe_snapshots WHERE created_at=?",
            (first["created_at"],),
        ).fetchone()[0]
    assert tie_count == 2


def test_later_unique_timestamp_wins_over_tie_and_duplicate_save_is_idempotent(tmp_path):
    repository = MagicFormulaUniverseRepository(tmp_path / "snapshots.db")
    repository.initialize()
    first = snapshot("first", "2026-10-12T20:00:00+00:00")
    second = snapshot("second", "2026-10-12T20:00:00+00:00")
    latest = snapshot("latest", "2026-10-12T20:01:00+00:00")
    for document in (first, second, latest):
        repository.save(document)
    assert repository.latest()["universe_snapshot_id"] == "latest"
    with pytest.raises(sqlite3.IntegrityError):
        repository.save(latest)
    assert repository.read("first") == first
    assert repository.latest()["universe_snapshot_id"] == "latest"


def test_production_snapshot_readback_is_independent_and_idempotent():
    repository = MagicFormulaUniverseRepository(Path("data/magic_formula/universe_snapshots.db"))
    with repository.connection() as connection:
        before = connection.execute(
            "SELECT COUNT(*), MAX(created_at) FROM magic_formula_universe_snapshots"
        ).fetchone()
    first_read = repository.read("ed8a9235-ee14-4a97-93fd-0dbcd87113fb")
    second_read = repository.read("ed8a9235-ee14-4a97-93fd-0dbcd87113fb")
    with repository.connection() as connection:
        after = connection.execute(
            "SELECT COUNT(*), MAX(created_at) FROM magic_formula_universe_snapshots"
        ).fetchone()
    assert first_read == second_read
    assert after == before
    assert first_read["ranking_status"] == "INACTIVE"
    assert first_read["tool_status"] == "VALIDATION_REQUIRED"
