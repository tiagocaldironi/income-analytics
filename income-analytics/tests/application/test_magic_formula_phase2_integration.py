"""Offline official-data pipeline and migration regression coverage."""

import csv
import hashlib
import io
import json
import shutil
from dataclasses import asdict, replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from alembic import command
from income_analytics.application.cvm_magic_formula_normalization import (
    ADAPTER_VERSION,
    MagicFormulaAccountingAdapterV1,
    NormalizationStatus,
)
from income_analytics.application.issuer_market_cap import IssuerMarketCapResolutionStatus
from income_analytics.application.magic_formula_activation_gate import (
    ActivationGateIssuer,
    MagicFormulaActivationGate,
)
from income_analytics.application.magic_formula_fundamentals_assembler import (
    MagicFormulaFundamentalsAssembler,
)
from income_analytics.application.magic_formula_validation import CompanyNormalizationValidation
from income_analytics.infrastructure import magic_formula_snapshot_repository as repository
from income_analytics.infrastructure.cvm_fundamentals_data import CvmDataset, CvmStatementParser
from income_analytics.infrastructure.magic_formula_contract_repository import (
    CanonicalMagicFormulaRepository,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/cvm/phase2_v1"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
# Independent reported EBIT amounts, in BRL (not adapter-generated expectations).
EBIT = {
    "DFP": dict(
        zip(
            MANIFEST["issuers"],
            map(Decimal, ("4062000000", "31969000000", "2908592000", "201196000", "23423386000")),
        )
    ),
    "ITR": dict(
        zip(
            MANIFEST["issuers"],
            map(Decimal, ("2658000000", "37953000000", "2102436000", "-190621000", "16406273000")),
        )
    ),
}
# Explicit independent source-code specification; intentionally not imported RULES.
ACCOUNTS = {
    "ebit": ("3.05",),
    "cash_and_equivalents": ("1.01.01",),
    "financial_debt_short_term": ("2.01.04",),
    "financial_debt_long_term": ("2.02.01",),
    "operating_current_assets": ("1.01.03", "1.01.04"),
    "operating_current_liabilities": ("2.01.02",),
    "net_fixed_assets": ("1.02.03",),
}


def parsed(kind):
    entry = MANIFEST["datasets"][kind]
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, metadata in entry["members"].items():
            payload = (FIXTURES / name).read_bytes()
            assert hashlib.sha256(payload).hexdigest() == metadata["sha256"]
            archive.writestr(name, payload)
    return CvmStatementParser().parse(
        CvmDataset(
            kind,
            entry["url"],
            datetime(2026, 9, 16, tzinfo=UTC),
            buffer.getvalue(),
        )
    )


def selected(kind, issuer):
    return tuple(
        r
        for r in parsed(kind)
        if r.cvm_code == issuer and (r.statement != "DRE" or r.period_start == "2025-01-01")
    )


@pytest.fixture(params=["clean", "0014-copy"])
def migrated(request, tmp_path, monkeypatch):
    target = tmp_path / "current.db"
    config = Config(str(ROOT / "alembic.ini"))
    if request.param == "0014-copy":
        original = tmp_path / "original-0014.db"
        monkeypatch.setenv("INCOME_ANALYTICS_DATABASE", str(original))
        command.upgrade(config, "0014_b3_import_audit")
        old_engine = create_engine(f"sqlite:///{original.as_posix()}")
        with old_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO b3_import_batches "
                    "(id,file_name,file_hash,report_type,status,created_at) "
                    "VALUES ('sentinel','sample.xlsx','sha','income','APPLIED','2025-01-01')"
                )
            )
        old_engine.dispose()
        before = original.read_bytes()
        shutil.copy2(original, target)
    monkeypatch.setenv("INCOME_ANALYTICS_DATABASE", str(target))
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{target.as_posix()}")
    with engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT version_num FROM alembic_version"))
            == ScriptDirectory.from_config(config).get_current_head()
        )
        if request.param == "0014-copy":
            assert (
                conn.scalar(text("SELECT file_name FROM b3_import_batches WHERE id='sentinel'"))
                == "sample.xlsx"
            )
            assert original.read_bytes() == before
    constraints = inspect(engine).get_unique_constraints("magic_formula_fundamentals_snapshots")
    assert any(
        c["column_names"]
        == ["issuer_id", "financial_reference_date", "market_reference_date", "adapter_version"]
        for c in constraints
    )
    monkeypatch.setattr(repository, "SessionFactory", sessionmaker(bind=engine))
    # Migrations above must create the schema; repository startup cannot mask gaps.
    monkeypatch.setattr(repository, "initialize_database", lambda: None)
    yield engine
    engine.dispose()


