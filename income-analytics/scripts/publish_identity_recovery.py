"""Append a validated recovery snapshot after backup, then close and read back."""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from income_analytics.infrastructure.magic_formula_universe_repository import (
    MagicFormulaUniverseRepository,
)


def run(output):
    raw = (output / "validated-candidate.json").read_bytes()
    candidate = json.loads(raw)
    report = json.loads((output / "readback-report.json").read_text(encoding="utf8"))
    if (
        report["status"] != "PASS"
        or hashlib.sha256(raw).hexdigest() != report["validated_candidate_sha256"]
        or candidate["identity_recovery_run"]["independent_readback"] != "PASS"
    ):
        raise ValueError("VALIDATED_READBACK_REQUIRED")
    database = Path("data/magic_formula/universe_snapshots.db").resolve()
    repository = MagicFormulaUniverseRepository(database)
    latest = repository.latest()
    if latest["universe_snapshot_id"] != candidate["identity_recovery_run"]["parent_id"]:
        raise ValueError("BASELINE_CHANGED")
    backup = output / "universe-before-publication.db"
    if backup.exists():
        raise ValueError("BACKUP_ALREADY_EXISTS_DO_NOT_OVERWRITE")
    source = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    destination = sqlite3.connect(backup)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    if MagicFormulaUniverseRepository(backup).latest() != latest:
        raise ValueError("BACKUP_READBACK_FAILED")
    repository.save(candidate)
    # save() closes its transaction and connection; read() opens a new connection.
    actual = MagicFormulaUniverseRepository(database).read(candidate["universe_snapshot_id"])
    if actual != candidate:
        raise ValueError("PERSISTED_READBACK_FAILED")
    receipt = {
        "snapshot_id": candidate["universe_snapshot_id"],
        "backup_path": str(backup.resolve()),
        "readback": "PASS",
        "ranking_status": actual["ranking_status"],
        "tool_status": actual["tool_status"],
    }
    (output / "publication.json").write_text(json.dumps(receipt, indent=2), encoding="utf8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
