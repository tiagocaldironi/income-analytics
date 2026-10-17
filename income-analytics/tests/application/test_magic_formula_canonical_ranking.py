from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from income_analytics.application.magic_formula_canonical_ranking import (
    MagicFormulaCanonicalRankingRepository,
    build_canonical_snapshot,
    ranking_read_model,
)
from income_analytics.application.magic_formula_contract import digest


def test_builds_a_deterministic_ranking_with_temporal_provenance() -> None:
    first = build_canonical_snapshot(created_at="2026-10-13T12:00:00Z")
    second = build_canonical_snapshot(created_at="2026-10-13T12:00:00Z")

    assert first["policy_id"] == "MF_BR_2027_V1"
    assert (
        first["policy_hash"] == "96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac"
    )
    assert first["ranking_hash"] == second["ranking_hash"]
    assert first["rankable_companies"] == 174
    assert len(first["metric_non_rankable"]) == 6
    assert len(first["provenance"]) == 174
    assert all(row["filing_date"] <= first["accounting_cutoff"] for row in first["results"])
    assert all(
        row["price_reference_date"] <= first["ranking_reference_date"] for row in first["results"]
    )
    assert all(
        row["combined_score"] == row["earnings_yield_rank"] + row["return_on_capital_rank"]
        for row in first["results"]
    )
    assert digest(first["results"]) != first["ranking_hash"]


def test_screening_search_and_pagination_preserve_global_rank() -> None:
    snapshot = build_canonical_snapshot(created_at="2026-10-13T12:00:00Z")
    full = ranking_read_model(snapshot, page=1, page_size=100)
    filtered = ranking_read_model(snapshot, exclude_retail=True, page=1, page_size=100)
    search = ranking_read_model(snapshot, query="WEGE3")
    second_page = ranking_read_model(snapshot, page=2, page_size=10)

    assert full["total"] == 174
    assert filtered["total"] < full["total"]
    assert {row["global_rank"] for row in filtered["items"]}.issubset(
        {row["global_rank"] for row in snapshot["results"]}
    )
    assert search["total"] == 1
    assert search["items"][0]["selected_security"] == "WEGE3"
    assert second_page["page"] == 2
    assert second_page["items"][0]["global_rank"] > 1


def test_snapshot_repository_is_append_only_and_idempotent(tmp_path: Path) -> None:
    snapshot = build_canonical_snapshot(created_at="2026-10-13T12:00:00Z")
    repository = MagicFormulaCanonicalRankingRepository(tmp_path / "rankings.db")
    repository.save(snapshot, initial_release_status="STAGED")
    repository.save(snapshot)

    assert repository.latest() is None
    assert (
        repository.read(snapshot["ranking_snapshot_id"])["ranking_hash"] == snapshot["ranking_hash"]
    )
    repository.record_release_event(
        snapshot["ranking_snapshot_id"],
        "PUBLISHED",
        "RELEASE_GATES_PASSED",
        created_at="2026-10-16T11:59:00Z",
    )
    assert repository.latest()["ranking_hash"] == snapshot["ranking_hash"]
    repository.record_release_event(
        snapshot["ranking_snapshot_id"],
        "INVALIDATED",
        "TEMPORAL_LOOKAHEAD",
        created_at="2026-10-16T12:00:00Z",
    )
    assert repository.latest() is None
    with pytest.raises(ValueError, match="INVALIDATED_SNAPSHOT_CANNOT_BE_REPUBLISHED"):
        repository.record_release_event(
            snapshot["ranking_snapshot_id"],
            "PUBLISHED",
            "TEMPORAL_VALIDATION_PASS",
            created_at="2026-10-16T12:01:00Z",
        )
    with sqlite3.connect(repository.database) as connection, pytest.raises(sqlite3.DatabaseError):
        connection.execute(
            "UPDATE magic_formula_ranking_snapshots SET policy_hash='changed' "
            "WHERE ranking_snapshot_id=?",
            (snapshot["ranking_snapshot_id"],),
        )


def test_no_snapshot_and_invalid_page_are_explicit() -> None:
    assert ranking_read_model(None)["snapshot_available"] is False
    with pytest.raises(ValueError, match="INVALID_PAGINATION"):
        ranking_read_model({}, page=0)
