"""Fail-closed operational gate and dry-run retention. No host execution path."""

import csv
import hashlib
import json
import re
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from delivery import (
    DeliveryError,
    Workspace,
    backup_database,
    database_check,
    require,
    restore_database,
)

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = (
    "operational_readiness_final.md", "operational_inventory.json", "failure_modes_matrix.csv",
    "health_readiness_contract.md", "observability_contract.md", "backup_retention_policy.md",
    "disaster_recovery_report.json", "rpo_rto_measurements.json", "windows_tailscale_checklist.md",
    "firebase_operational_checklist.md", "incident_runbooks.md", "beta_readiness_matrix.csv",
    "operational_gate_validation.json", "operational_hosted_validation.json",
)


def retention_plan(workspace, records, *, now, daily=7, weekly=4, monthly=3):
    """Select validated snapshots only; never delete or activate a real schedule.

    One newest valid copy per UTC day/week/month bucket. A corrupt record fails
    the whole plan instead of implicitly authorizing deletion of that backup.
    """
    require(now.tzinfo is not None, "UTC_CLOCK_REQUIRED")
    require(all(type(n) is int and 1 <= n <= 366 for n in (daily, weekly, monthly)),
            "INVALID_RETENTION")
    validated = []
    for record in records:
        path = workspace.safe(record["path"])
        require(path.is_file(), "BACKUP_MISSING")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"],
                "BACKUP_DIGEST_MISMATCH")
        database_check(workspace, path, record["schema_head"], record["state_signature"])
        timestamp = datetime.fromisoformat(record["created_at"])
        require(timestamp.tzinfo is not None and timestamp <= now, "INVALID_BACKUP_TIME")
        validated.append((timestamp.astimezone(UTC), path.name))
    keep, buckets = set(), [set(), set(), set()]
    for stamp, name in sorted(validated, reverse=True):
        keys = (stamp.date(), stamp.isocalendar()[:2], (stamp.year, stamp.month))
        eligible = (
            stamp >= now - timedelta(days=daily),
            stamp >= now - timedelta(weeks=weekly),
            0 <= (now.year - stamp.year) * 12 + now.month - stamp.month < monthly,
        )
        for index, key in enumerate(keys):
            if (eligible[index] and key not in buckets[index]
                    and len(buckets[index]) < (daily, weekly, monthly)[index]):
                keep.add(name)
                buckets[index].add(key)
    if validated:
        keep.add(max(validated)[1])  # Never discard the only/latest validated restore point.
    return {"mode": "DRY_RUN_ONLY", "keep": sorted(keep),
            "candidates": sorted(name for _, name in validated if name not in keep),
            "bucket_counts": dict(zip(("daily", "weekly", "monthly"), map(len, buckets))),
            "deletion_authorized": False}


def evaluate(details, root=ROOT):
    totals = details.get("totals", {})
    cases = details.get("cases", [])
    if set(totals) != {"passed", "failed", "errors", "skipped"} or any(
        type(value) is not int or value < 0 for value in totals.values()
    ):
        return "OPERATIONAL_NOT_VERIFIED"
    names = [row.get("name", "") for row in cases]
    required = {f"test_failure_exercise[{number:02d}]" for number in range(1, 26)}
    if not required.issubset(names) or len(names) != len(set(names)):
        return "OPERATIONAL_NOT_VERIFIED"
    if any(totals.get(key, 0) for key in ("failed", "errors")):
        return "OPERATIONAL_FAIL"
    if (totals.get("skipped", 0) or totals.get("passed", 0) != len(cases)
            or any(row.get("status") != "passed" for row in cases)):
        return "OPERATIONAL_NOT_VERIFIED"
    directory = root / "docs/engineering/operational-readiness"
    if not all((directory / name).is_file() for name in DOCUMENTS):
        return "OPERATIONAL_BLOCKED"
    if not documentation_valid(root):
        return "OPERATIONAL_BLOCKED"
    return "OPERATIONAL_PASS"


def documentation_valid(root):
    directory = root / "docs/engineering/operational-readiness"
    try:
        inventory = json.loads(
            (directory / "operational_inventory.json").read_text(encoding="utf-8")
        )
        components = inventory["components"]
        if inventory.get("schema") != 1 or len(components) < 18:
            return False
        for component in components:
            if component.get("state") not in {
                "VERIFIED", "PARTIALLY_VERIFIED", "NOT_VERIFIED", "BLOCKED"
            }:
                return False
            if not all(component.get(key) for key in (
                "component", "function", "dependencies", "configuration", "data", "failures",
                "impact", "detection", "recovery", "evidence",
            )):
                return False
            for name in component["evidence"].split(";"):
                path = (root / name.strip()).resolve()
                if not path.is_relative_to(root.resolve()) or not path.exists():
                    return False
        runbooks = (directory / "incident_runbooks.md").read_text(encoding="utf-8")
        if not all(f"INC-{number:02d}" in runbooks for number in range(1, 9)):
            return False
        with (directory / "failure_modes_matrix.csv").open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        if len(rows) != 25 or {row["id"] for row in rows} != {
            f"OP-{number:02d}" for number in range(1, 26)
        }:
            return False
        with (directory / "beta_readiness_matrix.csv").open(encoding="utf-8", newline="") as file:
            beta = list(csv.DictReader(file))
        if not beta or any(row["state"] not in {
            "READY", "NOT_READY", "NOT_VERIFIED", "NOT_APPLICABLE"
        } for row in beta):
            return False
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def require_operational(summary, report, job_status):
    result = dict(summary)
    approved = (
        job_status == "success" and report.get("operational_state") == "OPERATIONAL_PASS"
        and report.get("status") == "PASS" and report.get("exit_code") == 0
        and evaluate(report) == "OPERATIONAL_PASS"
        and report.get("recovery", {}).get("status") == "PASS"
        and report.get("recovery", {}).get("synthetic_rows_lost") == 0
        and report.get("recovery", {}).get("host_rpo_rto_certified") is False
    )
    result["operational_readiness"] = "OPERATIONAL_PASS" if approved else "OPERATIONAL_NOT_VERIFIED"
    result["host"] = "HOST_NOT_VERIFIED"
    result["beta"] = "BETA_NOT_AUTHORIZED"
    result["production"] = "PRODUCTION_NOT_AUTHORIZED"
    if not approved:
        result["engineering_ci"] = "FAIL"
    return result


