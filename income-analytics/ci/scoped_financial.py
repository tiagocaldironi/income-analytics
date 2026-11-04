"""Review-only scoped certification, without waiving the existing financial gate.

Run isolated feature/dependency tests and retain every historical result. Only an
independent financial decision can approve the proposed CERT_48 non-applicability.
This module deliberately has no approval switch or deployment capability.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import run as legacy
from pipeline_identity import execution_fingerprint

ROOT = Path(__file__).resolve().parents[1]
POLICY = "ci/scoped-financial-policy.json"


def assess(policy, details, trace, historical, root):
    problems = []
    cases = details.get("cases", [])
    nodes = [row["class"].replace(".", "/") + ".py::" + row["name"] for row in cases]
    if not cases or len(nodes) != len(set(nodes)):
        problems.append("INVALID_SCOPED_CASE_INVENTORY")
    actual = {
        state: sum(row.get("status") == state for row in cases)
        for state in ("passed", "failed", "errors", "skipped")
    }
    if actual != details.get("totals") or sum(actual.values()) != len(cases):
        problems.append("INVALID_SCOPED_TOTALS")
    if any(actual[state] for state in ("failed", "errors", "skipped")):
        problems.append("SCOPED_FAILURE_ERROR_OR_SKIP")
    for target in policy["test_targets"]:
        prefix = target.rstrip("/")
        if not any(node.startswith((prefix + "::", prefix + "/")) for node in nodes):
            problems.append("SCOPED_TEST_TARGET_NOT_EXECUTED:" + target)
    calls = trace.get("calls", [])
    if not calls or calls != sorted(set(calls)):
        problems.append("INVALID_DEPENDENCY_TRACE")
    for module in policy["required_executed_modules"]:
        if not any(call.startswith(module + ":") for call in calls):
            problems.append("DEPENDENCY_NOT_EXERCISED:" + module)
    for entrypoint in policy["required_executed_functions"]:
        if entrypoint not in calls:
            problems.append("ENTRYPOINT_NOT_EXERCISED:" + entrypoint)
    frozen_calls = [
        call for call in calls
        if call.split(":", 1)[0] in policy["cert48_modules"]
    ]
    if frozen_calls:
        problems.append("CERT48_DEPENDENCY_EXECUTED")
    immutable = json.loads((root / policy["immutable_inventory"]).read_text(encoding="utf-8"))
    if len(immutable["files"]) != 41:
        problems.append("IMMUTABLE_INVENTORY_INCOMPLETE")
    for name, expected in immutable["files"].items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            problems.append("IMMUTABLE_BYTES_CHANGED:" + name)
    exceptions = policy["historical_out_of_scope_proposal"]
    # Every exception must have provenance and a backlog destination. A status
    # change, missing test, duplicate identity or unknown failure blocks review.
    history = historical.get("cases", [])
    history_nodes = [row["class"].replace(".", "/") + ".py::" + row["name"] for row in history]
    observed = dict(zip(history_nodes, (row["status"] for row in history), strict=True))
    if len(history_nodes) != len(observed):
        problems.append("DUPLICATE_HISTORICAL_IDENTITY")
    excluded = []
    for node, exception in exceptions.items():
        valid = (
            (observed.get(node) == "passed" or (
                observed.get(node) == exception["baseline_status"]
                and historical.get("failure_causes", {}).get(node) == exception["cause"]
            ))
            and exception["issue"] in {57, 58}
            and exception.get("baseline_sha") == policy["historical_baseline_sha"]
        )
        if not valid:
            problems.append("HISTORICAL_CLASSIFICATION_CHANGED:" + node)
        excluded.append({"nodeid": node, "observed": observed.get(node), **exception})
    for node, state in observed.items():
        if state not in {"passed", "failed", "errors", "skipped"} or (
            state in {"failed", "errors", "skipped"} and node not in exceptions
        ):
            problems.append("UNREVIEWED_FINANCIAL_RESULT:" + node)
    return {
        "schema": 1,
        "scope": "PR69_INCLUDING_PR62",
        "technical_state": "PASS" if not problems else "BLOCKED",
        "technical_blockers": sorted(set(problems)),
        "scoped_totals": actual,
        "dependency_calls": calls,
        "import_definitions": trace.get("definitions", []),
        "cert48_executed_calls": frozen_calls,
        "immutable_files": len(immutable["files"]),
        "historical_out_of_scope_proposal": excluded,
        "historical_tests_visible": True,
        "historical_report_totals": historical.get("totals", {}),
        "historical_checkout_sha": historical.get("checkout_sha", "IN_PROCESS_SAME_CHECKOUT"),
        "cert48_applicability": "PROPOSED_NOT_APPLICABLE_REQUIRES_INDEPENDENT_APPROVAL",
        "financial_approval": "PENDING_INDEPENDENT_REVIEW",
        "financial_release_decision": "NO_GO",
        "activation": "REVIEW_ONLY_EXISTING_GATES_UNCHANGED",
        "deployment_authorized": False,
    }


def certify(historical, output):
    fingerprint = execution_fingerprint(ROOT)
    policy = json.loads((ROOT / POLICY).read_text(encoding="utf-8"))
    sandbox = Path(tempfile.mkdtemp(prefix="income-scoped-certification-")).resolve()
    env = legacy.isolated_environment(sandbox)
    trace_path = sandbox / "trace.json"
    env["CI_SCOPED_FINANCIAL_TRACE"] = str(trace_path)
    raw = sandbox / "scoped.xml"
    result = legacy.execute(
        [sys.executable, "-m", "pytest", "-p", "offline_plugin", "-p",
         "scoped_financial_trace", *policy["test_targets"], "-q", "--tb=short",
         f"--basetemp={sandbox / 'pytest'}", f"--junitxml={raw}"],
        env, sandbox, "scoped",
    )
    output.mkdir(parents=True, exist_ok=True)
    details = legacy.safe_junit(raw, output / "scoped-junit.xml")
    trace = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.exists() else {}
    report = assess(policy, details, trace, historical, ROOT)
    report["source_fingerprint"] = fingerprint
    if execution_fingerprint(ROOT) != fingerprint:
        report["technical_state"] = "BLOCKED"
        report["technical_blockers"].append("SOURCE_CHANGED_DURING_CERTIFICATION")
    if result.returncode != 0:
        report["technical_state"] = "BLOCKED"
        report["technical_blockers"].append("SCOPED_PYTEST_NONZERO")
    report["checkout_sha"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    report["policy_sha256"] = hashlib.sha256((ROOT / POLICY).read_bytes()).hexdigest()
    report["cases"] = details["cases"]
    (output / "scoped-financial.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    historical = json.loads(args.historical_report.read_text(encoding="utf-8"))
    report = certify(historical, args.output)
    print(json.dumps({key: report[key] for key in (
        "technical_state", "technical_blockers", "scoped_totals", "financial_release_decision"
    )}, indent=2))
    return int(report["technical_state"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
