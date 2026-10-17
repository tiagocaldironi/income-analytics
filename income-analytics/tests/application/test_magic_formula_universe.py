"""UNIVERSE-001..018: official source discovery and fail-closed readiness."""

import hashlib
import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from income_analytics.application.cvm_magic_formula_normalization import RULES
from income_analytics.application.magic_formula_stocks import MagicFormulaStockRankingService
from income_analytics.application.magic_formula_universe import (
    classify_candidates,
    coverage,
    discover_candidates,
    evaluate_readiness,
)
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)
from income_analytics.infrastructure.magic_formula_universe_sources import (
    discovery_sources,
    readiness_sources,
)
from scripts.discover_magic_formula_universe import canonical_context
from tests.application.test_magic_formula_ranking_engine import (
    canonical as ranking_canonical,  # noqa: F401
)

REFERENCE = "2025-12-31"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/cvm/universe_discovery_v1"


@pytest.fixture(scope="module")
def official(request):
    repository, states, _ = request.getfixturevalue("ranking_canonical")
    context = canonical_context(repository, REFERENCE)
    general, securities = discovery_sources(FIXTURES, 2025)
    candidates, _ = discover_candidates(general, securities, REFERENCE)
    tickers = {s["Codigo_Negociacao"].strip() for c in candidates for s in c["raw_securities"]}
    accounts, capital, quotes = readiness_sources(FIXTURES, FIXTURES, REFERENCE, tickers)
    with pytest.MonkeyPatch.context() as patch:

        def forbidden(*args, **kwargs):
            pytest.fail("Universe discovery must never invoke ranking")

        patch.setattr(MagicFormulaStockRankingService, "rank", forbidden)
        patch.setattr(MagicFormulaStockRankingService, "rank_validation_sample", forbidden)
        issuers = evaluate_readiness(
            classify_candidates(candidates, context, REFERENCE),
            accounts,
            capital,
            quotes,
            context,
            REFERENCE,
        )
    return dict(
        issuers=issuers,
        context=context,
        states=states,
        sources=(general, securities, accounts, capital, quotes),
    )


def synthetic():
    general = dict(
        CNPJ_Companhia="12345678000190",
        Codigo_CVM="999999",
        Versao="1",
        Data_Referencia=REFERENCE,
        Nome_Empresarial="Banco de exemplos industriais",
        Setor_Atividade="Papel e Celulose",
        Categoria_Registro_CVM="Categoria A",
        Situacao_Registro_CVM="Ativo",
        Data_Situacao_Registro_CVM="2000-01-01",
        Data_Categoria_Registro_CVM="2000-01-01",
        source_reference="fca|general|line=2",
    )
    security = dict(
        CNPJ_Companhia=general["CNPJ_Companhia"],
        Nome_Empresarial=general["Nome_Empresarial"],
        Data_Referencia=REFERENCE,
        Valor_Mobiliario="Ações Ordinárias",
        Sigla_Entidade_Administradora="B3",
        Mercado="Bolsa",
        Data_Inicio_Negociacao="2000-01-01",
        Data_Fim_Negociacao="",
        Codigo_Negociacao="EXMP3",
        Sigla_Classe_Acao_Preferencial="",
        Composicao_BDR_Unit="",
        ID_Documento="1",
        source_reference="fca|security|line=2",
    )
    accounts = [
        dict(
            CD_CVM="999999",
            CNPJ_CIA=general["CNPJ_Companhia"],
            DT_REFER=REFERENCE,
            DT_INI_EXERC="2025-01-01",
            DT_FIM_EXERC=REFERENCE,
            statement=r.statement,
            CD_CONTA=c,
            VL_CONTA="10",
            MOEDA="REAL",
            ESCALA_MOEDA="UNIDADE",
            source_reference="dfp|" + c,
        )
        for r in RULES
        for c in r.account_codes
    ]
    capital = dict(
        CNPJ_CIA=general["CNPJ_Companhia"],
        DT_REFER=REFERENCE,
        QT_ACAO_ORDIN_CAP_INTEGR="10",
        QT_ACAO_ORDIN_TESOURO="0",
        QT_ACAO_PREF_CAP_INTEGR="0",
        QT_ACAO_PREF_TESOURO="0",
        source_reference="dfp|capital",
    )
    quote = dict(
        ticker="EXMP3",
        effective_date="2025-12-30",
        price="10",
        currency="R$",
        isin="BREXMPACNOR0",
        source_reference="b3|line=2",
    )
    return [[general], [security], accounts, [capital], [quote]]


def evaluate(sources, context=None):
    general, securities, accounts, capital, quotes = sources
    candidates, _ = discover_candidates(general, securities, REFERENCE)
    return evaluate_readiness(
        classify_candidates(candidates, context or {}, REFERENCE),
        accounts,
        capital,
        quotes,
        context or {},
        REFERENCE,
    )