def run(env, sandbox, output):
    import sys

    import run as runner

    raw = sandbox / "operational-junit.xml"
    started = time.monotonic()
    process = runner.execute([
        sys.executable, "-m", "pytest", "-p", "offline_plugin", "ci/test_operational.py",
        "-ra", "--tb=short", f"--junitxml={raw}", f"--basetemp={sandbox / 'pytest'}",
    ], env, sandbox, "operational")
    details = runner.safe_junit(raw, output / "operational-junit.xml")
    state = evaluate(details)
    recovery = None
    if state == "OPERATIONAL_PASS":
        recovery = recovery_exercise()
    if process.returncode != 0 and state == "OPERATIONAL_PASS":
        state = "OPERATIONAL_FAIL"
    details.update(status="PASS" if state == "OPERATIONAL_PASS" else "FAIL",
                   operational_state=state, host="HOST_NOT_VERIFIED",
                   firebase_cloud="FIREBASE_CLOUD_NOT_VERIFIED",
                   production="PRODUCTION_NOT_AUTHORIZED", beta="BETA_NOT_AUTHORIZED",
                   recovery=recovery,
                   elapsed_seconds=round(time.monotonic() - started, 6))
    return int(state != "OPERATIONAL_PASS"), details


def recovery_exercise():
    workspace = Workspace()
    try:
        source = workspace.file("synthetic-source.db")
        with closing(sqlite3.connect(source)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("CREATE TABLE alembic_version(version_num TEXT)")
            writer.execute("INSERT INTO alembic_version VALUES ('operational-synthetic')")
            writer.execute("CREATE TABLE probe(id INTEGER PRIMARY KEY, value TEXT)")
            writer.executemany("INSERT INTO probe VALUES (?,?)",
                               [(i, "synthetic-only") for i in range(100)])
            writer.commit()
            backup = workspace.file("synthetic-backup.db")
            record = backup_database(workspace, source, backup, "operational-synthetic")
        detection_start = time.monotonic()
        source.rename(workspace.file("preserved-old.db"))
        require(not source.exists(), "SYNTHETIC_FAULT_NOT_DETECTED")
        detection = time.monotonic() - detection_start
        started = time.monotonic()
        restore_database(workspace, backup, source, record)
        recovery_duration = time.monotonic() - started
        validation_start = time.monotonic()
        database_check(workspace, source, "operational-synthetic", record["state_signature"])
        with closing(sqlite3.connect(source)) as reader:
            require(reader.execute("SELECT COUNT(*) FROM probe").fetchone() == (100,),
                    "SYNTHETIC_ROWS_LOST")
        validation = time.monotonic() - validation_start
        return {
            "status": "PASS", "environment": "DISPOSABLE_SYNTHETIC_SQLITE_WAL",
            "backup_seconds": record["duration_seconds"],
            "detection_seconds": round(detection, 6),
            "restore_seconds": round(recovery_duration, 6),
            "validation_seconds": round(validation, 6),
            "observed_recovery_seconds": round(detection + recovery_duration + validation, 6),
            "synthetic_committed_rows": 100, "synthetic_rows_lost": 0,
            "observed_rpo": "ZERO_COMMITTED_SYNTHETIC_ROWS_AT_BACKUP_BOUNDARY",
            "last_valid_backup_age_seconds": round(
                (datetime.now(UTC) - datetime.fromisoformat(record["created_at"])).total_seconds(),
                6,
            ),
            "host_rpo_rto_certified": False, "target_rpo_hours": 24, "target_rto_hours": 2,
            "targets": "PROPOSED_NOT_GUARANTEED", "production_access": False,
        }
    finally:
        workspace.cleanup()


def validate_receipt(document, expected):
    """Hosted collector rejects changed source, old attempt or transport digest."""
    for key in ("checkout_sha", "run_id", "run_attempt", "source_fingerprint",
                "governance_policy_sha256", "artifact_id", "artifact_digest"):
        require(document.get(key) == expected.get(key) and bool(document.get(key)),
                "OPERATIONAL_EVIDENCE_MISMATCH")
    require(re.fullmatch(r"sha256:[a-f0-9]{64}", document["artifact_digest"]) is not None,
            "INVALID_ARTIFACT_DIGEST")
    require(document.get("operational_state") == "OPERATIONAL_PASS", "OPERATIONAL_FAILED")
    return "VERIFIED"


def safe_failure(error):
    # Only stable local enum codes are publishable; never serialize exception payloads.
    return str(error) if isinstance(error, DeliveryError) and re.fullmatch(
        r"[A-Z_]{1,80}", str(error)) else "OPERATIONAL_FAILURE"
