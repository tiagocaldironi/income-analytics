"""PETRO-E2E-001..020: official raw evidence through persisted canonical policy."""

import hashlib
import json
import runpy
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from zipfile import ZipFile

import pytest
from alembic.config import Config

from alembic import command
from income_analytics.application.cvm_magic_formula_normalization import (
    MagicFormulaAccountingAdapterV1,
)
from income_analytics.application.magic_formula_contract import DIMENSIONS, is_ranking_eligible
from income_analytics.application.magic_formula_formal_qa import evaluate_formal_qa
from income_analytics.application.magic_formula_fundamentals_assembler import (
    MagicFormulaFundamentalsAssembler,
)
from income_analytics.infrastructure.magic_formula_contract_repository import (
    CanonicalMagicFormulaRepository,
)
from income_analytics.infrastructure.magic_formula_raw_verification import OfficialRawVerifier
from tests.application.test_magic_formula_canonical_contract import foundation  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "tests/fixtures/cvm/petrobras_canonical_v2"
RECOVERY = runpy.run_path(str(ROOT / "scripts/recover_petrobras_canonical.py"))


@pytest.fixture(scope="module")
def recovered(tmp_path_factory):
    directory = tmp_path_factory.mktemp("petrobras")
    database = directory / "clean.db"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("INCOME_ANALYTICS_DATABASE", str(database))
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
        # Network and ranking cannot be fallback paths in an evidence test.
        patch.setattr(
            "income_analytics.infrastructure.b3_cotahist_market_data.urlopen",
            lambda *a, **k: pytest.fail("NETWORK_FORBIDDEN"),
        )
        patch.setattr(
            "income_analytics.application.magic_formula_stocks.MagicFormulaStockRankingService.rank",
            lambda *a, **k: pytest.fail("RANKING_FORBIDDEN"),
        )
        result = RECOVERY["recover"](database, SOURCES, SOURCES, directory / "golden")
    repo = CanonicalMagicFormulaRepository(database)
    fixture = json.loads((directory / "golden/petrobras_2025.json").read_text(encoding="utf8"))
    with repo.connection() as conn:
        qa = dict(conn.execute("SELECT * FROM magic_formula_formal_qa").fetchone())
    qa["dimensions"] = json.loads(qa["evidence_json"])
    inputs = dict(
        issuer_id=result["issuer"]["issuer_id"],
        reference_date="2025-12-31",
        fixture=fixture,
        snapshot=repo.read_snapshot(result["snapshot_id"]),
        qa=qa,
    )
    return result, inputs, repo


@pytest.mark.parametrize(
    "case,reason",
    [
        (1, "MISSING_GOLDEN"),
        (2, "MISSING_VALIDATED_SNAPSHOT"),
        (3, "MISSING_FORMAL_QA"),
        (4, "QA_NOT_PASS"),
        (5, "QA_SNAPSHOT_MISMATCH"),
        (6, "SNAPSHOT_NOT_VALIDATED"),
        (7, "ADAPTER_VERSION_MISMATCH"),
        (8, "REFERENCE_DATE_MISMATCH"),
    ],
    ids=[f"PETRO-E2E-{i:03}" for i in range(1, 9)],
)
def test_negative_policy(recovered, case, reason):
    inputs = deepcopy(recovered[1])
    if case <= 3:
        inputs[{1: "fixture", 2: "snapshot", 3: "qa"}[case]] = None
    elif case == 4:
        inputs["qa"]["dimensions"][0]["status"] = "REVIEW_REQUIRED"
    elif case == 5:
        inputs["qa"]["snapshot_id"] = "another-snapshot"
    elif case == 6:
        inputs["snapshot"]["validation_status"] = "NOT_VALIDATED"
    elif case == 7:
        inputs["snapshot"]["adapter_version"] = "UNAPPROVED"
    elif case == 8:
        inputs["reference_date"] = "2025-12-30"
    decision = is_ranking_eligible(**inputs)
    assert not decision.eligible
    assert reason in decision.reasons


def test_petro_e2e_009_offsetting_class_cap_errors_fail_qa(recovered):
    inputs = deepcopy(recovered[1])
    lineage = json.loads(inputs["snapshot"]["lineage_json"])
    caps = lineage[-1]["market_cap_components"]
    caps[0]["partial_market_cap"] = str(Decimal(caps[0]["partial_market_cap"]) + 1)
    caps[1]["partial_market_cap"] = str(Decimal(caps[1]["partial_market_cap"]) - 1)
    # The issuer total still agrees; the dimensional check must reject both wrong partials.
    inputs["snapshot"]["lineage_json"] = json.dumps(lineage)
    qa = evaluate_formal_qa(inputs["fixture"], inputs["snapshot"], readback_matches=True)
    assert next(d for d in qa if d.dimension == "market_cap").status == "FAIL"


