"""Project Financial certification from the full suite's single JUnit execution."""

import json
import os
import subprocess
from pathlib import Path

from financial_certification import evaluate, failure_causes
from pipeline_identity import FINGERPRINT_VERSION, execution_fingerprint, governance_policy_identity
from scoped_financial import certify


def execution_identity(root: Path) -> dict:
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip()
    return {
        "checkout_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "source_fingerprint": execution_fingerprint(root),
        "fingerprint_version": FINGERPRINT_VERSION,
        "governance_policy_sha256": governance_policy_identity(root),
        "pr_head_sha": os.getenv("CI_PR_HEAD_SHA", ""),
        "run_id": os.getenv("GITHUB_RUN_ID", "LOCAL"),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", "1"),
        "event_sha": os.getenv("GITHUB_SHA", ""),
        "worktree_dirty": bool(dirty),
    }


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
    projected.update(execution_identity(root))
    projected["exit_code"] = int(projected["financial_state"] != "FINANCIAL_PASS")
    (output / "financial-result.json").write_text(
        json.dumps(projected, indent=2) + "\n", encoding="utf-8"
    )
