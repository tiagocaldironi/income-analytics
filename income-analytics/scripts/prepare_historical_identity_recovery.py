"""Build an offline recovery proposal. This command never writes the universe DB."""

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from income_analytics.application.historical_price import gap_analysis
from income_analytics.application.historical_security_identity import (
    EXCHANGE_DIRECTORY_POLICY,
    recover_price,
    recover_price_from_exchange_identity,
)
from income_analytics.application.magic_formula_universe import coverage
from income_analytics.infrastructure.historical_price_audit_source import scan_archive
from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)


def run(evidence_directory, output):
    repository = MagicFormulaUniverseRepository(Path("data/magic_formula/universe_snapshots.db"))
    baseline = repository.latest()
    manifest = json.loads((evidence_directory / "manifest.json").read_text(encoding="utf8"))
    if manifest["baseline_snapshot_id"] != baseline["universe_snapshot_id"]:
        raise ValueError("BASELINE_CHANGED")
    proofs = []
    directory_responses = {response["file"]: response for response in manifest["responses"]}
    for path in sorted(evidence_directory.glob("*.identity.json")):
        proof = json.loads(path.read_text(encoding="utf8"))
        source = evidence_directory / proof["source_file"]
        actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual_hash != proof["source_sha256"]:
            raise ValueError("IDENTITY_SOURCE_HASH_MISMATCH")
        if proof.get("schema_version") == EXCHANGE_DIRECTORY_POLICY:
            acquisition = directory_responses.get(proof["source_file"])
            if not acquisition or acquisition["sha256"] != actual_hash:
                raise ValueError("DIRECTORY_SOURCE_HASH_MISMATCH")
        else:
            acquisition_path = source.with_suffix(".manifest.json")
            acquisition = json.loads(acquisition_path.read_text(encoding="utf8"))
            if acquisition["sha256"] != actual_hash:
                raise ValueError("OFFER_SOURCE_HASH_MISMATCH")
        proofs.append(dict(proof, acquisition=acquisition,
                           extraction_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    index, archive_manifest = scan_archive(
        Path("data/cotahist") / f"COTAHIST_A{baseline['reference_date'][:4]}.ZIP",
        {proof["ticker"] for proof in proofs},
    )
    candidate = deepcopy(baseline)
    recovered, rejected = [], []
    for position, issuer in enumerate(baseline["issuers"]):
        issuer_proofs = [proof for proof in proofs if proof["cnpj"] == issuer["cnpj"]]
        if not issuer_proofs:
            continue
        if len(issuer_proofs) != 1:
            raise ValueError("AMBIGUOUS_IDENTITY_PROOF")
        proof = issuer_proofs[0]
        response = next(r for r in manifest["responses"] if r["issuer_id"] == issuer["issuer_id"])
        raw = (evidence_directory / response["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != response["sha256"]:
            raise ValueError("DIRECTORY_SOURCE_HASH_MISMATCH")
        current = json.loads(raw)
        try:
            resolver = (recover_price_from_exchange_identity
                        if proof.get("schema_version") == EXCHANGE_DIRECTORY_POLICY
                        else recover_price)
            proposal = resolver(
                issuer, proof, current, index[proof["ticker"]], baseline["reference_date"]
            )
        except ValueError as error:
            rejected.append({"issuer_id": issuer["issuer_id"], "reason": str(error)})
            continue
        proposal["securities"][0]["identity_resolution"]["directory_acquisition"] = response
        candidate["issuers"][position] = proposal
        recovered.append(issuer["issuer_id"])
    candidate.update(universe_snapshot_id=str(uuid4()), created_at=datetime.now(UTC).isoformat())
    candidate["coverage"] = coverage(candidate["issuers"])
    # The old audit is attached to its parent snapshot, never relabel it as a new run.
    candidate.pop("price_resolution_run", None)
    candidate["identity_recovery_run"] = {
        "parent_id": baseline["universe_snapshot_id"],
        "recovered_issuers": recovered,
        "rejected": rejected,
        "source_manifest": archive_manifest,
        "before_gap_analysis": gap_analysis(baseline["issuers"]),
        "after_gap_analysis": gap_analysis(candidate["issuers"]),
        "independent_readback": "REQUIRED",
    }
    output.mkdir(parents=True, exist_ok=True)
    for filename, value in (
        ("before.json", baseline),
        ("candidate.json", candidate),
        ("recovery-raw-index.json", index),
    ):
        (output / filename).write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf8"
        )
    print(json.dumps(candidate["identity_recovery_run"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.evidence_directory, args.output)