def test_petro_e2e_010_missing_metric_never_zero(recovered):
    raw = RECOVERY["dataset"](SOURCES, "dfp_cia_aberta_2025.zip", "DFP")
    from income_analytics.infrastructure.cvm_fundamentals_data import CvmStatementParser

    records = tuple(r for r in CvmStatementParser().parse(raw) if r.account_code != "3.05")
    metrics, _, status = MagicFormulaAccountingAdapterV1().normalize(records)
    assert status == "INSUFFICIENT_DATA"
    assert "ebit" not in metrics
    with pytest.raises(ValueError, match="INSUFFICIENT_DATA"):
        MagicFormulaFundamentalsAssembler().assemble(
            issuer_id=recovered[1]["issuer_id"],
            cvm_code="009512",
            company_name="Petrobras",
            financial_reference_date="2025-12-31",
            statement_type="DFP",
            metrics=metrics,
            market_cap=Decimal("410254648612.52"),
        )
    inputs = deepcopy(recovered[1])
    actual = json.loads(inputs["snapshot"]["metrics_json"])
    del actual["ebit"]
    inputs["snapshot"]["metrics_json"] = json.dumps(actual)
    assert not is_ranking_eligible(**inputs).eligible


def test_petro_e2e_011_builder_schema(recovered):
    fixture = recovered[1]["fixture"]
    assert fixture["schema_version"] == "MAGIC_FORMULA_GOLDEN_V2"
    assert fixture["fixture_status"] == "READY_FOR_VALIDATION"
    assert fixture["reference"]["price_effective_date"] == "2025-12-30"


def test_petro_e2e_012_securities_share_stable_uuid_and_isin(recovered):
    result, inputs, repo = recovered
    issuer = result["issuer"]
    assert str(UUID(issuer["issuer_id"])) == issuer["issuer_id"]
    assert {s["issuer_id"] for s in inputs["fixture"]["security"]} == {issuer["issuer_id"]}
    assert {s["isin"] for s in inputs["fixture"]["security"]} == {"BRPETRACNOR9", "BRPETRACNPR6"}
    assert repo.register_issuer(**issuer) == issuer


def test_petro_e2e_013_capital_locators_exactly_one_after_reload(recovered):
    receipts = recovered[0]["receipts"]
    capital = [r for r in receipts if r["kind"] == "capital"]
    assert len(capital) == 4 and all(r["applicable_records"] == 1 for r in capital)
    assert len({r["locator"] for r in capital}) == 4
    raw = OfficialRawVerifier(SOURCES, SOURCES).verify(recovered[1]["fixture"])
    assert raw == receipts


def test_petro_e2e_014_cotahist_preserves_original_lines(recovered):
    prices = recovered[1]["fixture"]["prices"]
    assert "|line=1692376|" in prices[0]["record_reference"]
    assert "|line=1692377|" in prices[1]["record_reference"]
    assert all(
        r["applicable_records"] == 1 for r in recovered[0]["receipts"] if r["kind"] == "market"
    )


def test_petro_e2e_015_independent_market_cap(recovered):
    fixture = recovered[1]["fixture"]
    price_by_ticker = {p["ticker"]: Decimal(p["price"]) for p in fixture["prices"]}
    partials = {
        c["ticker"]: Decimal(c["normalized_quantity"]) * price_by_ticker[c["ticker"]]
        for c in fixture["capital"]["securities"]
    }
    assert partials == {"PETR3": Decimal("242393476111.74"), "PETR4": Decimal("167861172500.78")}
    assert (
        sum(partials.values())
        == Decimal(fixture["expected"]["market_cap"])
        == Decimal("410254648612.52")
    )


def test_petro_e2e_016_eight_persisted_dimensions_bound_to_snapshot(recovered):
    result, inputs, _ = recovered
    assert inputs["qa"]["snapshot_id"] == result["snapshot_id"]
    assert {d: inputs["qa"][d] for d in DIMENSIONS} == dict.fromkeys(DIMENSIONS, "PASS")
    assert inputs["qa"]["final_status"] == "PASS"


def test_petro_e2e_017_validation_survives_independent_readback(recovered):
    result, inputs, repo = recovered
    assert result["initial_validation_status"] == "NOT_VALIDATED"
    new = CanonicalMagicFormulaRepository(repo.database)
    assert new.read_snapshot(result["snapshot_id"]) == inputs["snapshot"]
    assert inputs["snapshot"]["validation_status"] == "PASS"
    assert "validation_status" not in json.loads(inputs["snapshot"]["metrics_json"])


def test_petro_e2e_018_resolution_is_projected(recovered):
    assert (
        recovered[2].eligibility(recovered[1]["issuer_id"], "2025-12-31").issuer_status
        == "RESOLVED"
    )


