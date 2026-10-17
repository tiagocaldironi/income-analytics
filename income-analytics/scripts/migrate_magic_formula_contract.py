"""Adopt only the four existing V2 artifacts; never materialize financial data."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from income_analytics.application.magic_formula_contract import (
    ADAPTER_VERSION,
    FINANCIAL_METRICS,
    canonicalize_golden,
)
from income_analytics.infrastructure.magic_formula_contract_repository import (
    CanonicalMagicFormulaRepository,
)

SAMPLE = ("weg", "suzano", "rumo", "telefonica")


def migrate_existing(database: Path, fixtures_directory: Path) -> list[dict]:
    repo = CanonicalMagicFormulaRepository(database)
    results = []
    for slug in SAMPLE:
        path = fixtures_directory / f"{slug}_2025.json"
        fixture = json.loads(path.read_text(encoding="utf8"))
        capital = fixture["capital"]["securities"]
        codes = {c["cvm_code"] for c in capital}
        cnpjs = {c["fca_source_reference"].split("|")[2] for c in capital}
        if codes != {fixture["issuer"]["cvm_code"]} or len(cnpjs) != 1:
            raise ValueError("GOLDEN_IDENTITY_CONFLICT")
        with repo.connection() as conn:
            candidates = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM magic_formula_fundamentals_snapshots WHERE adapter_version=? "
                    "AND financial_reference_date=?",
                    (ADAPTER_VERSION, fixture["reference"]["financial_reference_date"]),
                )
                if json.loads(row["metrics_json"]).get("cvm_code", "").lstrip("0")
                == fixture["issuer"]["cvm_code"].lstrip("0")
            ]
        if len(candidates) != 1:
            raise ValueError(f"{slug}: EXACTLY_ONE_EXISTING_V2_REQUIRED")
        before = candidates[0]
        issuer = repo.register_issuer(
            cvm_code=fixture["issuer"]["cvm_code"],
            cnpj=next(iter(cnpjs)),
            display_name=fixture["issuer"].get("display_name", fixture["issuer"].get("name")),
            slug=slug,
            issuer_id=fixture["issuer"]["issuer_id"] if fixture.get("schema_version") else None,
        )
        canonical = canonicalize_golden(fixture, issuer)
        if not canonical["expected"] == fixture["expected"]:
            raise AssertionError("EVIDENCE_MISMATCH")
        repo.adopt_existing_snapshot(before["id"], issuer["issuer_id"])
        fixture_hash = repo.register_golden(canonical)
        qa_id = repo.validate_snapshot(before["id"], fixture_hash)
        after = repo.read_snapshot(before["id"])
        old_metrics, new_metrics = (
            json.loads(before["metrics_json"]),
            json.loads(after["metrics_json"]),
        )
        if not {k: old_metrics[k] for k in FINANCIAL_METRICS} == {
            k: new_metrics[k] for k in FINANCIAL_METRICS
        }:
            raise AssertionError("EVIDENCE_MISMATCH")
        if not before["lineage_json"] == after["lineage_json"]:
            raise AssertionError("EVIDENCE_MISMATCH")
        path.write_text(
            json.dumps(canonical, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf8",
        )
        result = repo.eligibility(issuer["issuer_id"], canonical["reference_date"])
        with repo.connection() as conn:
            qa = dict(
                conn.execute(
                    "SELECT * FROM magic_formula_formal_qa WHERE id=?", (qa_id,)
                ).fetchone()
            )
        results.append(
            dict(
                slug=slug,
                issuer_id=issuer["issuer_id"],
                snapshot_id=before["id"],
                validation_status=after["validation_status"],
                qa_decision_id=qa_id,
                dimensions=json.loads(qa["evidence_json"]),
                eligibility=asdict(result),
                financial_metrics_unchanged=True,
                lineage_unchanged=True,
            )
        )
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--fixtures-directory", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(migrate_existing(args.database, args.fixtures_directory), indent=2))
