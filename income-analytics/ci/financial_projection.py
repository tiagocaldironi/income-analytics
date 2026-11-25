"""Project Financial certification from the full suite's single JUnit execution."""

import json
from pathlib import Path

from financial_certification import evaluate, failure_causes
from scoped_financial import certify


def bind_to_python(projection: dict, python_report: dict) -> dict:
    """Bind a financial projection to the identity emitted by the full Python run."""
    fields = (
        "checkout_sha",
        "source_fingerprint",
        "fingerprint_version",
        "governance_policy_sha256",
        "pr_head_sha",
        "run_id",
        "run_attempt",
        "event_sha",
        "worktree_dirty",
    )
    if python_report.get("check") != "python" or projection.get("check") != "financial":
        raise ValueError("FINANCIAL_PROJECTION_REPORT_INVALID")
    if any(field not in python_report for field in fields):
        raise ValueError("PYTHON_REPORT_IDENTITY_MISSING")
    if python_report.get("worktree_dirty") is not False:
        raise ValueError("PYTHON_REPORT_WORKTREE_DIRTY")
    if any(
        field in projection and projection[field] != python_report[field]
        for field in fields
    ):
        raise ValueError("FINANCIAL_PROJECTION_IDENTITY_MISMATCH")
    projection.update({field: python_report[field] for field in fields})
    if any(projection.get(field) != python_report.get(field) for field in fields):
        raise ValueError("FINANCIAL_PROJECTION_IDENTITY_MISMATCH")
    scoped = projection.get("scoped_release_assessment", {})
    state = projection.get("financial_state")
    if (
        projection.get("worktree_dirty") is not False
        or scoped.get("checkout_sha") != projection.get("checkout_sha")
        or scoped.get("source_fingerprint") != projection.get("source_fingerprint")
        or state
        not in {"FINANCIAL_PASS", "FINANCIAL_FAIL", "FINANCIAL_BLOCKED", "FINANCIAL_NOT_VERIFIED"}
        or projection.get("exit_code") != int(state != "FINANCIAL_PASS")
    ):
        raise ValueError("FINANCIAL_PROJECTION_INVALID")
    return projection


def write_projection(root: Path, entries: list[dict], details: dict, raw: Path, output: Path):
    financial_nodeids = {entry["nodeid"] for entry in entries if entry["financial"]}
    cases = [
        case
        for case in details["cases"]
        if case["class"].replace(".", "/") + ".py::" + case["name"] in financial_nodeids
    ]
    projected = {
        "cases": cases,
        "totals": {
            key: sum(case["status"] == key for case in cases)
            for key in ("passed", "failed", "errors", "skipped")
        },
        "failure_causes": {
            node: cause
            for node, cause in failure_causes(raw).items()
            if node in financial_nodeids
        },
    }
    projected.update(evaluate(root, projected))
    projected["status"] = (
        "PASS"
        if projected["financial_state"] == "FINANCIAL_PASS"
        else ("BLOCKED" if projected["financial_state"] == "FINANCIAL_BLOCKED" else "FAIL")
    )
    projected["scoped_release_assessment"] = certify(projected, output / "financial")
    projected["check"] = "financial"
    projected["exit_code"] = int(projected["financial_state"] != "FINANCIAL_PASS")
    financial_output = output.parent / "financial" / "result.json"
    financial_output.parent.mkdir(parents=True, exist_ok=True)
    financial_output.write_text(
        json.dumps(projected, indent=2) + "\n", encoding="utf-8"
    )
