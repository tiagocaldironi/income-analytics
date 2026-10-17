"""CONTRACT-001..015: persisted canonical state and adversarial eligibility."""

import json
import runpy
import sqlite3
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest
from alembic.config import Config

from alembic import command
from income_analytics.application.magic_formula_contract import (
    ADAPTER_VERSION,
    DIMENSIONS,
    FINANCIAL_METRICS,
    GOLDEN_SCHEMA_VERSION,
    DimensionDecision,
    ValidationStatus,
    canonicalize_golden,
    final_qa_status,
    is_ranking_eligible,
)
from income_analytics.application.magic_formula_formal_qa import evaluate_formal_qa
from income_analytics.application.magic_formula_lineage_gate import MagicFormulaLineageGate
from income_analytics.infrastructure.magic_formula_contract_repository import (
    CanonicalMagicFormulaRepository,
)

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ("weg", "suzano", "rumo", "telefonica")


def seed_legacy(conn, slug, fixture):
    metrics = dict(fixture["expected"])
    metrics.update(
        issuer_id=slug, cvm_code=fixture["issuer"]["cvm_code"], validation_status="NOT_VALIDATED"
    )
    lineage = []
    for metric, group in fixture["accounting"].items():
        for source in group["components"]:
            item = dict(source, metric=metric, rule_id=group["rule_id"])
            item["normalized_value"] = item.pop("normalized_expected_value")
            item["multiplier"] = item.pop("normalization_multiplier")
            lineage.append(item)
    caps = []
    for cap in fixture["capital"]["securities"]:
        price = next(p for p in fixture["prices"] if p["ticker"] == cap["ticker"])
        item = dict(
            cap,
            issued_shares=cap["issued_or_integralized_shares"],
            price=price["price"],
            price_record_reference=price["record_reference"],
            price_effective_date=price["effective_date"],
        )
        caps.append(item)
    lineage.append({"market_cap_components": caps})
    conn.execute(
        "INSERT INTO magic_formula_fundamentals_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "snapshot-" + slug,
            slug,
            "2025-12-31",
            "2025-12-31",
            "DFP",
            "CONSOLIDATED",
            ADAPTER_VERSION,
            "VALID",
            "PASS",
            json.dumps(metrics),
            json.dumps(lineage),
            "2026-09-13 19:40:00",
        ),
    )


@pytest.fixture
def foundation(tmp_path, monkeypatch):
    db = tmp_path / "contract.db"
    monkeypatch.setenv("INCOME_ANALYTICS_DATABASE", str(db))
    config = Config(str(ROOT / "alembic.ini"))
    command.upgrade(config, "0015_magic_formula_fundamentals_snapshots")
    directory = tmp_path / "golden"
    directory.mkdir()
    with sqlite3.connect(db) as conn:
        for slug in SAMPLE:
            fixture = json.loads(
                (ROOT / f"tests/golden/magic_formula/{slug}_2025.json").read_text(encoding="utf8")
            )
            (directory / f"{slug}_2025.json").write_text(json.dumps(fixture), encoding="utf8")
            seed_legacy(conn, slug, fixture)
    command.upgrade(config, "head")
    return db, directory, CanonicalMagicFormulaRepository(db)


def prepare(foundation, *, approve=True):
    db, directory, repo = foundation
    fixture = json.loads((directory / "weg_2025.json").read_text(encoding="utf8"))
    cap = fixture["capital"]["securities"][0]
    issuer = repo.register_issuer(
        cvm_code=fixture["issuer"]["cvm_code"],
        cnpj=cap["fca_source_reference"].split("|")[2],
        display_name="WEG",
        slug="weg",
        issuer_id=fixture["issuer"]["issuer_id"] if fixture.get("schema_version") else None,
    )
    canonical = canonicalize_golden(fixture, issuer)
    repo.adopt_existing_snapshot("snapshot-weg", issuer["issuer_id"])
    fixture_hash = repo.register_golden(canonical)
    if approve:
        repo.validate_snapshot("snapshot-weg", fixture_hash)
    return issuer, canonical, fixture_hash


