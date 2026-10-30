"""Audited occurrence reconciliation and fail-closed promotion of clean checks."""

import hashlib
import importlib.metadata
import json
from collections import Counter
from pathlib import Path

FIELDS = ("tool", "file", "line", "column", "code", "message")


def key(finding: dict) -> str:
    return json.dumps({name: finding.get(name) for name in FIELDS}, sort_keys=True)


def ruff_exception_findings(root: Path, policy: dict) -> list[dict]:
    """Only exact style occurrences in byte-immutable historical migrations qualify."""
    if policy["ruff_version"] != importlib.metadata.version("ruff"):
        raise ValueError("RUFF_EXCEPTION_TOOL_VERSION_MISMATCH")
    if (
        hashlib.sha256((root / "pyproject.toml").read_bytes()).hexdigest()
        != policy["configuration_sha256"]
    ):
        raise ValueError("RUFF_EXCEPTION_CONFIGURATION_CHANGED")
    approved = []
    files = set()
    for row in policy["occurrences"]:
        finding = row["finding"]
        file = finding["file"]
        if (
            finding["tool"] != "ruff"
            or finding["code"] not in {"E501", "E701", "E702", "I001"}
            or not file.startswith("alembic/versions/")
            or not file.endswith(".py")
            or not row.get("reason")
        ):
            raise ValueError("RUFF_EXCEPTION_OUTSIDE_IMMUTABLE_STYLE_SCOPE")
        path = (root / file).resolve()
        if not path.is_relative_to((root / "alembic/versions").resolve()):
            raise ValueError("RUFF_EXCEPTION_PATH_ESCAPE")
        if hashlib.sha256(path.read_bytes()).hexdigest() != policy["source_sha256"][file]:
            raise ValueError("RUFF_EXCEPTION_SOURCE_BYTES_CHANGED")
        files.add(file)
        approved.append(finding)
    if files != set(policy["source_sha256"]) or len(set(map(key, approved))) != len(approved):
        raise ValueError("RUFF_EXCEPTION_INVENTORY_MISMATCH")
    return approved


def classify_ruff(code: int, findings: list[dict], approved: list[dict]) -> tuple[int, dict]:
    """Keep raw findings/exit visible; never waive a new rule, location or duplicate."""
    if code not in (0, 1) or type(code) is not int or bool(findings) != (code == 1):
        raise ValueError("RUFF_RAW_RESULT_INCONSISTENT")
    observed = Counter(map(key, findings))
    allowed = Counter(map(key, approved))
    extra, missing = observed - allowed, allowed - observed
    passed = not extra and not missing
    return (0 if passed else 1), {
        "status": "PASS" if passed else "FAIL",
        "contract": "FULL_SCOPE_ZERO_UNJUSTIFIED; EXACT_IMMUTABLE_MIGRATION_STYLE_EXCEPTIONS",
        "raw_tool_exit_code": code,
        "findings": findings,
        "justified_findings": [json.loads(item) for item in (observed & allowed).elements()],
        "unjustified_findings": [json.loads(item) for item in extra.elements()],
        "missing_approved_observations": [json.loads(item) for item in missing.elements()],
    }


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


def require_clean_diagnostics(summary: dict, reports: dict, approved=()) -> dict:
    """Only Ruff has zero unreviewed findings; mypy/full remain unpromoted."""
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
        and isinstance(report.get("findings"), list)
        and Counter(map(key, report["findings"])) == Counter(map(key, approved))
        and Counter(map(key, report.get("justified_findings", []))) == Counter(map(key, approved))
        and report.get("unjustified_findings") == []
        and report.get("missing_approved_observations") == []
        and type(report.get("raw_tool_exit_code")) is int
        and report["raw_tool_exit_code"] == (1 if approved else 0)
        and all(
            report.get(field) == reference.get(field) and report.get(field) for field in identity
        )
    )
    result["promoted_diagnostics"] = {"ruff": "PASS" if passed else "FAIL"}
    result["unpromoted_diagnostics"] = ["mypy", "python"]
    if not passed:
        result["engineering_ci"] = "FAIL"
    return result
