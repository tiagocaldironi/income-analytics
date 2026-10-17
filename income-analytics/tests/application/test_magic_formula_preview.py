"""Preview is a read-only presentation over the frozen complete-data universe."""

from pathlib import Path

import pytest

from income_analytics.application.magic_formula_preview import build_preview
from income_analytics.application.magic_formula_stocks import MagicFormulaStockRankingService
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)

ROOT = Path(__file__).resolve().parents[2]
BASELINE_SNAPSHOT_ID = "6d418683-6c09-4cfd-a67b-a4cc54718ddd"


@pytest.fixture(scope="module")
def preview():
    universe = MagicFormulaUniverseRepository(
        ROOT / "data/magic_formula/universe_snapshots.db"
    ).read(BASELINE_SNAPSHOT_ID)
    return build_preview(universe)


def test_preview_001_only_complete_data_universe_is_counted(preview):
    assert preview["preview_status"] == "ACTIVE"
    assert preview["preview_eligible_count"] == 178
    assert preview["preview_coverage"] == "57.98"
    assert preview["coverage"] == {
        "companies_analyzed": 178,
        "universe_identified": 307,
        "coverage_percentage": "57.98",
        "awaiting_complete_data": 129,
        "ranked_companies": 174,
        "not_ranked": 4,
    }


def test_preview_002_uses_the_validated_ranking_engine(monkeypatch):
    universe = MagicFormulaUniverseRepository(
        ROOT / "data/magic_formula/universe_snapshots.db"
    ).read(BASELINE_SNAPSHOT_ID)
    calls = []
    original = MagicFormulaStockRankingService._rank_approved

    def tracked(inputs):
        calls.append(len(inputs))
        return original(inputs)

    monkeypatch.setattr(MagicFormulaStockRankingService, "_rank_approved", staticmethod(tracked))
    preview = build_preview(universe)
    assert calls == [174]
    assert len(preview["items"]) == 174


def test_preview_003_production_gate_stays_blocked(preview):
    assert preview["ranking_gate"] == "BLOCKED"
    assert preview["ranking_status"] == "INACTIVE"
    assert all(item["final_rank"] >= 1 for item in preview["items"])
    assert {item["reason_code"] for item in preview["not_ranked"]} == {
        "NON_POSITIVE_INVESTED_CAPITAL"
    }


def test_preview_current_snapshot_counts_are_derived_from_eligible_issuers():
    universe = MagicFormulaUniverseRepository(
        ROOT / "data/magic_formula/universe_snapshots.db"
    ).latest()
    result = build_preview(universe)
    complete = {
        i["issuer_id"]
        for i in universe["issuers"]
        if i["methodology_eligibility"] == "ELIGIBLE"
        and i["data_readiness_status"] == "FULL_DATA_READY"
    }
    assert result["preview_eligible_count"] == len(complete)
    assert {i["issuer_id"] for i in result["items"] + result["not_ranked"]} == complete
    assert result["coverage"]["ranked_companies"] + result["coverage"]["not_ranked"] == len(
        complete
    )
    assert result["ranking_gate"] == "BLOCKED"
    assert result["ranking_status"] == "INACTIVE"
