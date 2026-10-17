"""RANK-001..018 and fail-closed validation-sample regressions."""

import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from itertools import permutations
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from income_analytics.application.magic_formula_contract import is_ranking_eligible
from income_analytics.application.magic_formula_ranking_validation import (
    RankingGateBlocked,
    compare_independent_qa,
    freeze_sample,
    independent_rank_qa,
    ranking_artifact,
)
from income_analytics.application.magic_formula_stocks import MagicFormulaStockRankingService
from income_analytics.infrastructure.magic_formula_contract_repository import (
    CanonicalMagicFormulaRepository,
)
from income_analytics.infrastructure.magic_formula_ranking_repository import (
    MagicFormulaRankingRepository,
)
from tests.application.test_magic_formula_canonical_contract import seed_legacy

ROOT = Path(__file__).resolve().parents[2]
SLUGS = ("petrobras", "weg", "suzano", "rumo", "telefonica")
ENGINE = MagicFormulaStockRankingService()


class MemoryCanonicalRepository:
    def __init__(self, states):
        self.states = deepcopy(states)
        self.override = None
        self.calls = []

    def read_snapshot(self, snapshot_id):
        return next(
            (
                s["snapshot"]
                for s in self.states.values()
                if s["snapshot"] and s["snapshot"]["id"] == snapshot_id
            ),
            None,
        )

    def eligibility(self, issuer_id, reference_date, *, snapshot_id):
        self.calls.append(snapshot_id)
        state = self.states[issuer_id]
        decision = is_ranking_eligible(issuer_id=issuer_id, reference_date=reference_date, **state)
        return self.override(decision) if self.override else decision


@pytest.fixture(scope="module")
def canonical(tmp_path_factory):
    directory = tmp_path_factory.mktemp("ranking-canonical")
    database = directory / "canonical.db"
    fixtures = {
        s: json.loads(
            (ROOT / f"tests/golden/magic_formula/{s}_2025.json").read_text(encoding="utf8")
        )
        for s in SLUGS
    }
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("INCOME_ANALYTICS_DATABASE", str(database))
        config = Config(str(ROOT / "alembic.ini"))
        command.upgrade(config, "0015_magic_formula_fundamentals_snapshots")
        conn = sqlite3.connect(database)
        try:
            for slug, fixture in fixtures.items():
                seed_legacy(conn, slug, fixture)
            conn.commit()
        finally:
            conn.close()
        command.upgrade(config, "head")
    repo = CanonicalMagicFormulaRepository(database)
    states = {}
    for slug, fixture in fixtures.items():
        issuer = fixture["issuer"]["issuer_id"]
        repo.register_issuer(**fixture["issuer"])
        repo.adopt_existing_snapshot("snapshot-" + slug, issuer)
        qid = repo.validate_snapshot("snapshot-" + slug, repo.register_golden(fixture))
        with repo.connection() as conn:
            qa = dict(
                conn.execute("SELECT * FROM magic_formula_formal_qa WHERE id=?", (qid,)).fetchone()
            )
        qa["dimensions"] = json.loads(qa["evidence_json"])
        states[issuer] = dict(
            fixture=fixture, snapshot=repo.read_snapshot("snapshot-" + slug), qa=qa
        )
    bindings = [dict(issuer_id=i, snapshot_id=s["snapshot"]["id"]) for i, s in states.items()]
    sample = freeze_sample(repo, bindings, "2025-12-31")
    return repo, states, sample


@pytest.fixture
def memory(canonical):
    return MemoryCanonicalRepository(canonical[1]), deepcopy(canonical[2])


def artificial():
    return [
        dict(
            issuer_id=i,
            snapshot_id="s" + i,
            qa_id="q" + i,
            snapshot_digest="hash" + i,
            earnings_yield=ey,
            return_on_capital=roc,
        )
        for i, ey, roc in (("A", "0.9", "0.1"), ("B", "0.5", "0.5"), ("C", "0.1", "0.9"))
    ]


def test_rank_001_ey_desc():
    result = ENGINE._rank_approved(artificial())
    assert {r["issuer_id"]: r["earnings_yield_rank"] for r in result} == {"A": 1, "B": 2, "C": 3}


def test_rank_002_roc_desc():
    result = ENGINE._rank_approved(artificial())
    assert {r["issuer_id"]: r["return_on_capital_rank"] for r in result} == {"A": 3, "B": 2, "C": 1}