def test_universe_001_official_not_manual(official):
    assert len(official["issuers"]) == 360
    assert len(official["issuers"]) > len(official["states"])
    altered = synthetic()
    assert len(evaluate(altered)) == 1
    altered[1] = []
    assert evaluate(altered) == []


def test_universe_002_issuer_economic_unit(official):
    ids = [i["issuer_id"] for i in official["issuers"]]
    assert len(ids) == len(set(ids))
    assert all(
        s["issuer_id"] == i["issuer_id"] for i in official["issuers"] for s in i["securities"]
    )
    assert all(
        i["issuer_id"] not in {s["ticker"] for s in i["securities"]} for i in official["issuers"]
    )


def test_universe_003_petrobras_two_classes_one_issuer(official):
    found = [
        i
        for i in official["issuers"]
        if any(s["ticker"] in {"PETR3", "PETR4"} for s in i["securities"])
    ]
    assert len(found) == 1
    assert {"PETR3", "PETR4"} <= {s["ticker"] for s in found[0]["securities"]}


def test_universe_004_golden_five_natural(official):
    discovered = {i["issuer_id"] for i in official["issuers"]}
    assert set(official["states"]) <= discovered


def test_universe_005_financial_evidence_not_name():
    sources = synthetic()
    assert evaluate(sources)[0]["methodology_eligibility"] == "ELIGIBLE"
    sources[0][0]["Setor_Atividade"] = "Emp. Adm. Part. - Bancos"
    row = evaluate(sources)[0]
    assert row["methodology_eligibility"] == "EXCLUDED"
    assert row["exclusion_reason"] == "FINANCIAL_SECTOR"
    assert row["sector_source_reference"]


def test_universe_006_missing_data_not_exclusion():
    sources = synthetic()
    sources[2:] = [[], [], []]
    row = evaluate(sources)[0]
    assert row["methodology_eligibility"] == "ELIGIBLE"
    assert row["exclusion_reason"] is None
    assert row["data_readiness_status"] == "DATA_GAP"


@pytest.mark.parametrize(
    ("index", "reason"),
    [(2, "NO_ACCOUNTING_DATA"), (3, "NO_CAPITAL_DATA"), (4, "NO_REFERENCE_PRICE")],
    ids=["UNIVERSE-007", "UNIVERSE-008", "UNIVERSE-009"],
)
def test_missing_dimension(index, reason):
    sources = synthetic()
    sources[index] = []
    row = evaluate(sources)[0]
    assert row["data_readiness_status"] == "DATA_GAP"
    assert reason in row["data_reason_codes"]


def test_universe_010_ambiguous_identity_closed():
    sources = synthetic()
    sources[0].append(dict(sources[0][0], Codigo_CVM="999998"))
    row = evaluate(sources)[0]
    assert row["issuer_id"] is None
    assert row["identity_status"] == "UNRESOLVED"
    assert row["eligibility_status"] == "REVIEW_REQUIRED"
    assert "UNRESOLVED_IDENTITY" in row["data_reason_codes"]


def test_universe_011_reference_policy():
    sources = synthetic()
    sources[4].append(dict(sources[4][0], effective_date="2026-01-02", price="999"))
    assert evaluate(sources)[0]["securities"][0]["price"] == "10"
    assert evaluate(sources)[0]["securities"][0]["effective_market_date"] == "2025-12-30"
    sources[4][0]["effective_date"] = "2025-12-23"
    assert "NO_REFERENCE_PRICE" in evaluate(sources)[0]["data_reason_codes"]


def test_universe_012_multiple_securities_and_units():
    sources = synthetic()
    sources[1].append(
        dict(sources[1][0], Codigo_Negociacao="EXMP4", Valor_Mobiliario="Ações Preferenciais")
    )
    sources[1].append(dict(sources[1][0], Codigo_Negociacao="EXMP11", Valor_Mobiliario="Units"))
    rows = evaluate(sources)
    assert len(rows) == 1
    assert len(rows[0]["securities"]) == 3


def test_universe_013_coverage_arithmetic(official):
    measured = coverage(official["issuers"])
    assert list(measured["funnel"].values()) == sorted(measured["funnel"].values(), reverse=True)
    for name, value in measured["independent_dimensions"].items():
        metric = measured["metrics"][name.lower() + "_coverage"]
        assert metric["numerator"] == value
        assert metric["denominator"] == measured["funnel"]["METHODOLOGY_ELIGIBLE"]
    assert measured["funnel"]["FULL_DATA_READY"] == 5


