"""Recover Petrobras from official local archives; never invokes ranking.

Run against a migrated database after taking an SQLite backup. Source files
must already exist locally: this workflow does not download or substitute data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from income_analytics.application.cvm_magic_formula_normalization import (
    MagicFormulaAccountingAdapterV1,
)
from income_analytics.application.issuer_market_cap import (
    IssuerMarketCapService,
    NormalizedSecurityPrice,
    ShareClassCapital,
)
from income_analytics.application.magic_formula_accounting_evidence import (
    MagicFormulaAccountingEvidenceBuilder,
)
from income_analytics.application.magic_formula_activation_gate import MagicFormulaActivationGate
from income_analytics.application.magic_formula_contract import DIMENSIONS, digest
from income_analytics.application.magic_formula_fundamentals_assembler import (
    MagicFormulaFundamentalsAssembler,
)
from income_analytics.application.magic_formula_golden_evidence_builder import (
    MagicFormulaGoldenEvidenceBuilder,
)
from income_analytics.application.magic_formula_security_capital_evidence import (
    CvmFcaSecurityParser,
    IssuerEvidenceIdentity,
    SecurityCapitalEvidenceAssembler,
    SecurityClassEvidenceRequest,
)
from income_analytics.infrastructure.b3_cotahist_market_data import B3CotahistMarketDataProvider
from income_analytics.infrastructure.cvm_capital_structure import CvmCapitalCompositionParser
from income_analytics.infrastructure.cvm_fundamentals_data import CvmDataset, CvmStatementParser
from income_analytics.infrastructure.magic_formula_contract_repository import (
    CanonicalMagicFormulaRepository,
)
from income_analytics.infrastructure.magic_formula_raw_verification import (
    OfficialRawVerifier,
    require,
)
from income_analytics.infrastructure.magic_formula_snapshot_repository import (
    SqliteMagicFormulaSnapshotRepository,
)

REFERENCE = "2025-12-31"
TICKERS = (("PETR3", "ON"), ("PETR4", "PN"))
TABLES = (
    "magic_formula_issuers",
    "magic_formula_golden_fixtures",
    "magic_formula_fundamentals_snapshots",
    "magic_formula_formal_qa",
)


def dump_rows(repo):
    with repo.connection() as conn:
        return {
            table: [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY rowid")]
            for table in TABLES
        }


def assert_preserved(before, after):
    for table, rows in before.items():
        require(all(row in after[table] for row in rows), "EXISTING_ARTIFACT_CHANGED:" + table)


def dataset(directory, name, kind):
    path = directory / name
    return CvmDataset(kind, name, datetime.now(UTC), path.read_bytes())


def build_evidence(issuer, cvm_directory, market_directory):
    dfp = dataset(cvm_directory, "dfp_cia_aberta_2025.zip", "DFP")
    fca = dataset(cvm_directory, "fca_cia_aberta_2025.zip", "FCA")
    raw = tuple(
        replace(r, issuer_id=issuer["issuer_id"])
        for r in CvmStatementParser().parse(dfp)
        if r.cvm_code == issuer["cvm_code"]
        and r.reference_date == REFERENCE
        and r.statement_scope == "CONSOLIDATED"
    )
    accounting = MagicFormulaAccountingEvidenceBuilder().build(raw)
    compositions = [
        c
        for c in CvmCapitalCompositionParser().parse(dfp)
        if "".join(x for x in c.cnpj if x.isdigit()) == issuer["cnpj"]
        and c.reference_date == REFERENCE
    ]
    composition = OfficialRawVerifier.one(compositions, "PETROBRAS_CAPITAL")
    security = SecurityCapitalEvidenceAssembler().build(
        issuer=IssuerEvidenceIdentity(issuer["issuer_id"], issuer["cvm_code"], issuer["cnpj"]),
        composition=composition,
        fca_records=CvmFcaSecurityParser().parse(fca),
        requests=tuple(
            SecurityClassEvidenceRequest("BR:" + t, t, c, "UNIT", Decimal(1)) for t, c in TICKERS
        ),
    )
    # Enforce local sources before calling the standard provider (which also supports downloads).
    require((market_directory / "COTAHIST_A2025.ZIP").is_file(), "MISSING_LOCAL_COTAHIST")
    provider = B3CotahistMarketDataProvider(cache_directory=market_directory)
    verifier = OfficialRawVerifier(cvm_directory, market_directory)
    quotes = verifier.quotes(REFERENCE, tuple(t for t, _ in TICKERS))
    prices = []
    for ticker, _ in TICKERS:
        price = provider.price_evidence_on(ticker, date.fromisoformat(REFERENCE))
        q = verifier.one(
            [q for q in quotes if q["record_reference"] == price.record_reference],
            price.record_reference,
        )
        prices.append(replace(price, isin=q["isin"] or None))
    prices = tuple(prices)
    built = MagicFormulaGoldenEvidenceBuilder().build(
        issuer_name=issuer["display_name"],
        accounting=accounting,
        security_capital=security,
        prices=prices,
        market_reference_date=REFERENCE,
        canonical_issuer=issuer,
    )
    require(built.status.value == "READY_FOR_VALIDATION", "INCOMPLETE:" + str(built.missing))
    # Acceptance anchors are checks only, never inputs to builders or calculations.
    anchors = {
        "PETR3": ("7442231382", "32.57", "242393476111.74"),
        "PETR4": ("5446501379", "30.82", "167861172500.78"),
    }
    for cap in security.components:
        price = next(p for p in prices if p.ticker == cap.ticker)
        shares, close, partial = map(Decimal, anchors[cap.ticker])
        require(
            cap.normalized_quantity == shares
            and price.price == close
            and cap.normalized_quantity * price.price == partial,
            "ANCHOR:" + cap.ticker,
        )
        require(price.effective_date == date(2025, 12, 30), "PRICE_DATE")
    require(
        Decimal(built.fixture["expected"]["market_cap"]) == Decimal("410254648612.52"),
        "TOTAL_MARKET_CAP_ANCHOR",
    )
    return built.fixture, raw, security, prices


def production_inputs(raw, security, prices):
    metrics, accounting_lineage, status = MagicFormulaAccountingAdapterV1().normalize(raw)
    require(status.value == "VALID", "NORMALIZATION:" + status.value)
    capitals = tuple(
        ShareClassCapital(
            issuer_id=c.issuer_id,
            security_id=c.security_id,
            ticker=c.ticker,
            share_class=c.share_class,
            shares_outstanding=c.normalized_quantity,
            reference_date=c.reference_date,
            source=c.source,
            source_reference=c.source_reference,
        )
        for c in security.components
    )
    normalized_prices = tuple(
        NormalizedSecurityPrice(
            security_id=next(c.security_id for c in security.components if c.ticker == p.ticker),
            ticker=p.ticker,
            requested_reference_date=p.requested_reference_date,
            effective_date=p.effective_date,
            price=p.price,
            currency=p.currency,
            source=p.source,
            source_reference=p.record_reference,
        )
        for p in prices
    )
    market_cap, calculated = IssuerMarketCapService().calculate(capitals, normalized_prices)
    lineage = []
    for item in accounting_lineage:
        record = OfficialRawVerifier.one(
            [
                r
                for r in raw
                if r.account_code == item.account_code and r.period_start == item.period_start
            ],
            item.account_code,
        )
        lineage.append(
            dict(
                asdict(item),
                statement=record.statement,
                currency=item.source_currency,
                currency_scale=item.source_scale,
                multiplier=item.normalization_multiplier,
                source_reference=MagicFormulaAccountingEvidenceBuilder.source_reference(record),
            )
        )
    components = []
    for cap, calculated_cap in zip(security.components, calculated, strict=True):
        price = next(p for p in prices if p.ticker == cap.ticker)
        components.append(
            dict(
                asdict(cap),
                **calculated_cap,
                price_record_reference=price.record_reference,
                isin=price.isin,
            )
        )
    lineage.append({"market_cap_components": components})
    return metrics, market_cap, lineage


def recover(database: Path, cvm_directory: Path, market_directory: Path, output: Path):
    repo = CanonicalMagicFormulaRepository(database)
    before = dump_rows(repo)
    require(
        not any(i["cvm_code"] == "009512" for i in before[TABLES[0]]),
        "PETROBRAS_ALREADY_EXISTS_REVIEW_BEFORE_RETRY",
    )
    with repo.connection() as conn:
        heads = [
            row[0] for row in conn.execute("SELECT version_num FROM alembic_version").fetchall()
        ]
        require(len(heads) == 1, "SCHEMA_HEAD_COUNT")
        # The canonical evidence contract was introduced at 0016. Portfolio
        # migrations 0017+ are valid descendants and must not make the
        # Petrobras recovery reject a newer, compatible schema.
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        project_root = Path(__file__).resolve().parents[1]
        script = ScriptDirectory.from_config(Config(str(project_root / "alembic.ini")))
        revision = script.get_revision(heads[0])
        ancestors: set[str] = set()
        while revision is not None and revision.revision not in ancestors:
            ancestors.add(revision.revision)
            parent = revision.down_revision
            revision = script.get_revision(parent) if isinstance(parent, str) else None
        require("0016_magic_formula_canonical_contract" in ancestors, "SCHEMA_HEAD")
    issuer = repo.register_issuer(
        cvm_code="009512",
        cnpj="33.000.167/0001-01",
        display_name="Petróleo Brasileiro S.A. Petrobras",
        slug="petrobras",
    )
    fixture, raw, security, prices = build_evidence(issuer, cvm_directory, market_directory)
    output.mkdir(parents=True, exist_ok=True)
    target = output / "petrobras_2025.json"
    require(not target.exists(), "GOLDEN_OUTPUT_EXISTS")
    target.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf8"
    )
    # Serialization round-trip precedes DB storage; both handles are closed before reload.
    fixture_hash = repo.register_golden(json.loads(target.read_text(encoding="utf8")))
    with repo.connection() as conn:
        fixture = json.loads(
            conn.execute(
                "SELECT fixture_json FROM magic_formula_golden_fixtures WHERE fixture_hash=?",
                (fixture_hash,),
            ).fetchone()[0]
        )
    require(digest(fixture) == fixture_hash, "GOLDEN_ROUNDTRIP")
    receipts = OfficialRawVerifier(cvm_directory, market_directory).verify(fixture)
    metrics, cap, lineage = production_inputs(raw, security, prices)
    engine = create_engine("sqlite:///" + database.resolve().as_posix(), poolclass=NullPool)
    try:
        writer = SqliteMagicFormulaSnapshotRepository(
            session_factory=sessionmaker(bind=engine),
            initialize=lambda: None,
        )
        _, snapshot_id = MagicFormulaFundamentalsAssembler().assemble_and_snapshot(
            snapshot_repository=writer,
            market_reference_date=REFERENCE,
            lineage=lineage,
            issuer_id=issuer["issuer_id"],
            cvm_code=issuer["cvm_code"],
            company_name=issuer["display_name"],
            financial_reference_date=REFERENCE,
            statement_type="DFP",
            metrics=metrics,
            market_cap=cap,
        )
    finally:
        engine.dispose()
    initial = repo.read_snapshot(snapshot_id)
    require(initial["validation_status"] == "NOT_VALIDATED", "INITIAL_VALIDATION")
    (output / "snapshot-initial.json").write_text(json.dumps(initial, indent=2), encoding="utf8")
    qa_id = repo.validate_snapshot(snapshot_id, fixture_hash)
    # Independent new connections: the writer, QA transaction, and all prior reads are closed.
    reopened = CanonicalMagicFormulaRepository(database)
    snapshot = reopened.read_snapshot(snapshot_id)
    with reopened.connection() as conn:
        qa = dict(
            conn.execute("SELECT * FROM magic_formula_formal_qa WHERE id=?", (qa_id,)).fetchone()
        )
        stored = conn.execute(
            "SELECT fixture_json FROM magic_formula_golden_fixtures WHERE fixture_hash=?",
            (fixture_hash,),
        ).fetchone()[0]
        persisted_issuer = dict(
            conn.execute(
                "SELECT * FROM magic_formula_issuers WHERE issuer_id=?", (issuer["issuer_id"],)
            ).fetchone()
        )
    require(
        persisted_issuer == issuer and json.loads(stored) == fixture, "READBACK_IDENTITY_GOLDEN"
    )
    require(
        qa["snapshot_id"] == snapshot_id
        and qa["final_status"] == "PASS"
        and all(qa[d] == "PASS" for d in DIMENSIONS),
        "FORMAL_QA:" + qa["evidence_json"],
    )
    require(snapshot["validation_status"] == "PASS", "VALIDATION_READBACK")
    require("validation_status" not in json.loads(snapshot["metrics_json"]), "JSON_VALIDATION")
    (output / "snapshot-readback.json").write_text(json.dumps(snapshot, indent=2), encoding="utf8")
    (output / "qa-readback.json").write_text(json.dumps(qa, indent=2), encoding="utf8")
    require(
        all(initial[k] == snapshot[k] for k in initial if k != "validation_status"),
        "VALIDATION_CHANGED_FINANCIAL_ARTIFACT",
    )
    decision = reopened.eligibility(issuer["issuer_id"], REFERENCE, snapshot_id=snapshot_id)
    require(decision.eligible and decision.issuer_status == "RESOLVED", "ELIGIBILITY")
    after = dump_rows(reopened)
    assert_preserved(before, after)
    policies = {
        i["slug"]: asdict(reopened.eligibility(i["issuer_id"], REFERENCE)) for i in after[TABLES[0]]
    }
    sample = ("weg", "suzano", "rumo", "telefonica", "petrobras")
    count = sum(
        policies.get(s, {}).get("eligible", False) and policies[s]["issuer_status"] == "RESOLVED"
        for s in sample
    )
    gate = MagicFormulaActivationGate().evaluate_canonical(
        reopened,
        tuple(i["issuer_id"] for i in after[TABLES[0]] if i["slug"] in sample),
        REFERENCE,
    )
    ready = count == len(sample) and not gate.critical_findings
    require(
        gate.tool_status == "VALIDATION_REQUIRED" and gate.ranked_issuers == 0,
        "RANKING_MUST_REMAIN_INACTIVE",
    )
    source_hashes = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (
            cvm_directory / "dfp_cia_aberta_2025.zip",
            cvm_directory / "fca_cia_aberta_2025.zip",
            market_directory / "COTAHIST_A2025.ZIP",
        )
    }
    result = dict(
        issuer=issuer,
        fixture_hash=fixture_hash,
        snapshot_id=snapshot_id,
        qa_id=qa_id,
        initial_validation_status=initial["validation_status"],
        validation_status=snapshot["validation_status"],
        dimensions={d: qa[d] for d in DIMENSIONS},
        readback_status="PASS",
        receipts=receipts,
        metrics=json.loads(snapshot["metrics_json"]),
        policies=policies,
        source_hashes=source_hashes,
        existing_artifacts_unchanged=True,
        preserved_artifact_counts={table: len(rows) for table, rows in before.items()},
        baseline_artifacts_digest=digest(before),
        validated_resolved_issuers=count,
        multisector_golden_gate="PASS" if ready else "BLOCKED",
        ranking_gate="READY" if ready else "BLOCKED",
        activation_gate=asdict(gate),
        tool_status="VALIDATION_REQUIRED",
        ranking_status="INACTIVE",
    )
    (output / "recovery-result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf8"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--cvm-directory", type=Path, default=Path("data/cvm"))
    parser.add_argument("--market-directory", type=Path, default=Path("data/cotahist"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--backup", required=True, type=Path)
    args = parser.parse_args()
    require(not args.backup.exists(), "BACKUP_ALREADY_EXISTS")
    source = sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        destination = sqlite3.connect(args.backup)
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()
    result = recover(args.database, args.cvm_directory, args.market_directory, args.output)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
