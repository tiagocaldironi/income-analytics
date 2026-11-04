"""Scoped technical promotion only. No merge, deployment or global certification."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from delivery_pipeline import Github, delivery_decision
from gate_policy import summarize_reports
from operational import require_operational
from pipeline_identity import execution_fingerprint, governance_policy_identity
from scoped_financial import assess

ROOT = Path(__file__).resolve().parents[1]
APPROVAL = "ci/scoped-promotion-approval.json"
PROTECTED = (
    "ci/diagnostic_relocations.py",
    "ci/diagnostic-relocations-79.json",
    "ci/test_diagnostic_relocations.py",
    "src/",
    "alembic/",
    "tests/application/",
    "tests/api/",
    "tests/unit/",
    "tests/acceptance/",
    "tests/infrastructure/",
    "tests/fixtures/",
    "docs/engineering/scoped-financial-certification/",
    "pyproject.toml",
    "alembic.ini",
    "ci/requirements-windows-py314.lock",
    "ci/runtime-windows-py314.lock",
    "ci/scoped_financial.py",
    "ci/scoped_financial_trace.py",
    "ci/scoped-financial-policy.json",
    "ci/financial_certification.py",
    "ci/financial_certification_policy.json",
    "ci/gate_plugin.py",
    "ci/offline_plugin.py",
    "ci/run.py",
    "ci/test-groups.json",
    "ci/governance.py",
    "ci/delivery.py",
    "ci/delivery_stage.py",
    "ci/delivery_pipeline.py",
    "ci/typing-baseline-acceptance.json",
    "docs/engineering/release-policy-65/",
    "docs/engineering/engineering-debt-closure/quality_ledger.json",
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def surface(root, commit):
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("INVALID_APPROVAL_COMMIT")
    data = subprocess.check_output(
        [
            "git",
            "ls-tree",
            "-rz",
            "--full-tree",
            commit,
            "--",
            *("income-analytics/" + path for path in PROTECTED),
        ],
        cwd=root,
    )
    records = []
    for row in data.decode("utf-8").split("\0"):
        if row:
            metadata, name = row.split("\t", 1)
            mode, kind, oid = metadata.split()
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise ValueError("UNSUPPORTED_CERTIFIED_SURFACE")
            records.append((name, mode, oid))
    if not records:
        raise ValueError("EMPTY_CERTIFIED_SURFACE")
    return digest(sorted(records))


def valid_owner(record, comment, approved_surface, candidate_surface):
    return (
        record.get("state") == "OWNER_APPROVED"
        and record.get("owner") == "tiagocaldironi"
        and comment.get("user", {}).get("login") == record["owner"]
        and comment.get("id") == record.get("comment_id")
        and comment.get("html_url") == record.get("comment_url")
        and hashlib.sha256(comment.get("body", "").encode()).hexdigest()
        == record.get("comment_body_sha256")
        and "OWNER_APPROVED" in comment.get("body", "")
        and record.get("approved_sha", "INVALID") in comment.get("body", "")
        and approved_surface == candidate_surface == record.get("certified_surface_sha256")
        and record.get("merge_authorized") is False
        and record.get("production_deploy_authorized") is False
    )


def inventory(report):
    cases = report.get("cases", [])
    nodes = [row["class"] + "::" + row["name"] for row in cases]
    totals = {
        key: sum(row.get("status") == key for row in cases)
        for key in ("passed", "failed", "errors", "skipped")
    }
    supplied = report.get("totals", {})
    if set(supplied) != set(totals) or any(
        type(value) is not int or value < 0 for value in supplied.values()
    ):
        raise ValueError("INVALID_TEST_TOTALS")
    if (
        not cases
        or len(nodes) != len(set(nodes))
        or totals != report.get("totals")
        or sum(totals.values()) != len(cases)
    ):
        raise ValueError("INVALID_TEST_INVENTORY")
    return dict(zip(nodes, (row["status"] for row in cases), strict=True))


def no_test_regressions(before, after):
    old, new = inventory(before), inventory(after)
    return (
        old.keys() <= new.keys()
        and all(new[node] in {state, "passed"} for node, state in old.items())
        and all(new[node] == "passed" for node in new.keys() - old.keys())
    )


def evaluate(root, reports, security, staging, gate, comment, record, identity, surfaces):
    blockers = []
    states = {
        key: "BLOCKED"
        for key in ("ENGINEERING", "SECURITY", "FINANCIAL_SCOPED", "HISTORICAL_DEBT", "RELEASE")
    }
    expected = (
        identity["checkout_sha"],
        identity["source_fingerprint"],
        identity["governance_policy_sha256"],
    )

    def bound(row):
        return (
            tuple(
                row.get(k)
                for k in ("checkout_sha", "source_fingerprint", "governance_policy_sha256")
            )
            == expected
        )

    if not all(bound(row) for row in [*reports.values(), security]):
        blockers.append("EVIDENCE_IDENTITY_MISMATCH")
    for row in reports.values():
        if (
            (row.get("check") != "build" and str(row.get("run_id")) != identity["run_id"])
            or row.get("worktree_dirty") is not False
            or row.get("pr_head_sha") != identity["pr_head_sha"]
        ):
            blockers.append("EVIDENCE_RUN_OR_HEAD_MISMATCH")
        if type(row.get("exit_code")) is not int or row["exit_code"] not in {0, 1}:
            blockers.append("INVALID_CHECK_EXIT_CODE")
    summary = summarize_reports(reports)
    summary = require_operational(summary, reports.get("operational", {}), "success")
    if (
        summary["engineering_ci"] != "PASS"
        or gate.get("engineering_ci") != "PASS"
        or gate.get("consistent_identity") is not True
        or gate.get("promoted_diagnostics", {}).get("ruff") != "PASS"
    ):
        blockers.append("ENGINEERING_NOT_APPROVED")
    else:
        states["ENGINEERING"] = "PASS"
    controls = (
        "source_policy",
        "gitleaks",
        "security_tests",
        "findings_policy",
        "sast",
        "secret_scanning",
        "dependencies",
    )
    empty_findings = (
        ("gitleaks", "untriaged"),
        ("sast", "untriaged"),
        ("secret_scanning", "untriaged"),
        ("dependencies", "alerts"),
        ("source_policy", "forbidden_files"),
        ("findings_policy", "high_critical_unresolved"),
    )
    tests = security.get("security_tests", {})
    verified_security_tests = inventory(tests)
    if (
        security.get("status") != "PASS"
        or any(security.get(k, {}).get("status") != "PASS" for k in controls)
        or security.get("artifact_sha256") != reports["build"].get("artifact_sha256")
        or security.get("gitleaks", {}).get("negative_fixture") != "REJECTED"
        or gate.get("security_baseline") != "PASS"
        or any(security.get(group, {}).get(key) != [] for group, key in empty_findings)
        or any(state != "passed" for state in verified_security_tests.values())
    ):
        blockers.append("SECURITY_NOT_APPROVED")
    else:
        states["SECURITY"] = "PASS"
    financial = reports["financial"]
    scoped = financial.get("scoped_release_assessment", {})
    policy = json.loads((root / "ci/scoped-financial-policy.json").read_text(encoding="utf-8"))
    recomputed = assess(
        policy,
        {"cases": scoped.get("cases", []), "totals": scoped.get("scoped_totals")},
        {"calls": scoped.get("dependency_calls", [])},
        financial,
        root,
    )
    if (
        recomputed["technical_state"] != "PASS"
        or scoped.get("technical_state") != "PASS"
        or scoped.get("checkout_sha") != identity["checkout_sha"]
        or scoped.get("source_fingerprint") != identity["source_fingerprint"]
        or scoped.get("policy_sha256")
        != hashlib.sha256((root / "ci/scoped-financial-policy.json").read_bytes()).hexdigest()
    ):
        blockers.append("SCOPED_CERTIFICATION_NOT_VERIFIED")
    elif not valid_owner(record, comment, *surfaces):
        blockers.append("OWNER_APPROVAL_NOT_BOUND_TO_CERTIFIED_SURFACE")
    else:
        states["FINANCIAL_SCOPED"] = "PASS"
    baseline = json.loads(
        (root / "docs/engineering/release-policy-65/candidate_python.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        not no_test_regressions(baseline, reports["python"])
        or recomputed["technical_state"] != "PASS"
        or reports["quality"].get("accepted_typing_nonregression", {}).get("status") != "PASS"
        or reports["quality"].get("accepted_typing_nonregression", {}).get("added") != []
    ):
        blockers.append("NEW_REGRESSION_OR_UNCLASSIFIED_HISTORICAL_DEBT")
    else:
        states["HISTORICAL_DEBT"] = "KNOWN_DEBT_VISIBLE"
    candidate = staging.get("candidate", {})
    if (
        staging.get("workflow_identity", {}).get("delivery_run_id") != identity["run_id"]
        or staging.get("workflow_identity", {}).get("controller_checkout_sha")
        != identity["checkout_sha"]
        or candidate.get("source_commit") != identity["checkout_sha"]
        or candidate.get("source_fingerprint") != identity["source_fingerprint"]
        or candidate.get("governance_policy_identity") != expected[2]
        or str(candidate.get("build_run_id")) != identity["run_id"]
        or candidate.get("package_sha256") != reports["build"].get("artifact_sha256")
    ):
        blockers.append("STAGING_IDENTITY_MISMATCH")
    try:
        delivery_decision(candidate, staging, "premerge")
    except ValueError, KeyError:
        blockers.append("STAGING_OR_ROLLBACK_NOT_VERIFIED")
    if (
        identity.get("engineering_job") != "success"
        or identity.get("security_job") != "success"
        or identity.get("staging_job") != "success"
    ):
        blockers.append("REQUIRED_JOB_NOT_SUCCESSFUL")
    if not blockers:
        states["RELEASE"] = "GO"
    return {
        "schema": 1,
        **identity,
        "gates": states,
        "decision": "NO_GO" if blockers else "GO",
        "blockers": sorted(set(blockers)),
        "eligibility_scope": "CERTIFIED_SCOPED_TECHNICAL_PROMOTION_ONLY",
        "owner_approval": {
            **record,
            "revalidated_candidate_sha": identity["checkout_sha"],
            "revalidated_pr_head_sha": identity["pr_head_sha"],
        },
        "historical_evidence": recomputed["historical_out_of_scope_proposal"],
        "historical_test_totals": reports["python"].get("totals"),
        "scoped_test_totals": scoped.get("scoped_totals"),
        "linked_issues": [57, 58, 59, 60, 65, 76, 77, 80],
        "merge_authorized": False,
        "deployment_authorized": False,
        "production_status": "PRODUCTION_NOT_AUTHORIZED",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    args = parser.parse_args()
    output = ROOT / "ci-reports/promotion"
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "decision": "NO_GO",
        "blockers": ["INCOMPLETE_EVIDENCE"],
        "gates": {
            name: "BLOCKED"
            for name in (
                "ENGINEERING",
                "SECURITY",
                "FINANCIAL_SCOPED",
                "HISTORICAL_DEBT",
                "RELEASE",
            )
        },
        "merge_authorized": False,
        "deployment_authorized": False,
    }
    try:
        reports = {}
        security = None
        for path in args.inputs.rglob("result.json"):
            row = json.loads(path.read_text(encoding="utf-8"))
            if row.get("check"):
                if row["check"] in reports:
                    raise ValueError("DUPLICATE_REPORT")
                reports[row["check"]] = row
            elif "security_tests" in row:
                if security is not None:
                    raise ValueError("DUPLICATE_SECURITY_REPORT")
                security = row
        if (
            set(reports)
            != {
                "runtime",
                "engineering",
                "financial",
                "python",
                "node",
                "quality",
                "build",
                "ruff",
                "mypy",
                "operational",
            }
            or security is None
        ):
            raise ValueError("MISSING_OR_UNKNOWN_REPORT")

        def one(name):
            paths = list(args.inputs.rglob(name))
            if len(paths) != 1:
                raise ValueError("MISSING_OR_DUPLICATE_EVIDENCE")
            return json.loads(paths[0].read_text(encoding="utf-8"))

        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        if (
            sha != os.environ["GITHUB_SHA"]
            or subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            ).strip()
        ):
            raise ValueError("DIRTY_OR_WRONG_CANDIDATE")
        record = json.loads((ROOT / APPROVAL).read_text(encoding="utf-8"))
        if (
            os.environ.get("RELEASE_PR_NUMBER") != str(record.get("pr_number", 69))
            or os.environ.get("GITHUB_REPOSITORY") != "tiagocaldironi/income-analytics"
        ):
            raise ValueError("WRONG_RELEASE_CONTEXT")
        comment = Github(os.getenv("RELEASE_GITHUB_TOKEN")).json(
            "issues/comments/" + str(record["comment_id"])
        )
        identity = {
            "checkout_sha": sha,
            "pr_head_sha": os.environ["CI_PR_HEAD_SHA"],
            "run_id": os.environ["GITHUB_RUN_ID"],
            "source_fingerprint": execution_fingerprint(ROOT),
            "governance_policy_sha256": governance_policy_identity(ROOT),
            "engineering_job": os.environ["RELEASE_ENGINEERING_JOB"],
            "security_job": os.environ["RELEASE_SECURITY_JOB"],
            "staging_job": os.environ["RELEASE_STAGING_JOB"],
        }
        result = evaluate(
            ROOT,
            reports,
            security,
            one("validation.json"),
            one("gate-summary.json"),
            comment,
            record,
            identity,
            (surface(ROOT, record["approved_sha"]), surface(ROOT, sha)),
        )
    except Exception as error:
        code = str(error)
        result["blockers"] = [code if re.fullmatch(r"[A-Z_]{1,80}", code) else type(error).__name__]
    (output / "promotion-report.json").write_text(json.dumps(result, indent=2) + "\n")
    if os.getenv("GITHUB_STEP_SUMMARY"):
        lines = [
            "## Scoped technical promotion: " + result["decision"],
            "",
            "| Gate | State |",
            "|---|---|",
        ]
        lines.extend(
            "| " + key + " | " + value + " |" for key, value in result.get("gates", {}).items()
        )
        lines.append("\nNo merge or production deployment is authorized by this result.\n")
        Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text("\n".join(lines))
    print(json.dumps({"decision": result["decision"], "blockers": result["blockers"]}))
    return int(result["decision"] != "GO")


if __name__ == "__main__":
    raise SystemExit(main())
