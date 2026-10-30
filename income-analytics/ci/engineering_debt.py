"""Audited occurrence reconciliation and fail-closed promotion of clean checks."""

import hashlib
import json
from collections import Counter
from pathlib import Path

FIELDS = ("tool", "file", "line", "column", "code", "message")


def key(finding: dict) -> str:
    return json.dumps({name: finding.get(name) for name in FIELDS}, sort_keys=True)


def reconciled_findings(original: list[dict], ledger: dict, root: Path) -> list[dict]:
    rows = ledger["occurrences"]
    if Counter(key(row["before"]) for row in rows) != Counter(map(key, original)):
        raise ValueError("DEBT_LEDGER_ORIGINAL_OCCURRENCES_MISMATCH")
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("DEBT_LEDGER_DUPLICATE_ID")
    for file, digest in ledger["reviewed_source_sha256"].items():
        path = (root / file).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("DEBT_LEDGER_PATH_ESCAPE")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("DEBT_LEDGER_SOURCE_REVIEW_REQUIRED")
    remaining = []
    for row in rows:
        before, after = row["before"], row["after"]
        if not row.get("evidence"):
            raise ValueError("DEBT_LEDGER_MISSING_EVIDENCE")
        if after is None:
            if row["status"] != "RESOLVED":
                raise ValueError("DEBT_LEDGER_INVALID_RESOLUTION")
        else:
            if row["status"] != "OPEN" or any(
                before[name] != after[name] for name in ("tool", "file", "code", "message")
            ):
                raise ValueError("DEBT_LEDGER_UNREVIEWED_DIAGNOSTIC")
            remaining.append(after)
    return remaining


def require_clean_diagnostics(summary: dict, reports: dict) -> dict:
    """Only Ruff has reached zero; mypy/full remain explicitly unpromoted."""
    result = dict(summary)
    report = reports.get("ruff", {})
    reference = reports.get("engineering", {})
    identity = (
        "checkout_sha",
        "source_fingerprint",
        "governance_policy_sha256",
        "fingerprint_version",
        "run_id",
        "run_attempt",
    )
    passed = (
        report.get("check") == "ruff"
        and report.get("status") == "PASS"
        and report.get("exit_code") == 0
        and type(report.get("exit_code")) is int
        and report.get("findings") == []
        and all(
            report.get(field) == reference.get(field) and report.get(field) for field in identity
        )
    )
    result["promoted_diagnostics"] = {"ruff": "PASS" if passed else "FAIL"}
    result["unpromoted_diagnostics"] = ["mypy", "python"]
    if not passed:
        result["engineering_ci"] = "FAIL"
    return result
