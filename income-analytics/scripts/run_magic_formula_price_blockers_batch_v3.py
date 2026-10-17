"""Run a deterministic, non-persisting price-blocker recovery batch."""

import argparse
import hashlib
import json
from pathlib import Path

from income_analytics.application.magic_formula_price_blocker_batch import run_batch
from income_analytics.infrastructure.historical_price_audit_source import scan_archive
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)


def logical_digest(candidate):
    document = dict(candidate)
    document.pop("universe_snapshot_id", None)
    run = dict(document.get("identity_recovery_run", {}))
    run.pop("dry_run", None)
    document["identity_recovery_run"] = run
    raw = json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def run(before_directory: Path, evidence_directory: Path, output: Path):
    before = json.loads((before_directory / "before-inventory.json").read_text(encoding="utf-8"))
    snapshot_copy = json.loads(
        (before_directory / "snapshot-before.json").read_text(encoding="utf-8")
    )
    repository = MagicFormulaUniverseRepository(Path("data/magic_formula/universe_snapshots.db"))
    current = repository.latest()
    if current["universe_snapshot_id"] != before["snapshot_id"]:
        raise ValueError("BEFORE_SNAPSHOT_IS_NOT_CURRENT_LATEST")
    if snapshot_copy["universe_snapshot_id"] != before["snapshot_id"]:
        raise ValueError("BEFORE_ARTIFACT_MISMATCH")
    manifest = json.loads((evidence_directory / "manifest.json").read_text(encoding="utf-8"))
    directory_responses = {r["cvm_code"]: r for r in manifest["responses"]}
    tickers = set()
    for blocker in before["blockers"]:
        for security in blocker["securities"]:
            if security.get("ticker"):
                tickers.add(security["ticker"])
        response = directory_responses.get(blocker["cvm_code"])
        if not response:
            continue
        raw_path = evidence_directory / response["file"]
        if hashlib.sha256(raw_path.read_bytes()).hexdigest() != response["sha256"]:
            raise ValueError("B3_EVIDENCE_HASH_MISMATCH")
        current_security_data = json.loads(raw_path.read_text(encoding="utf-8"))
        for security in current_security_data.get("otherCodes") or []:
            if security.get("code"):
                tickers.add(security["code"])
        if current_security_data.get("code"):
            tickers.add(current_security_data["code"])
    archive = Path("data/cotahist") / f"COTAHIST_A{current['reference_date'][:4]}.ZIP"
    price_index, price_manifest = scan_archive(archive, tickers)
    candidate = run_batch(snapshot_copy, evidence_directory, price_index, price_manifest)
    statuses = candidate["identity_recovery_run"]["terminal_status_counts"]
    if len(candidate["identity_recovery_run"]["case_results"]) != before["price_only_blockers"]:
        raise AssertionError("BLOCKER_COUNT_CHANGED_DURING_DRY_RUN")
    output.mkdir(parents=True, exist_ok=True)
    (output / "candidate.json").write_text(
        json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = {
        "dry_run": True,
        "persisted": False,
        "before_snapshot_id": before["snapshot_id"],
        "candidate_snapshot_id": candidate["universe_snapshot_id"],
        "blockers_processed": len(candidate["identity_recovery_run"]["case_results"]),
        "terminal_status_counts": statuses,
        "after_coverage": candidate["coverage"],
        "before_gap_analysis": candidate["identity_recovery_run"]["before_gap_analysis"],
        "after_gap_analysis": candidate["identity_recovery_run"]["after_gap_analysis"],
        "logical_digest": logical_digest(candidate),
        "cotahist_manifest": price_manifest,
    }
    (output / "dry-run-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for result in candidate["identity_recovery_run"]["case_results"]:
        print(
            json.dumps(
                {
                    k: result[k]
                    for k in (
                        "cvm_code",
                        "company",
                        "terminal_status",
                        "confidence",
                        "reason",
                        "selected_identity",
                        "price_lookup_result",
                    )
                },
                ensure_ascii=False,
            )
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    run(arguments.before, arguments.evidence, arguments.output)
