"""Validate the frozen sample, then apply only document-backed unit evidence."""

import argparse
import json
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from income_analytics.application.historical_shares_units import (
    POLICY_VERSION,
    apply_readiness,
    outstanding,
    resolve,
)
from income_analytics.application.magic_formula_contract import digest
from income_analytics.application.magic_formula_universe import coverage, digits
from income_analytics.infrastructure.cvm_historical_shares_document import read_unit_evidence
from income_analytics.infrastructure.magic_formula_contract_repository import (
    CanonicalMagicFormulaRepository,
)
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)
from income_analytics.infrastructure.magic_formula_universe_sources import csv_records


def run(universe_database, universe_id, sample_path, evidence_directory, output, persist=False):
    repository = MagicFormulaUniverseRepository(universe_database)
    before = repository.read(universe_id)
    sample = json.loads(sample_path.read_text(encoding="utf8"))
    if sample["universe_snapshot_id"] != universe_id:
        raise ValueError("SAMPLE_UNIVERSE_MISMATCH")
    start = perf_counter()
    indexed = {i["issuer_id"]: i for i in before["issuers"]}
    evidence = {}
    sample_results = []
    controls_pass = True
    for item in sample["issuers"]:
        path = evidence_directory / (item["document"]["ID_DOC"] + "-evidence.zip")
        proof = read_unit_evidence(path) if path.exists() else None
        evidence[item["issuer_id"]] = proof
        resolution = resolve(indexed[item["issuer_id"]], item["capital"], proof)
        record = dict(
            issuer_id=item["issuer_id"],
            display_name=item["display_name"],
            control=item["control"],
            strata=item["strata"],
            resolution=resolution,
        )
        if item["control"]:
            canonical = CanonicalMagicFormulaRepository(Path("income_analytics.db"))
            issuer = indexed[item["issuer_id"]]
            snapshot = canonical.read_snapshot(issuer["canonical_snapshot_id"])
            components = [
                c
                for entry in json.loads(snapshot["lineage_json"])
                for c in entry.get("market_cap_components", [])
            ]
            approved = {
                c["share_class"]: str(
                    int(Decimal(str(c["issued_shares"])) - Decimal(str(c["treasury_shares"])))
                )
                for c in components
            }
            actual = outstanding(resolution) if resolution["status"] == "RESOLVED" else {}
            record["control_pass"] = bool(approved) and all(
                actual.get(k) == v for k, v in approved.items()
            )
            controls_pass = controls_pass and record["control_pass"]
        sample_results.append(record)
    sample_seconds = perf_counter() - start
    states = Counter(i["resolution"]["status"] for i in sample_results)
    # No generic default is approved. Only exact document evidence may propagate.
    accepted = (
        controls_pass
        and states.get("REVIEW_REQUIRED", 0) == 0
        and states.get("SOURCE_SCHEMA_ERROR", 0) == 0
    )
    start = perf_counter()
    year = before["reference_date"][:4]
    capital_rows = list(
        csv_records(
            Path(f"data/cvm/dfp_cia_aberta_{year}.zip"),
            f"dfp_cia_aberta_composicao_capital_{year}.csv",
        )
    )
    document_rows = list(
        csv_records(Path(f"data/cvm/dfp_cia_aberta_{year}.zip"), f"dfp_cia_aberta_{year}.csv")
    )
    resolutions = {}
    if accepted:
        for issuer in before["issuers"]:
            if issuer["methodology_eligibility"] != "ELIGIBLE" or not (
                "UNIT_UNRESOLVED" in issuer["data_reason_codes"]
                or issuer["canonical_status"] == "RESOLVED"
            ):
                continue
            rows = [
                r
                for r in capital_rows
                if digits(r["CNPJ_CIA"]) == issuer["cnpj"]
                and r["DT_REFER"] == before["reference_date"]
            ]
            if len(rows) != 1:
                continue
            proof = evidence.get(issuer["issuer_id"])
            if proof is None:
                docs = [
                    d
                    for d in document_rows
                    if digits(d["CNPJ_CIA"]) == issuer["cnpj"]
                    and d["DT_REFER"] == rows[0]["DT_REFER"]
                    and d["VERSAO"] == rows[0]["VERSAO"]
                ]
                if len(docs) == 1:
                    path = evidence_directory / (docs[0]["ID_DOC"] + "-evidence.zip")
                    proof = read_unit_evidence(path) if path.exists() else None
            resolutions[issuer["issuer_id"]] = resolve(issuer, rows[0], proof)
    resolution_seconds = perf_counter() - start
    start = perf_counter()
    after_issuers = apply_readiness(before["issuers"], resolutions)
    measured = coverage(after_issuers)
    if after_issuers != apply_readiness(list(reversed(before["issuers"])), resolutions)[::-1]:
        raise ValueError("NON_DETERMINISTIC_UNIT_RESOLUTION")
    if measured["methodology_distribution"] != before["coverage"]["methodology_distribution"]:
        raise ValueError("METHODOLOGY_CHANGED")
    migrated = [
        dict(
            issuer_id=i["issuer_id"],
            primary_gap_before=(indexed[i["issuer_id"]]["data_reason_codes"] or [None])[0],
            primary_gap_after=(i["data_reason_codes"] or [None])[0],
            reasons_before=indexed[i["issuer_id"]]["data_reason_codes"],
            reasons_after=i["data_reason_codes"],
        )
        for i in after_issuers
        if i["methodology_eligibility"] == "ELIGIBLE"
    ]
    capital_market_ready = sum(
        i["market_readiness"]["capital_ready"]
        and i["market_readiness"]["security_ready"]
        and i["market_readiness"]["price_ready"]
        for i in after_issuers
        if i["methodology_eligibility"] == "ELIGIBLE"
    )
    recompute_seconds = perf_counter() - start
    audit = dict(
        policy_version=POLICY_VERSION,
        parent_universe_snapshot_id=universe_id,
        sample_results=sample_results,
        sample_counts=dict(states),
        sample_size=len(sample_results),
        generalization_decision="DOCUMENT_BOUND_ONLY" if accepted else "DO_NOT_GENERALIZE",
        global_default_authorized=False,
        full_universe_policy_evaluations=len(resolutions),
        controls_pass=controls_pass,
        before_coverage=before["coverage"],
        after_coverage=measured,
        market_cap_ready=capital_market_ready,
        gap_migration=migrated,
        determinism_status="PASS",
        magnitude_inference_used=False,
        issuer_hardcode_used=False,
        timings=dict(
            sample_validation_seconds=sample_seconds,
            full_universe_resolution_seconds=resolution_seconds,
            coverage_recomputation_seconds=recompute_seconds,
        ),
    )
    document = deepcopy(before)
    document.update(
        universe_snapshot_id=str(uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        status="PASS" if accepted else "FAIL",
        issuers=after_issuers,
        coverage=measured,
        unit_resolution_run=audit,
    )
    output.mkdir(parents=True, exist_ok=True)
    if persist:
        repository.save(document)
        restored = MagicFormulaUniverseRepository(universe_database).read(
            document["universe_snapshot_id"]
        )
        if restored != document:
            raise ValueError("UNIT_RESOLUTION_READBACK_FAIL")
    (output / "universe-snapshot.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf8"
    )
    summary = dict(
        universe_snapshot_id=document["universe_snapshot_id"],
        generalization_decision=audit["generalization_decision"],
        sample_counts=dict(states),
        before=before["coverage"],
        after=measured,
        market_cap_ready=capital_market_ready,
        controls_pass=controls_pass,
        unit_resolution_readback="PASS" if persist else "NOT_PERSISTED",
        lineage_digest=digest(resolutions),
        timings=audit["timings"],
    )
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf8"
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--universe-database", type=Path, default=Path("data/magic_formula/universe_snapshots.db")
    )
    parser.add_argument("--universe-id", required=True)
    parser.add_argument("--sample-path", type=Path, required=True)
    parser.add_argument("--evidence-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--persist", action="store_true")
    print(json.dumps(run(**vars(parser.parse_args())), indent=2))