def policy_inputs(foundation):
    issuer, fixture, _ = prepare(foundation)
    repo = foundation[2]
    with repo.connection() as conn:
        qa = dict(conn.execute("SELECT * FROM magic_formula_formal_qa").fetchone())
    qa["dimensions"] = json.loads(qa["evidence_json"])
    return dict(
        issuer_id=issuer["issuer_id"],
        reference_date="2025-12-31",
        snapshot=repo.read_snapshot("snapshot-weg"),
        qa=qa,
        fixture=fixture,
    )


def test_contract_001_identity_independent_of_ticker_name_slug(foundation):
    issuer, _, _ = prepare(foundation)
    same = foundation[2].register_issuer(
        cvm_code="5410", cnpj=issuer["cnpj"], display_name="renamed", slug="new-presentation-slug"
    )
    assert same["issuer_id"] == issuer["issuer_id"]
    assert str(UUID(issuer["issuer_id"])) == issuer["issuer_id"]
    assert issuer["issuer_id"] not in ("WEGE3", "weg", "005410")
    with pytest.raises(ValueError, match="IDENTITY_CONFLICT"):
        foundation[2].register_issuer(
            cvm_code="5410", cnpj="12345678901234", display_name="x", slug="x"
        )


def test_contract_002_golden_schema_and_lineage_preserved(foundation):
    old = json.loads((foundation[1] / "weg_2025.json").read_text())
    _, fixture, _ = prepare(foundation)
    assert fixture["schema_version"] == GOLDEN_SCHEMA_VERSION
    assert fixture["expected"] == old["expected"]
    assert fixture["accounting"] == old["accounting"]
    assert fixture["prices"] == old["prices"]
    assert MagicFormulaLineageGate().evaluate(fixture).complete
    fixture.pop("schema_version")
    assert not MagicFormulaLineageGate().evaluate(fixture).complete


def test_contract_003_only_column_can_store_validation(foundation):
    repo = foundation[2]
    snapshot = repo.read_snapshot("snapshot-weg")
    assert snapshot["validation_status"] == "REVIEW_REQUIRED"  # legacy PASS is not evidence
    assert "validation_status" not in json.loads(snapshot["metrics_json"])
    with pytest.raises(sqlite3.IntegrityError, match="NON_CANONICAL"):
        with repo.connection(write=True) as conn:
            conn.execute(
                "UPDATE magic_formula_fundamentals_snapshots SET metrics_json="
                "json_set(metrics_json,'$.validation_status','PASS') WHERE id='snapshot-weg'"
            )


def test_contract_004_pass_requires_bound_qa(foundation):
    repo = foundation[2]
    prepare(foundation, approve=False)
    with pytest.raises(sqlite3.IntegrityError, match="PASS_REQUIRES"):
        with repo.connection(write=True) as conn:
            conn.execute(
                "UPDATE magic_formula_fundamentals_snapshots SET validation_status='PASS' "
                "WHERE id='snapshot-weg'"
            )


def test_contract_005_qa_a_cannot_validate_b(foundation):
    inputs = policy_inputs(foundation)
    inputs["snapshot"]["id"] = "snapshot-B"
    result = is_ranking_eligible(**inputs)
    assert not result.eligible and "QA_SNAPSHOT_MISMATCH" in result.reasons
    with pytest.raises(sqlite3.IntegrityError, match="PASS_REQUIRES"):
        with foundation[2].connection(write=True) as conn:
            conn.execute(
                "UPDATE magic_formula_fundamentals_snapshots SET validation_status='PASS' "
                "WHERE id='snapshot-suzano'"
            )


