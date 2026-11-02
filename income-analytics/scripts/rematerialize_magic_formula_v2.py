"""Materialize auditable V2 snapshots from the four official local source archives."""

from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path

from income_analytics.application.magic_formula_accounting_evidence import (
    MagicFormulaAccountingEvidenceBuilder,
)
from income_analytics.application.magic_formula_fundamentals_assembler import (
    MagicFormulaFundamentalsAssembler,
)
from income_analytics.application.magic_formula_golden_evidence_builder import (
    MagicFormulaGoldenEvidenceBuilder,
)
from income_analytics.application.magic_formula_market_evidence import (
    MagicFormulaMarketEvidenceAgent,
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
from income_analytics.infrastructure.magic_formula_snapshot_repository import (
    SqliteMagicFormulaSnapshotRepository,
)

ROOT = Path("data/cvm")
CONFIG = (
    ("weg", "WEG S.A.", "005410", "84.429.695/0001-11", "WEGE3"),
    ("suzano", "Suzano S.A.", "013986", "16.404.287/0001-55", "SUZB3"),
    ("rumo", "Rumo S.A.", "017450", "02.387.241/0001-60", "RAIL3"),
    ("telefonica", "Telefônica Brasil S.A.", "017671", "02.558.157/0001-62", "VIVT3"),
)


def dataset(name, kind):
    p = ROOT / name
    return CvmDataset(kind, p.name, datetime.now(UTC), p.read_bytes())


def run():
    dfp = dataset("dfp_cia_aberta_2025.zip", "DFP")
    fca = dataset("fca_cia_aberta_2025.zip", "FCA")
    raw, caps, fcas = (
        CvmStatementParser().parse(dfp),
        CvmCapitalCompositionParser().parse(dfp),
        CvmFcaSecurityParser().parse(fca),
    )
    prices = MagicFormulaMarketEvidenceAgent(B3CotahistMarketDataProvider()).obtain
    repo, assembler, golden = (
        SqliteMagicFormulaSnapshotRepository(),
        MagicFormulaFundamentalsAssembler(),
        MagicFormulaGoldenEvidenceBuilder(),
    )
    for issuer, name, code, cnpj, ticker in CONFIG:
        records = tuple(
            x
            for x in raw
            if x.cvm_code == code
            and x.reference_date == "2025-12-31"
            and x.statement_scope == "CONSOLIDATED"
        )
        acc = MagicFormulaAccountingEvidenceBuilder().build(records)
        capital = next(x for x in caps if x.cnpj == cnpj and x.reference_date == "2025-12-31")
        sec = SecurityCapitalEvidenceAssembler().build(
            issuer=IssuerEvidenceIdentity(issuer, code, cnpj),
            composition=capital,
            fca_records=fcas,
            requests=(
                SecurityClassEvidenceRequest(
                    f"BR:{ticker}", ticker, "ON", "UNIT", __import__("decimal").Decimal("1")
                ),
            ),
        )
        price = prices(ticker=ticker, requested_reference_date=date(2025, 12, 31))
        fixture = golden.build(
            issuer_name=name,
            accounting=acc,
            security_capital=sec,
            prices=(price,),
            market_reference_date="2025-12-31",
        )
        if fixture.status.value != "READY_FOR_VALIDATION":
            raise ValueError(f"{issuer}: incomplete golden evidence: {fixture.missing}")
        target = Path("tests/golden/magic_formula") / f"{issuer}_2025.json"
        if target.exists() and '"status":"APPROVED"' in target.read_text(encoding="utf-8"):
            raise ValueError(f"{issuer}: approved fixture cannot be replaced")
        target.write_text(
            __import__("json").dumps(fixture.fixture, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        metrics = {x.metric: x.normalized_value for x in acc.components}
        market_cap = sec.components[0].normalized_quantity * price.price
        lineage = [
            dict(asdict(source), metric=component.metric, rule_id=component.rule_id)
            for component in acc.components
            for source in component.sources
        ]
        lineage += [
            {
                "market_cap_components": [
                    dict(
                        asdict(sec.components[0]),
                        price=str(price.price),
                        price_effective_date=str(price.effective_date),
                        price_source=price.source,
                        price_record_reference=price.record_reference,
                    )
                ]
            }
        ]
        _, sid = assembler.assemble_and_snapshot(
            snapshot_repository=repo,
            market_reference_date="2025-12-31",
            lineage=lineage,
            issuer_id=issuer,
            cvm_code=code,
            company_name=name,
            financial_reference_date="2025-12-31",
            statement_type="DFP",
            metrics=metrics,
            market_cap=market_cap,
        )
        print(f"{issuer}: {sid}")


if __name__ == "__main__":
    run()