def test_universe_014_reason_reconciliation(official):
    measured = coverage(official["issuers"])
    assert sum(measured["primary_status_distribution"].values()) == len(official["issuers"])
    assert sum(measured["methodology_distribution"].values()) == len(official["issuers"])
    assert (
        sum(measured["primary_gap_reasons"].values())
        == measured["funnel"]["METHODOLOGY_ELIGIBLE"] - 5
    )
    for reason, count in measured["data_gap_reason_incidence"].items():
        assert count == sum(
            reason in i["data_reason_codes"]
            for i in official["issuers"]
            if i["methodology_eligibility"] == "ELIGIBLE"
        )


def test_universe_015_new_connection_readback_immutable(tmp_path, official):
    path = tmp_path / "universe.db"
    repository = MagicFormulaUniverseRepository(path)
    repository.initialize()
    document = dict(
        universe_snapshot_id="test-id",
        reference_date=REFERENCE,
        universe_policy_version="test-v1",
        created_at="2026-09-17",
        universe_type="CANDIDATE_PUBLISHABLE_UNIVERSE",
        issuers=official["issuers"],
        coverage=coverage(official["issuers"]),
        tool_status="VALIDATION_REQUIRED",
        ranking_status="INACTIVE",
    )
    repository.save(document)
    del repository
    assert MagicFormulaUniverseRepository(path).read("test-id") == document
    for statement in (
        "DELETE FROM magic_formula_universe_snapshots",
        "UPDATE magic_formula_universe_snapshots SET reference_date='wrong'",
    ):
        with MagicFormulaUniverseRepository(path).connection(write=True) as conn:
            with pytest.raises(sqlite3.IntegrityError, match="IMMUTABLE"):
                conn.execute(statement)
    wrong = deepcopy(document)
    wrong["coverage"]["funnel"]["FULL_DATA_READY"] += 1
    with pytest.raises(ValueError, match="COVERAGE_MISMATCH"):
        MagicFormulaUniverseRepository(path).save(wrong)


def test_universe_016_ingestion_order(official):
    reversed_sources = [list(reversed(rows)) for rows in official["sources"]]
    assert evaluate(reversed_sources, official["context"]) == official["issuers"]


def test_universe_017_five_remain_ready(official):
    anchors = [i for i in official["issuers"] if i["issuer_id"] in official["states"]]
    assert len(anchors) == 5
    for row in anchors:
        assert row["methodology_eligibility"] == "ELIGIBLE"
        assert row["data_readiness_status"] == "FULL_DATA_READY"
        assert row["canonical_status"] == "RESOLVED"
        assert row["canonical_ranking_eligible"] is True


@pytest.mark.parametrize("missing", ["", None, "NaN", "invalid"])
def test_universe_018_missing_is_not_zero(missing):
    sources = synthetic()
    sources[2][0]["VL_CONTA"] = missing
    sources[3][0]["QT_ACAO_ORDIN_CAP_INTEGR"] = missing
    sources[4][0]["price"] = missing
    row = evaluate(sources)[0]
    assert {"NO_ACCOUNTING_DATA", "NO_CAPITAL_DATA", "NO_REFERENCE_PRICE"} <= set(
        row["data_reason_codes"]
    )
    assert row["securities"][0]["price"] is None
    assert not row["market_readiness"]["capital_ready"]


def test_unknown_sector_review_and_unit_scale_not_inferred():
    sources = synthetic()
    row = evaluate(sources)[0]
    assert "UNIT_UNRESOLVED" in row["data_reason_codes"]
    assert row["market_readiness"]["quantity_unit"] is None
    sources[0][0]["Setor_Atividade"] = "Unknown"
    assert evaluate(sources)[0]["methodology_eligibility"] == "REVIEW_REQUIRED"


def test_quoted_unit_is_not_missing_price_or_resolved_capital():
    sources = synthetic()
    sources[1][0].update(Codigo_Negociacao="EXMP11", Valor_Mobiliario="Units")
    sources[4][0]["ticker"] = "EXMP11"
    row = evaluate(sources)[0]
    assert row["market_readiness"]["price_ready"]
    assert "NO_REFERENCE_PRICE" not in row["data_reason_codes"]
    assert not row["market_readiness"]["security_ready"]
    assert not row["market_readiness"]["capital_ready"]


def test_duplicate_price_and_wrong_account_period_fail_closed():
    sources = synthetic()
    sources[4].append(dict(sources[4][0], price="11"))
    sources[2][0]["DT_FIM_EXERC"] = "2025-09-30"
    row = evaluate(sources)[0]
    assert row["data_readiness_status"] == "REVIEW_REQUIRED"
    assert {"AMBIGUOUS_REFERENCE_PRICE", "TEMPORAL_CONFLICT"} <= set(row["data_reason_codes"])


def test_versioned_official_archives_checksums():
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf8"))
    for source in manifest["sources"]:
        assert (
            hashlib.sha256((FIXTURES / source["source_file"]).read_bytes()).hexdigest()
            == source["fixture_sha256"]
        )