@pytest.mark.parametrize("dimension", DIMENSIONS)
def test_contract_006_one_review_blocks_final_pass(dimension):
    decisions = tuple(DimensionDecision(d, ValidationStatus.PASS, ("source",)) for d in DIMENSIONS)
    decisions = tuple(
        replace(d, status=ValidationStatus.REVIEW_REQUIRED) if d.dimension == dimension else d
        for d in decisions
    )
    assert final_qa_status(decisions) == ValidationStatus.REVIEW_REQUIRED


def test_contract_007_resolution_requires_snapshot_validation_and_qa(foundation):
    inputs = policy_inputs(foundation)
    assert is_ranking_eligible(**inputs).issuer_status == "RESOLVED"
    inputs["qa"] = None
    assert is_ranking_eligible(**inputs).issuer_status == "NOT_RESOLVED"


def test_contract_008_no_snapshot_cannot_be_resolved(foundation):
    inputs = policy_inputs(foundation)
    inputs["snapshot"] = None
    result = is_ranking_eligible(**inputs)
    assert not result.eligible and result.issuer_status == "NOT_RESOLVED"


@pytest.mark.parametrize("missing", ["snapshot", "qa", "fixture"])
def test_contract_009_fail_closed(foundation, missing):
    inputs = policy_inputs(foundation)
    inputs[missing] = None
    assert not is_ranking_eligible(**inputs).eligible


def test_contract_010_incompatible_reference_blocks(foundation):
    inputs = policy_inputs(foundation)
    inputs["reference_date"] = "2024-12-31"
    assert "REFERENCE_DATE_MISMATCH" in is_ranking_eligible(**inputs).reasons


def test_contract_011_incompatible_adapter_blocks(foundation):
    inputs = policy_inputs(foundation)
    inputs["snapshot"]["adapter_version"] = "CVM_MAGIC_FORMULA_ADAPTER_V1"
    assert "ADAPTER_VERSION_MISMATCH" in is_ranking_eligible(**inputs).reasons


@pytest.mark.parametrize("bad", [None, "NaN", "Infinity"])
def test_contract_012_missing_metric_never_zero(foundation, bad):
    inputs = policy_inputs(foundation)
    metrics = json.loads(inputs["snapshot"]["metrics_json"])
    metrics["ebit"] = bad
    inputs["snapshot"]["metrics_json"] = json.dumps(metrics)
    assert "FINANCIAL_INELIGIBILITY" in is_ranking_eligible(**inputs).reasons
    assert metrics["ebit"] == bad


def test_contract_013_petrobras_stays_missing(foundation):
    decision = foundation[2].eligibility("petrobras", "2025-12-31")
    assert not decision.eligible
    assert decision.issuer_status == "NOT_RESOLVED"
    assert {"MISSING_GOLDEN", "MISSING_VALIDATED_SNAPSHOT", "MISSING_FORMAL_QA"} <= set(
        decision.reasons
    )


def test_contract_014_readback_and_immutability(foundation):
    issuer, _, fixture_hash = prepare(foundation)
    db = foundation[0]
    fresh = CanonicalMagicFormulaRepository(db)
    decision = fresh.eligibility(issuer["issuer_id"], "2025-12-31")
    assert decision.eligible and decision.issuer_status == "RESOLVED"
    assert fresh.validate_snapshot("snapshot-weg", fixture_hash) == decision.qa_decision_id
    with pytest.raises(sqlite3.IntegrityError, match="IMMUTABLE"):
        with fresh.connection(write=True) as conn:
            conn.execute("UPDATE magic_formula_formal_qa SET final_status='FAIL'")
    with pytest.raises(sqlite3.IntegrityError, match="IMMUTABLE"):
        with fresh.connection(write=True) as conn:
            conn.execute(
                "UPDATE magic_formula_fundamentals_snapshots SET metrics_json='{}' "
                "WHERE id='snapshot-weg'"
            )


