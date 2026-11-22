"""Project Financial certification from the full suite's single JUnit execution."""

import json
from pathlib import Path

from financial_certification import evaluate, failure_causes
from scoped_financial import certify


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
    (output / "financial-result.json").write_text(
        json.dumps(projected, indent=2) + "\n", encoding="utf-8"
    )
