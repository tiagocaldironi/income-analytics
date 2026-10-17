"""SHARES-UNIT-001..020 using pinned official historical-document evidence."""

import hashlib
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from income_analytics.application.historical_shares_units import (
    POLICY_VERSION,
    apply_readiness,
    outstanding,
    resolve,
)
from income_analytics.application.magic_formula_stocks import MagicFormulaStockRankingService
from income_analytics.application.magic_formula_universe import coverage
from income_analytics.infrastructure.cvm_historical_shares_document import read_unit_evidence
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)
from tests.application.test_magic_formula_ranking_engine import (
    canonical as ranking_canonical,  # noqa: F401
)
from tests.application.test_magic_formula_universe import (
    official as universe_official,  # noqa: F401
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/cvm/shares_unit_v1"


@pytest.fixture(scope="module")
def sample():
    data = json.loads((FIXTURES / "sample.json").read_text(encoding="utf8"))
    rows = []
    for issuer in data["issuers"]:
        evidence = read_unit_evidence(FIXTURES / (issuer["document"]["ID_DOC"] + "-evidence.zip"))
        rows.append((issuer, evidence, resolve(issuer, issuer["capital"], evidence)))
    return rows


def test_shares_unit_001_no_magnitude_inference(sample):
    for issuer, evidence, _ in sample:
        for raw in ("1", "1000", "9999999999999"):
            cap, proof = deepcopy(issuer["capital"]), deepcopy(evidence)
            for field in proof["quantities"]:
                cap[field] = proof["quantities"][field] = "0" if "TESOURO" in field else raw
            result = resolve(issuer, cap, proof)
            assert result["status"] == "RESOLVED"
            assert result["normalization_multiplier"] == (
                "1000" if proof["unit_label"] == "Mil" else "1"
            )
            assert resolve(issuer, cap, None)["status"] == "UNIT_UNRESOLVED"


def test_shares_unit_002_no_issuer_hardcode(sample):
    issuer, proof, _ = deepcopy(sample[0])
    issuer.update(issuer_id="different-id", cnpj="12345678000190", cvm_code="999999")
    proof.update(cnpj=issuer["cnpj"], cvm_code=issuer["cvm_code"])
    assert resolve(issuer, issuer["capital"], proof)["status"] == "RESOLVED"


def test_shares_unit_003_raw_quantity_preserved(sample):
    for issuer, _, result in sample:
        assert result["status"] == "RESOLVED"
        for quantity in result["quantities"]:
            field = (
                "QT_ACAO_"
                + ("ORDIN_" if quantity["share_class"] == "ON" else "PREF_")
                + ("CAP_INTEGR" if quantity["quantity_kind"] == "issued" else "TESOURO")
            )
            assert quantity["raw_quantity"] == issuer["capital"][field]


def test_shares_unit_004_multiplier_explicit(sample):
    assert {r["normalization_multiplier"] for _, _, r in sample} == {"1", "1000"}


def test_shares_unit_005_integral_normalized_quantity(sample):
    for _, _, result in sample:
        assert all(
            Decimal(q["normalized_quantity"]) == int(q["normalized_quantity"])
            for q in result["quantities"]
        )
    issuer, proof, _ = deepcopy(next(row for row in sample if row[1]["unit_label"] == "Unidade"))
    issuer["capital"]["QT_ACAO_ORDIN_CAP_INTEGR"] = proof["quantities"][
        "QT_ACAO_ORDIN_CAP_INTEGR"
    ] = "1.5"
    assert resolve(issuer, issuer["capital"], proof)["status"] == "REVIEW_REQUIRED"


def test_shares_unit_006_source_reference(sample):
    for issuer, evidence, result in sample:
        assert result["source_reference"] == issuer["capital"]["source_reference"]
        assert "EscalaQtdAcoes" in evidence["source_reference"]
        assert all(
            q["unit_source_reference"] == evidence["source_reference"] for q in result["quantities"]
        )


def test_shares_unit_007_policy_version(sample):
    assert all(r["policy_version"] == POLICY_VERSION for _, _, r in sample)


def test_shares_unit_008_golden_five_identical(sample):
    controls = {i["issuer_id"]: r for i, _, r in sample if i["control"]}
    assert len(controls) == 5
    for path in (ROOT / "tests/golden/magic_formula").glob("*_2025.json"):
        fixture = json.loads(path.read_text(encoding="utf8"))
        issuer_id = fixture.get("issuer", {}).get("issuer_id")
        if issuer_id not in controls:
            continue
        quantities = outstanding(controls[issuer_id])
        for security in fixture["capital"]["securities"]:
            assert quantities[security["share_class"]] == security["outstanding_shares"]


@pytest.mark.parametrize(
    ("ticker", "share_class", "expected"),
    [("PETR3", "ON", "7442231382"), ("PETR4", "PN", "5446501379")],
    ids=["SHARES-UNIT-009", "SHARES-UNIT-010"],
)
def test_petrobras_quantities(sample, ticker, share_class, expected):
    result = next(r for i, _, r in sample if any(s["ticker"] == ticker for s in i["securities"]))
    assert outstanding(result)[share_class] == expected


def test_shares_unit_011_classes_never_mixed(sample):
    for _, _, result in sample:
        assert {(q["share_class"], q["quantity_kind"]) for q in result["quantities"]} == {
            ("ON", "issued"),
            ("PN", "issued"),
            ("ON", "treasury"),
            ("PN", "treasury"),
        }


def test_shares_unit_012_units_not_double_counted(sample, request):
    official = request.getfixturevalue("universe_official")
    resolutions = {i["issuer_id"]: r for i, _, r in sample}
    updated = apply_readiness(official["issuers"], resolutions)
    assert len(updated) == len(official["issuers"])
    assert all("UNIT" not in outstanding(r) for r in resolutions.values())
    for before, after in zip(official["issuers"], updated, strict=True):
        assert before["securities"] == after["securities"]
        assert (
            before["market_readiness"]["security_ready"]
            == after["market_readiness"]["security_ready"]
        )


def test_shares_unit_013_treasury_subtracted(sample):
    for _, _, result in sample:
        for share_class, net in outstanding(result).items():
            amounts = {
                q["quantity_kind"]: Decimal(q["normalized_quantity"])
                for q in result["quantities"]
                if q["share_class"] == share_class
            }
            assert Decimal(net) == amounts["issued"] - amounts["treasury"]


def test_shares_unit_014_corporate_event_not_scale(sample):
    issuer, proof, _ = deepcopy(sample[0])
    proof["reference_date"] = "2026-06-30"
    proof["corporate_event"] = "SPLIT_1000_TO_1"
    assert resolve(issuer, issuer["capital"], proof)["status"] == "REVIEW_REQUIRED"


def test_shares_unit_015_unknown_remains_unresolved(sample):
    issuer, proof, _ = deepcopy(sample[0])
    proof["unit_label"] = "UNKNOWN"
    assert resolve(issuer, issuer["capital"], proof)["status"] == "UNIT_UNRESOLVED"
    assert resolve(issuer, issuer["capital"], None)["normalization_multiplier"] is None


def test_shares_unit_016_ingestion_order(sample):
    expected = {i["issuer_id"]: r for i, _, r in sample}
    assert {i["issuer_id"]: resolve(i, i["capital"], e) for i, e, _ in reversed(sample)} == expected


def test_shares_unit_017_lineage_persisted(tmp_path, sample, request):
    official = request.getfixturevalue("universe_official")
    issuers = apply_readiness(official["issuers"], {i["issuer_id"]: r for i, _, r in sample})
    document = dict(
        universe_snapshot_id="unit-test",
        reference_date="2025-12-31",
        universe_policy_version="test",
        created_at="test",
        universe_type="CANDIDATE_PUBLISHABLE_UNIVERSE",
        issuers=issuers,
        coverage=coverage(issuers),
        tool_status="VALIDATION_REQUIRED",
        ranking_status="INACTIVE",
    )
    database = tmp_path / "units.db"
    repository = MagicFormulaUniverseRepository(database)
    repository.initialize()
    repository.save(document)
    del repository
    assert MagicFormulaUniverseRepository(database).read("unit-test") == document


def test_shares_unit_018_coverage_arithmetic(sample, request):
    official = request.getfixturevalue("universe_official")
    after = apply_readiness(official["issuers"], {i["issuer_id"]: r for i, _, r in sample})
    measured = coverage(after)
    assert (
        measured["methodology_distribution"]
        == coverage(official["issuers"])["methodology_distribution"]
    )
    assert sum(measured["primary_status_distribution"].values()) == 360
    assert measured["independent_dimensions"]["CAPITAL_READY"] > 5
    assert measured["funnel"]["FULL_DATA_READY"] <= measured["funnel"]["CAPITAL_READY"]


def test_shares_unit_019_no_ranking(sample, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Ranking is forbidden in this phase")

    monkeypatch.setattr(MagicFormulaStockRankingService, "rank", forbidden)
    monkeypatch.setattr(MagicFormulaStockRankingService, "rank_validation_sample", forbidden)
    for issuer, proof, _ in sample:
        assert resolve(issuer, issuer["capital"], proof)["status"] == "RESOLVED"


def test_shares_unit_020_frozen_engine():
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf8"))
    for path, expected in manifest["frozen_code_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_fixture_hashes():
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf8"))
    for item in manifest["documents"]:
        assert hashlib.sha256((FIXTURES / item["file"]).read_bytes()).hexdigest() == item["sha256"]


def test_noneligible_classification_is_not_overwritten(sample, request):
    official = request.getfixturevalue("universe_official")
    source = deepcopy(official["issuers"][0])
    source["methodology_eligibility"] = "EXCLUDED"
    source["eligibility_status"] = "EXCLUDED"
    assert apply_readiness([source], {source["issuer_id"]: sample[0][2]}) == [source]


@pytest.mark.parametrize("field", ["cnpj", "cvm_code", "reference_date", "version"])
def test_identity_and_version_fail_closed(sample, field):
    issuer, proof, _ = deepcopy(sample[0])
    proof[field] = "wrong"
    assert resolve(issuer, issuer["capital"], proof)["status"] == "REVIEW_REQUIRED"


def test_conflicting_raw_quantity_fail_closed(sample):
    issuer, proof, _ = deepcopy(sample[0])
    issuer["capital"]["QT_ACAO_ORDIN_CAP_INTEGR"] = "123"
    result = resolve(issuer, issuer["capital"], proof)
    assert result["status"] == "REVIEW_REQUIRED"
    with pytest.raises(ValueError, match="UNIT_RESOLUTION_REQUIRED"):
        outstanding(result)


@pytest.mark.parametrize("change", ["unit_label", "pdf_quantity", "xml_digest", "missing_unit"])
def test_document_cross_evidence_fails_closed(sample, tmp_path, change):
    issuer, _, _ = next(row for row in sample if row[1]["unit_label"] == "Unidade")
    original = FIXTURES / (issuer["document"]["ID_DOC"] + "-evidence.zip")
    with ZipFile(original) as archive:
        members = {n: archive.read(n) for n in archive.namelist()}
    metadata = json.loads(members["evidence.json"])
    text = metadata["pdf_capital_page"]["text"]
    if change == "unit_label":
        metadata["pdf_capital_page"]["text"] = text.replace("(Unidades)", "(Mil)")
    elif change == "pdf_quantity":
        metadata["pdf_capital_page"]["text"] = text.replace("Ordinárias", "Class unknown", 1)
    elif change == "missing_unit":
        metadata["pdf_capital_page"]["text"] = text.replace("(Unidades)", "(Unknown)")
    else:
        metadata["member_sha256"][metadata["main_xml_member"]] = "wrong"
    members["evidence.json"] = json.dumps(metadata).encode("utf8")
    path = tmp_path / "contradiction.zip"
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, value in members.items():
            archive.writestr(name, value)
    if change == "xml_digest":
        with pytest.raises(ValueError, match="SOURCE_DIGEST_MISMATCH"):
            read_unit_evidence(path)
    else:
        assert read_unit_evidence(path)["status"] in ("REVIEW_REQUIRED", "SOURCE_SCHEMA_ERROR")