def test_contract_015_four_existing_migrate_without_financial_changes(foundation):
    db, directory, repo = foundation
    before = {slug: repo.read_snapshot("snapshot-" + slug) for slug in SAMPLE}
    migrate = runpy.run_path(str(ROOT / "scripts/migrate_magic_formula_contract.py"))[
        "migrate_existing"
    ]
    result = migrate(db, directory)
    assert len(result) == 4 and all(r["eligibility"]["eligible"] for r in result)
    again = migrate(db, directory)
    assert [r["qa_decision_id"] for r in again] == [r["qa_decision_id"] for r in result]
    for slug in SAMPLE:
        after = repo.read_snapshot("snapshot-" + slug)
        old_values, new_values = (
            json.loads(before[slug]["metrics_json"]),
            json.loads(after["metrics_json"]),
        )
        assert {k: old_values[k] for k in FINANCIAL_METRICS} == {
            k: new_values[k] for k in FINANCIAL_METRICS
        }
        assert before[slug]["lineage_json"] == after["lineage_json"]


def test_missing_locator_produces_review_not_eight_passes(foundation):
    issuer, fixture, _ = prepare(foundation, approve=False)
    fixture["capital"]["securities"][0].pop("treasury_source_reference")
    repo = foundation[2]
    key = repo.register_golden(fixture)
    repo.validate_snapshot("snapshot-weg", key)
    assert repo.read_snapshot("snapshot-weg")["validation_status"] == "REVIEW_REQUIRED"
    assert not repo.eligibility(issuer["issuer_id"], "2025-12-31").eligible


def test_later_failure_revokes_eligibility_without_deleting_qa(foundation):
    issuer, fixture, _ = prepare(foundation)
    fixture = deepcopy(fixture)
    fixture["expected"]["ebit"] = "1"
    repo = foundation[2]
    key = repo.register_golden(fixture)
    repo.validate_snapshot("snapshot-weg", key)
    assert repo.read_snapshot("snapshot-weg")["validation_status"] == "FAIL"
    assert not repo.eligibility(issuer["issuer_id"], "2025-12-31").eligible
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) FROM magic_formula_formal_qa").fetchone()[0] == 2


def test_missing_readback_cannot_pass(foundation):
    _, fixture, _ = prepare(foundation, approve=False)
    dims = evaluate_formal_qa(
        fixture, foundation[2].read_snapshot("snapshot-weg"), readback_matches=False
    )
    assert final_qa_status(dims) != ValidationStatus.PASS


def test_malformed_qa_dimensions_fail_closed(foundation):
    inputs = policy_inputs(foundation)
    inputs["qa"]["dimensions"] = [{"status": "garbage"}]
    result = is_ranking_eligible(**inputs)
    assert not result.eligible and "QA_NOT_PASS" in result.reasons


def test_empty_evidence_is_persisted_as_review(foundation):
    issuer, fixture, _ = prepare(foundation, approve=False)
    fixture["security"] = []
    repo = foundation[2]
    fixture_hash = repo.register_golden(fixture)
    repo.validate_snapshot("snapshot-weg", fixture_hash)
    assert repo.read_snapshot("snapshot-weg")["validation_status"] == "REVIEW_REQUIRED"
    assert not repo.eligibility(issuer["issuer_id"], "2025-12-31").eligible


def test_canonical_release_gate_remains_blocked(foundation):
    from income_analytics.application.investment_tools import TOOLS, ranking_contract
    from income_analytics.application.magic_formula_activation_gate import (
        MagicFormulaActivationGate,
    )

    db, directory, repo = foundation
    migrate = runpy.run_path(str(ROOT / "scripts/migrate_magic_formula_contract.py"))[
        "migrate_existing"
    ]
    migrated = migrate(db, directory)
    gate = MagicFormulaActivationGate().evaluate_canonical(
        repo,
        tuple(item["issuer_id"] for item in migrated),
        "2025-12-31",
    )
    assert gate.resolved_issuers == 4
    assert gate.ranked_issuers == 0
    assert gate.tool_status == "VALIDATION_REQUIRED"
    assert ranking_contract(TOOLS[0])["items"] == []
    assert ranking_contract(TOOLS[0])["data_status"] == "VALIDATION_REQUIRED"
