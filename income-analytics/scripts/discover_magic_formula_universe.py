"""Discover candidate issuers and measure coverage without running any ranking."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from income_analytics.application.magic_formula_contract import METHODOLOGY_VERSION, digest
from income_analytics.application.magic_formula_universe import (
    UNIVERSE_POLICY_VERSION,
    classify_candidates,
    coverage,
    discover_candidates,
    evaluate_readiness,
)
from income_analytics.infrastructure.magic_formula_contract_repository import (
    CanonicalMagicFormulaRepository,
)
from income_analytics.infrastructure.magic_formula_ranking_repository import (
    MagicFormulaRankingRepository,
)
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)
from income_analytics.infrastructure.magic_formula_universe_sources import (
    discovery_sources,
    readiness_sources,
    source_manifest,
)


def canonical_state(repository):
    with repository.connection() as conn:
        return {
            table: [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY rowid")]
            for table in (
                "magic_formula_issuers",
                "magic_formula_golden_fixtures",
                "magic_formula_fundamentals_snapshots",
                "magic_formula_formal_qa",
            )
        }


def canonical_context(repository, reference):
    with repository.connection() as conn:
        issuers = [dict(i) for i in conn.execute("SELECT * FROM magic_formula_issuers")]
    result = {}
    for issuer in issuers:
        item = dict(issuer)
        decision = repository.eligibility(issuer["issuer_id"], reference)
        if decision.issuer_status == "RESOLVED":
            snapshot = repository.read_snapshot(decision.snapshot_id)
            lineage = json.loads(snapshot["lineage_json"])
            item["approved"] = dict(
                snapshot_id=decision.snapshot_id,
                qa_id=decision.qa_decision_id,
                ranking_eligible=decision.eligible,
                capital=[c for entry in lineage for c in entry.get("market_cap_components", [])],
            )
        result[issuer["issuer_id"]] = item
    return result


def validated_anchors(ranking_database):
    repository = MagicFormulaRankingRepository(ranking_database)
    with repository.connection() as conn:
        ids = [
            r[0]
            for r in conn.execute(
                "SELECT artifact_id FROM magic_formula_ranking_artifacts "
                "WHERE kind='RANKING_SNAPSHOT'"
            )
        ]
    artifacts = [repository.read(i) for i in ids]
    passed = [
        a for a in artifacts if a["status"] == "PASS" and a["independent_qa"]["status"] == "PASS"
    ]
    if not passed:
        raise ValueError("MISSING_VALIDATED_RANKING_ENGINE_ARTIFACT")
    latest = max(passed, key=lambda a: (a["created_at"], a["ranking_snapshot_id"]))
    if len(latest["inputs"]) != 5:
        raise ValueError("VALIDATED_SAMPLE_MUST_HAVE_FIVE")
    return latest


def run(database, ranking_database, universe_database, cvm_directory, market_directory, output):
    if universe_database.resolve() in (database.resolve(), ranking_database.resolve()):
        raise ValueError("SEPARATE_UNIVERSE_ARTIFACT_DATABASE_REQUIRED")
    canonical = CanonicalMagicFormulaRepository(database)
    before = canonical_state(canonical)
    anchors = validated_anchors(ranking_database)
    reference = anchors["reference_date"]
    timings = {}
    start = perf_counter()
    sources = source_manifest(cvm_directory, market_directory, int(reference[:4]))
    general, securities = discovery_sources(cvm_directory, int(reference[:4]))
    candidates, rejected = discover_candidates(general, securities, reference)
    timings["discovery_seconds"] = perf_counter() - start
    start = perf_counter()
    context = canonical_context(canonical, reference)
    classified = classify_candidates(candidates, context, reference)
    timings["classification_seconds"] = perf_counter() - start
    start = perf_counter()
    tickers = {
        r["Codigo_Negociacao"].strip().upper() for c in candidates for r in c["raw_securities"]
    }
    accounts, capitals, quotes = readiness_sources(
        cvm_directory, market_directory, reference, tickers
    )
    issuers = evaluate_readiness(classified, accounts, capitals, quotes, context, reference)
    measured = coverage(issuers)
    timings["readiness_seconds"] = perf_counter() - start
    # Independent order of ingestion must preserve IDs, statuses, reasons and counts.
    start = perf_counter()
    reversed_candidates, reversed_rejected = discover_candidates(
        list(reversed(general)), list(reversed(securities)), reference
    )
    repeated = evaluate_readiness(
        classify_candidates(reversed_candidates, context, reference),
        list(reversed(accounts)),
        list(reversed(capitals)),
        list(reversed(quotes)),
        context,
        reference,
    )
    if issuers != repeated or rejected != reversed_rejected:
        raise ValueError("UNIVERSE_DETERMINISM_FAIL")
    timings["determinism_seconds"] = perf_counter() - start
    indexed = {i["issuer_id"]: i for i in issuers if i["issuer_id"] is not None}
    regression = []
    for anchor in anchors["inputs"]:
        found = indexed.get(anchor["issuer_id"])
        regression.append(
            dict(
                issuer_id=anchor["issuer_id"],
                discovered=found is not None,
                methodology_eligible=bool(found and found["methodology_eligibility"] == "ELIGIBLE"),
                data_ready=bool(found and found["data_readiness_status"] == "FULL_DATA_READY"),
                canonical_resolved=bool(found and found["canonical_status"] == "RESOLVED"),
                snapshot_unchanged=bool(
                    found and found["canonical_snapshot_id"] == anchor["snapshot_id"]
                ),
            )
        )
    golden_pass = all(all(v for k, v in row.items() if k != "issuer_id") for row in regression)
    resolved_ids = [i["issuer_id"] for i in issuers if i["identity_status"] == "RESOLVED"]
    duplicates_pass = len(resolved_ids) == len(set(resolved_ids)) and len(issuers) == len(
        {i["candidate_key"] for i in issuers}
    )
    if canonical_state(canonical) != before:
        raise ValueError("CANONICAL_ARTIFACT_CHANGED")
    if source_manifest(cvm_directory, market_directory, int(reference[:4])) != sources:
        raise ValueError("SOURCE_ARCHIVES_CHANGED")
    document = dict(
        universe_snapshot_id=str(uuid4()),
        universe_type="CANDIDATE_PUBLISHABLE_UNIVERSE",
        reference_date=reference,
        methodology_version=METHODOLOGY_VERSION,
        universe_policy_version=UNIVERSE_POLICY_VERSION,
        created_at=datetime.now(UTC).isoformat(),
        status="PASS" if golden_pass and duplicates_pass else "FAIL",
        reference_policy=dict(
            accounting_reference=reference,
            capital_reference=reference,
            requested_market_date=reference,
            effective_market_date="LAST_OFFICIAL_CLOSE_ON_OR_BEFORE_WITHIN_7_CALENDAR_DAYS",
            source_vintage="RETROSPECTIVE_PINNED_ARCHIVES_NOT_POINT_IN_TIME_BACKTEST",
        ),
        sources=sources,
        issuers=issuers,
        coverage=measured,
        discovery_audit=dict(
            fca_general_rows=len(general),
            fca_security_rows=len(securities),
            omitted_security_records=rejected,
        ),
        validated_ranking_snapshot_id=anchors["ranking_snapshot_id"],
        golden_five_regression=regression,
        canonical_before_digest=digest(before),
        canonical_after_digest=digest(canonical_state(canonical)),
        duplicate_issuer_status="PASS" if duplicates_pass else "FAIL",
        determinism_status="PASS",
        tool_status="VALIDATION_REQUIRED",
        ranking_status="INACTIVE",
    )
    start = perf_counter()
    repository = MagicFormulaUniverseRepository(universe_database)
    repository.initialize()
    repository.save(document)
    restored = MagicFormulaUniverseRepository(universe_database).read(
        document["universe_snapshot_id"]
    )
    if restored != document:
        raise ValueError("UNIVERSE_READBACK_FAIL")
    timings["persistence_seconds"] = perf_counter() - start
    output.mkdir(parents=True, exist_ok=True)
    (output / "universe-snapshot.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf8"
    )
    summary = dict(
        universe_snapshot_id=document["universe_snapshot_id"],
        universe_database=str(universe_database.resolve()),
        phase1_gate=document["status"],
        universe_readback_status="PASS",
        coverage=measured,
        golden_five_regression=regression,
        timings=timings,
        tool_status="VALIDATION_REQUIRED",
        ranking_status="INACTIVE",
    )
    (output / "run-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf8"
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--ranking-database", type=Path, required=True)
    parser.add_argument("--universe-database", type=Path, required=True)
    parser.add_argument("--cvm-directory", type=Path, default=Path("data/cvm"))
    parser.add_argument("--market-directory", type=Path, default=Path("data/cotahist"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(**vars(args)), indent=2))


if __name__ == "__main__":
    main()