def test_petro_e2e_019_eligible_without_activating_tool(recovered):
    assert recovered[2].eligibility(recovered[1]["issuer_id"], "2025-12-31").eligible
    assert recovered[0]["ranking_status"] == "INACTIVE"
    assert recovered[0]["tool_status"] == "VALIDATION_REQUIRED"
    assert recovered[0]["ranking_gate"] == "BLOCKED"  # one issuer in the clean database


def test_petro_e2e_020_existing_four_unchanged_and_five_ready(request, tmp_path):
    database, directory, repo = request.getfixturevalue("foundation")
    for slug in ("weg", "suzano", "rumo", "telefonica"):
        fixture = json.loads((directory / f"{slug}_2025.json").read_text(encoding="utf8"))
        repo.register_issuer(**fixture["issuer"])
        repo.adopt_existing_snapshot("snapshot-" + slug, fixture["issuer"]["issuer_id"])
        repo.validate_snapshot("snapshot-" + slug, repo.register_golden(fixture))
    before = RECOVERY["dump_rows"](repo)
    result = RECOVERY["recover"](database, SOURCES, SOURCES, tmp_path / "petro-golden")
    RECOVERY["assert_preserved"](before, RECOVERY["dump_rows"](repo))
    assert result["validated_resolved_issuers"] == 5
    assert result["multisector_golden_gate"] == "PASS"
    assert result["ranking_gate"] == "READY"
    assert result["ranking_status"] == "INACTIVE"
    assert result["tool_status"] == "VALIDATION_REQUIRED"


def test_raw_excerpt_checksums_and_original_cotahist_records():
    manifest = json.loads((SOURCES / "manifest.json").read_text(encoding="utf8"))
    for source in manifest["sources"]:
        archive = SOURCES / source["source_file"]
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == source["excerpt_archive_sha256"]
        with ZipFile(archive) as z:
            for member in source.get("members", []):
                assert (
                    hashlib.sha256(z.read(member["name"])).hexdigest() == member["excerpt_sha256"]
                )
            if "records" in source:
                lines = z.read(z.namelist()[0]).splitlines(keepends=True)
                for row in source["records"]:
                    assert hashlib.sha256(lines[row["line"] - 1]).hexdigest() == row["sha256"]


@pytest.mark.parametrize("kind", ["accounting", "security", "capital", "market"])
def test_tampered_locator_is_rejected(recovered, kind):
    fixture = deepcopy(recovered[1]["fixture"])
    if kind == "accounting":
        fixture["accounting"]["ebit"]["components"][0]["source_reference"] = fixture["accounting"][
            "ebit"
        ]["components"][0]["source_reference"].replace("|3.05|", "|3.999|")
    elif kind == "security":
        fixture["security"][0]["fca_source_reference"] = fixture["security"][0][
            "fca_source_reference"
        ].replace("147760", "999999")
    elif kind == "capital":
        fixture["capital"]["securities"][0]["issued_source_reference"] = fixture["capital"][
            "securities"
        ][0]["issued_source_reference"].replace("QT_ACAO_ORDIN", "QT_ACAO_PREF")
    else:
        fixture["prices"][0]["record_reference"] = fixture["prices"][0]["record_reference"].replace(
            "line=1692376", "line=1692377"
        )
    with pytest.raises(ValueError, match="GOLDEN_EVIDENCE_DEFECT"):
        OfficialRawVerifier(SOURCES, SOURCES).verify(fixture)


def test_duplicate_raw_account_cannot_pass_locator(recovered):
    verifier = OfficialRawVerifier(SOURCES, SOURCES)
    rows = verifier.csv_rows("dfp_cia_aberta_2025.zip", "dfp_cia_aberta_DRE_con_2025.csv")
    row = next(r for r in rows if r["CD_CONTA"] == "3.05" and r["ORDEM_EXERC"] == "ÚLTIMO")
    rows.append(deepcopy(row))
    with pytest.raises(ValueError, match="LOCATOR_COUNT:2"):
        verifier.verify(recovered[1]["fixture"])


def test_golden_builder_does_not_use_production_adapter_or_snapshot(recovered, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("GOLDEN_MUST_NOT_READ_PRODUCTION_RESULTS")

    monkeypatch.setattr(MagicFormulaAccountingAdapterV1, "normalize", forbidden)
    monkeypatch.setattr(MagicFormulaFundamentalsAssembler, "assemble", forbidden)
    monkeypatch.setattr(CanonicalMagicFormulaRepository, "read_snapshot", forbidden)
    fixture, _, _, _ = RECOVERY["build_evidence"](recovered[0]["issuer"], SOURCES, SOURCES)
    assert fixture["expected"] == recovered[1]["fixture"]["expected"]