def test_rank_003_score_is_sum_only():
    assert all(r["magic_formula_score"] == 4 for r in ENGINE._rank_approved(artificial()))


def test_rank_004_score_primary_order():
    values = artificial()
    values[1]["return_on_capital"] = "1.0"
    result = ENGINE._rank_approved(values)
    assert [r["issuer_id"] for r in result] == ["B", "A", "C"]
    assert [r["magic_formula_score"] for r in result] == [3, 4, 5]


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("issuer_status", "NOT_RESOLVED", "ISSUER_NOT_RESOLVED"),
        ("eligible", False, "ISSUER_NOT_RANKING_ELIGIBLE"),
    ],
    ids=["RANK-005", "RANK-006"],
)
def test_resolution_and_eligibility_exclusions(memory, field, value, reason):
    repo, sample = memory
    repo.override = lambda d: replace(d, **{field: value})
    with pytest.raises(RankingGateBlocked) as error:
        ENGINE.rank_validation_sample(sample, repository=repo)
    assert all(reason in x["reason_codes"] for x in error.value.exclusions)


@pytest.mark.parametrize(
    "metric,value,reason",
    [
        ("earnings_yield", None, "MISSING_OR_INVALID_EARNINGS_YIELD"),
        ("return_on_capital", None, "MISSING_OR_INVALID_RETURN_ON_CAPITAL"),
        ("enterprise_value", "0", "NON_POSITIVE_ENTERPRISE_VALUE"),
        ("invested_capital", "-1", "NON_POSITIVE_INVESTED_CAPITAL"),
    ],
    ids=["RANK-007", "RANK-008", "RANK-009", "RANK-010"],
)
def test_invalid_metrics_block_entire_sample(memory, metric, value, reason):
    repo, sample = memory
    state = next(iter(repo.states.values()))
    metrics = json.loads(state["snapshot"]["metrics_json"])
    if value is None:
        del metrics[metric]
    else:
        metrics[metric] = value
    state["snapshot"]["metrics_json"] = json.dumps(metrics)
    with pytest.raises(RankingGateBlocked) as error:
        ENGINE.rank_validation_sample(sample, repository=repo)
    assert reason in error.value.exclusions[0]["reason_codes"]


def test_rank_011_ties_stable_uuid_order():
    expected = ENGINE._rank_approved(artificial())
    for order in permutations(artificial()):
        assert ENGINE._rank_approved(list(order)) == expected
    assert [r["issuer_id"] for r in expected] == ["A", "B", "C"]


def test_rank_012_display_order_is_not_financial_superiority():
    result = ENGINE._rank_approved(artificial())
    assert [r["final_rank"] for r in result] == [1, 1, 1]
    assert [r["final_display_order"] for r in result] == [1, 2, 3]
    assert all(r["score_tied"] and r["magic_formula_score"] == 4 for r in result)


def test_rank_013_frozen_inputs_all_permutations(memory):
    repo, sample = memory
    expected = ENGINE.rank_validation_sample(sample, repository=repo)
    for order in permutations(sample["inputs"]):
        variant = dict(sample, inputs=list(order))
        assert ENGINE.rank_validation_sample(variant, repository=repo) == expected
    assert set(repo.calls) == {i["snapshot_id"] for i in sample["inputs"]}


def test_rank_014_independent_qa_never_calls_engine(memory, monkeypatch):
    repo, sample = memory
    result = ENGINE.rank_validation_sample(sample, repository=repo)
    monkeypatch.setattr(ENGINE, "_rank_approved", lambda *a: pytest.fail("QA_USED_PRODUCTION"))
    assert compare_independent_qa(sample["inputs"], result)["status"] == "PASS"
    result[0]["magic_formula_score"] += 1
    with pytest.raises(ValueError, match="INDEPENDENT_RANKING_QA_FAIL"):
        compare_independent_qa(sample["inputs"], result)


def test_rank_015_wrong_snapshot_qa_cannot_authorize(memory):
    repo, sample = memory
    next(iter(repo.states.values()))["qa"]["snapshot_id"] = "wrong-snapshot"
    with pytest.raises(RankingGateBlocked, match="QA_SNAPSHOT_MISMATCH"):
        ENGINE.rank_validation_sample(sample, repository=repo)


def test_rank_016_v1_excluded(memory):
    repo, sample = memory
    next(iter(repo.states.values()))["snapshot"]["adapter_version"] = "CVM_MAGIC_FORMULA_ADAPTER_V1"
    with pytest.raises(RankingGateBlocked, match="ADAPTER_VERSION_MISMATCH"):
        ENGINE.rank_validation_sample(sample, repository=repo)