@pytest.mark.parametrize("kind", ["DFP", "ITR"])
def test_official_multisector_pipeline(migrated, kind):
    repo = repository.SqliteMagicFormulaSnapshotRepository()
    for issuer, (name, sector) in MANIFEST["issuers"].items():
        # Raw CVM identifiers remain source locators; persistence uses the internal UUID.
        member = FIXTURES / f"{kind.lower()}_cia_aberta_BPA_con_2025.csv"
        with member.open(encoding="latin1", newline="") as source:
            source_issuer = next(
                row for row in csv.DictReader(source, delimiter=";") if row["CD_CVM"] == issuer
            )
        identity = CanonicalMagicFormulaRepository(Path(migrated.url.database)).register_issuer(
            cvm_code=issuer,
            cnpj=source_issuer["CNPJ_CIA"],
            display_name=name,
            slug=issuer,
        )
        records = selected(kind, issuer)
        metrics, lineage, status = MagicFormulaAccountingAdapterV1().normalize(records)
        assert status is NormalizationStatus.VALID
        raw = {r.account_code: r.value for r in records}
        assert metrics == {
            metric: sum((raw[c] for c in codes), Decimal(0)) * 1000
            for metric, codes in ACCOUNTS.items()
        }
        assert metrics["ebit"] == EBIT[kind][issuer]
        assert len(lineage) == 8
        assert all(
            item.normalized_value == item.raw_value * 1000
            and item.adapter_version == ADAPTER_VERSION
            and item.source_scale == "THOUSAND"
            for item in lineage
        )
        assert all(item.account_code != "1.01.02" for item in lineage)
        date = MANIFEST["datasets"][kind]["reference_date"]
        kwargs = dict(
            snapshot_repository=repo,
            market_reference_date=date,
            lineage=[asdict(item) for item in lineage],
            issuer_id=identity["issuer_id"],
            cvm_code=issuer,
            company_name=name,
            financial_reference_date=date,
            statement_type=kind,
            metrics=metrics,
            market_cap=Decimal("100000000000"),
        )
        fundamentals, snapshot_id = MagicFormulaFundamentalsAssembler().assemble_and_snapshot(
            **kwargs
        )
        assert MagicFormulaFundamentalsAssembler().assemble_and_snapshot(**kwargs)[1] == snapshot_id
        assert fundamentals.validation_status == "NOT_VALIDATED"
        assert (
            fundamentals.net_working_capital
            == metrics["operating_current_assets"] - metrics["operating_current_liabilities"]
        )
        assert fundamentals.enterprise_value == Decimal("100000000000") + fundamentals.net_debt
        validation_id = repo.save_validation(
            CompanyNormalizationValidation.compare(
                issuer_id=identity["issuer_id"],
                reference_date=date,
                adapter_version=ADAPTER_VERSION,
                metric="ebit",
                expected_value=EBIT[kind][issuer],
                actual_value=metrics["ebit"],
                notes=f"{sector}; accounting only; synthetic market cap; no release approval",
            )
        )
        with migrated.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT * FROM magic_formula_fundamentals_snapshots WHERE id=:id"),
                    {"id": snapshot_id},
                )
                .mappings()
                .one()
            )
            assert Decimal(json.loads(row["metrics_json"])["ebit"]) == EBIT[kind][issuer]
            assert json.loads(row["lineage_json"]) == json.loads(
                json.dumps([asdict(item) for item in lineage], default=str)
            )
            validation = (
                conn.execute(
                    text("SELECT * FROM company_normalization_validations WHERE id=:id"),
                    {"id": validation_id},
                )
                .mappings()
                .one()
            )
            assert validation["status"] == "PASS"
            assert Decimal(validation["difference"]) == 0
            assert Decimal(validation["expected_value"]) == Decimal(validation["actual_value"])
    with migrated.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM magic_formula_fundamentals_snapshots")) == 5
    gate = MagicFormulaActivationGate().evaluate(
        tuple(
            ActivationGateIssuer(
                issuer, IssuerMarketCapResolutionStatus.UNIT_UNRESOLVED, True, True
            )
            for issuer in MANIFEST["issuers"]
        )
    )
    assert gate.ranked_issuers == 0
    assert gate.tool_status == "VALIDATION_REQUIRED"
    assert "INSUFFICIENT_RESOLVED_UNIVERSE" in gate.critical_findings


def test_official_itr_rejects_quarter_plus_ytd():
    records = tuple(r for r in parsed("ITR") if r.cvm_code == "004170")
    assert (
        MagicFormulaAccountingAdapterV1().normalize(records)[2]
        is NormalizationStatus.INSUFFICIENT_DATA
    )


@pytest.mark.parametrize(
    "defect",
    ["missing_component", "duplicate", "individual", "issuer", "date", "period", "type", "scale"],
)
def test_official_data_rejects_unsafe_inputs(defect):
    records = selected("DFP", "004170")
    if defect == "missing_component":
        records = tuple(r for r in records if r.account_code != "1.01.04")
    elif defect == "duplicate":
        records += tuple(r for r in records if r.account_code == "3.05")
    else:
        changes = {
            "individual": {"statement_scope": "INDIVIDUAL"},
            "issuer": {"issuer_id": "other"},
            "date": {"reference_date": "2024-12-31"},
            "period": {"period_end": "2024-12-31"},
            "type": {"statement_type": "ITR"},
            "scale": {"currency_scale": "UNKNOWN"},
        }
        records = tuple(
            replace(r, **changes[defect]) if r.account_code == "3.05" else r for r in records
        )
    assert MagicFormulaAccountingAdapterV1().normalize(records)[2] is not NormalizationStatus.VALID