def test_rank_017_ranking_persistence_and_new_connection(canonical, tmp_path):
    repo, _, sample = canonical
    artifacts = MagicFormulaRankingRepository(tmp_path / "rankings.db")
    artifacts.initialize()
    artifacts.save_sample(sample, repo)
    frozen = MagicFormulaRankingRepository(artifacts.database).read(sample["sample_id"])
    result = ENGINE.rank_validation_sample(frozen, repository=repo)
    document = ranking_artifact(frozen, result, compare_independent_qa(frozen["inputs"], result))
    artifacts.save_ranking(document, repo)
    assert (
        MagicFormulaRankingRepository(artifacts.database).read(document["ranking_snapshot_id"])
        == document
    )
    with pytest.raises(sqlite3.IntegrityError, match="IMMUTABLE_RANKING_ARTIFACT"):
        with artifacts.connection(write=True) as conn:
            conn.execute("DELETE FROM magic_formula_ranking_artifacts")


def test_rank_018_lineage_bound_to_exact_snapshot_and_qa(memory, tmp_path):
    repo, sample = memory
    result = ENGINE.rank_validation_sample(sample, repository=repo)
    for row in result:
        source = repo.states[row["issuer_id"]]
        assert row["fundamentals_snapshot_id"] == source["snapshot"]["id"]
        assert row["formal_qa_id"] == source["qa"]["id"]
        assert row["adapter_version"] == source["snapshot"]["adapter_version"]
    artifacts = MagicFormulaRankingRepository(tmp_path / "ranking.db")
    artifacts.initialize()
    artifacts.save_sample(sample, repo)
    document = ranking_artifact(sample, result, compare_independent_qa(sample["inputs"], result))
    document["items"][0]["fundamentals_snapshot_id"] = "wrong-snapshot"
    with pytest.raises(ValueError, match="RANKING_LINEAGE_MISMATCH"):
        artifacts.save_ranking(document, repo)


@pytest.mark.parametrize("artifact", ["fixture", "snapshot", "qa"])
def test_petrobras_missing_artifact_regression(memory, artifact):
    repo, sample = memory
    petro = next(s for s in repo.states.values() if s["fixture"]["issuer"]["slug"] == "petrobras")
    petro[artifact] = None
    with pytest.raises(RankingGateBlocked):
        ENGINE.rank_validation_sample(sample, repository=repo)


def test_one_review_dimension_blocks(memory):
    repo, sample = memory
    next(iter(repo.states.values()))["qa"]["dimensions"][0]["status"] = "REVIEW_REQUIRED"
    with pytest.raises(RankingGateBlocked, match="QA_NOT_PASS"):
        ENGINE.rank_validation_sample(sample, repository=repo)


def test_dense_individual_ties_match_independent_qa():
    values = artificial()
    values[1]["earnings_yield"] = values[0]["earnings_yield"]
    values[1]["return_on_capital"] = values[2]["return_on_capital"]
    actual = ENGINE._rank_approved(values)
    assert compare_independent_qa(values, actual)["status"] == "PASS"
    assert {i["earnings_yield_rank"] for i in actual} == {1, 2}


def test_frozen_inputs_cannot_be_replaced_with_latest(memory):
    repo, sample = memory
    next(iter(repo.states.values()))["qa"]["id"] = "newer-qa"
    with pytest.raises(RankingGateBlocked, match="FROZEN_INPUT_OR_QA_CHANGED"):
        ENGINE.rank_validation_sample(sample, repository=repo)


def test_partial_sample_and_duplicates_block_before_calculation(memory, monkeypatch):
    repo, sample = memory
    monkeypatch.setattr(ENGINE, "_rank_approved", lambda *a: pytest.fail("PARTIAL_RANKING"))
    with pytest.raises(RankingGateBlocked, match="EXACTLY_FIVE"):
        ENGINE.rank_validation_sample(dict(sample, inputs=sample["inputs"][:4]), repository=repo)
    with pytest.raises(RankingGateBlocked, match="EXACTLY_FIVE"):
        freeze_sample(repo, [sample["inputs"][0]] * 5, sample["reference_date"])


def test_independent_algorithm_artificial_score_tie():
    result = independent_rank_qa(artificial())
    assert all(r["magic_formula_score"] == 4 and r["final_rank"] == 1 for r in result)
