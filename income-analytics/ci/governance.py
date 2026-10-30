"""Run independent engineering, diagnostic and financial checks with audit metadata."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import run as legacy
from engineering_debt import (
    classify_ruff,
    reconciled_findings,
    require_clean_diagnostics,
    ruff_exception_findings,
)
from financial_certification import evaluate as evaluate_financial_evidence
from financial_certification import failure_causes
from gate_policy import (
    BASELINE,
    ROOT,
    compare_diagnostics,
    normalized_message,
    require_security_baseline,
    summarize_reports,
)
from operational import require_operational
from operational import run as run_operational
from pipeline_identity import FINGERPRINT_VERSION, execution_fingerprint, governance_policy_identity

CHECKS = (
    "runtime",
    "engineering",
    "financial",
    "python",
    "node",
    "ruff",
    "mypy",
    "quality",
    "operational",
)


def source_fingerprint() -> str:
    return execution_fingerprint(ROOT)


def parse_mypy_output(output: str) -> list[dict]:
    """Reject partially parsed output instead of hiding new diagnostics."""
    findings = []
    for line in output.splitlines():
        match = re.match(r"(.+\.pyi?):(\d+): error: (.*)  \[([^]]+)\]$", line)
        if match:
            findings.append(
                {
                    "tool": "mypy",
                    "file": match[1].replace("\\", "/"),
                    "line": int(match[2]),
                    "column": None,
                    "code": match[4],
                    "message": normalized_message(match[3]),
                }
            )
        elif ": error:" in line or line.lstrip().startswith("error:"):
            raise ValueError("UNPARSED_MYPY_DIAGNOSTIC")
        summary = re.match(r"Found (\d+) errors?\b", line)
        if summary and int(summary[1]) != len(findings):
            raise ValueError("MYPY_DIAGNOSTIC_COUNT_MISMATCH")
    return findings


def quality_findings(check: str, env: dict, sandbox: Path) -> tuple[int, list[dict]]:
    if check == "ruff":
        args = [sys.executable, "-m", "ruff", "check", ".", "--no-cache", "--output-format=json"]
    else:
        args = [
            sys.executable,
            "-m",
            "mypy",
            "src",
            "--no-incremental",
            "--show-error-codes",
            "--no-pretty",
        ]
    result = legacy.execute(args, env, sandbox, check)
    findings = []
    if check == "ruff":
        for item in json.loads(result.stdout or "[]"):
            findings.append(
                {
                    "tool": check,
                    "file": Path(item["filename"]).relative_to(ROOT).as_posix(),
                    "line": item["location"]["row"],
                    "column": item["location"]["column"],
                    "code": item["code"],
                    "message": normalized_message(item["message"]),
                }
            )
    else:
        findings = parse_mypy_output(result.stdout)
    if result.returncode not in (0, 1) or (result.returncode == 1 and not findings):
        raise ValueError("QUALITY_TOOL_OR_PARSER_FAILURE")
    return result.returncode, findings


def python_check(check: str, env: dict, sandbox: Path, output: Path) -> tuple[int, dict]:
    gate = {"python": "full", "engineering": "engineering", "financial": "financial"}[check]
    inventory = sandbox / "inventory.json"
    env["CI_TEST_INVENTORY"] = str(inventory)
    raw = sandbox / "junit.xml"
    args = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "offline_plugin",
        "-p",
        "gate_plugin",
        "tests",
        "ci/test_ci.py",
        "ci/test_governance.py",
        "ci/test_pr52_governance.py",
        "ci/test_build_artifact.py",
        "ci/test_delivery.py",
        "ci/test_security.py",
        "ci/test_financial_certification.py",
        "ci/test_operational.py",
        "ci/test_engineering_debt.py",
        f"--ci-gate={gate}",
        "-ra",
        "--tb=short",
        "--continue-on-collection-errors",
        f"--basetemp={sandbox / 'pytest'}",
        f"--junitxml={raw}",
    ]
    if check == "python":
        args += [
            "-p",
            "pytest_cov",
            "--cov=income_analytics",
            f"--cov-report=xml:{sandbox / 'coverage.xml'}",
        ]
    result = legacy.execute(args, env, sandbox, check)
    details = legacy.safe_junit(raw, output / f"{check}-junit.xml")
    if not inventory.exists():
        raise ValueError("INVENTORY_OR_COLLECTION_FAILED")
    entries = json.loads(inventory.read_text(encoding="utf-8"))
    statuses = {
        (case["class"].replace(".", "/") + ".py::" + case["name"]): case["status"]
        for case in details["cases"]
    }
    for entry in entries:
        if entry["selected"]:
            entry["result"] = statuses.get(entry["nodeid"], "RESULT_NOT_MATCHED")
    (output / "inventory.json").write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    details["collected"] = len(entries)
    details["selected"] = sum(entry["selected"] for entry in entries)
    details["deselected"] = [entry["nodeid"] for entry in entries if not entry["selected"]]
    if any(entry["result"] == "RESULT_NOT_MATCHED" for entry in entries):
        return 2, {**details, "status": "FAIL", "reason": "INVENTORY_JUNIT_MISMATCH"}
    if check == "engineering":
        if details["totals"]["skipped"] or details["totals"]["passed"] == 0:
            return 1, {**details, "status": "FAIL", "reason": "SKIP_OR_EMPTY_ENGINEERING_SCOPE"}
    if check == "financial":
        details["failure_causes"] = failure_causes(raw)
        evidence = evaluate_financial_evidence(ROOT, details)
        details.update(evidence)
        approved = evidence["financial_state"] == "FINANCIAL_PASS" and result.returncode == 0
        details["status"] = (
            "PASS"
            if approved
            else ("BLOCKED" if evidence["financial_state"] == "FINANCIAL_BLOCKED" else "FAIL")
        )
        return (0 if approved else max(result.returncode, 1)), details
    coverage = sandbox / "coverage.xml"
    if coverage.exists():
        import xml.etree.ElementTree as ET

        tree = ET.parse(coverage)
        for source in tree.getroot().iter("source"):
            source.text = "src/income_analytics"
        tree.write(output / "coverage.xml", encoding="utf-8", xml_declaration=True)
        details["coverage_line_rate"] = tree.getroot().get("line-rate")
    return result.returncode, {**details, "status": "PASS" if result.returncode == 0 else "FAIL"}


def run_check(check: str, env: dict, sandbox: Path, output: Path) -> tuple[int, dict]:
    if check == "operational":
        return run_operational(env, sandbox, output)
    if check in {"engineering", "financial", "python"}:
        return python_check(check, env, sandbox, output)
    if check in {"ruff", "mypy"}:
        code, findings = quality_findings(check, env, sandbox)
        if check == "ruff":
            policy = json.loads((ROOT / "ci/ruff-exceptions.json").read_text(encoding="utf-8"))
            result, details = classify_ruff(code, findings, ruff_exception_findings(ROOT, policy))
            details["ruff_version"] = importlib.metadata.version("ruff")
            return result, details
        return code, {"status": "FAIL_WITH_DEBT" if findings else "PASS", "findings": findings}
    if check == "quality":
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        compatibility = json.loads(
            (ROOT / "docs/engineering/security/quality_compatibility.json").read_text(
                encoding="utf-8"
            )
        )
        if hashlib.sha256(BASELINE.read_bytes()).hexdigest() != compatibility["baseline_sha256"]:
            raise ValueError("ORIGINAL_QUALITY_BASELINE_CHANGED")
        expected_findings = json.loads(json.dumps(baseline["findings"]))
        for relocation in compatibility["relocated"]:
            matching = [
                row
                for row in expected_findings
                if (
                    row["file"] == "src/income_analytics/main.py"
                    and row["line"] == relocation["before"]
                    and row["code"] == relocation["code"]
                    and row["message"] == relocation["message"]
                )
            ]
            if len(matching) != 1 or relocation["after"] != relocation["before"] + 2:
                raise ValueError("UNREVIEWED_DIAGNOSTIC_RELOCATION")
            matching[0]["line"] = relocation["after"]
        if (
            hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest()
            != compatibility["quality_configuration_sha256"]
        ):
            raise ValueError("QUALITY_CONFIGURATION_REVIEW_REQUIRED")
        if (
            hashlib.sha256((ROOT / "ci/requirements-windows-py314.lock").read_bytes()).hexdigest()
            != compatibility["lock_sha256"]
        ):
            raise ValueError("QUALITY_LOCK_REVIEW_REQUIRED")
        actual, exits = [], {}
        ledger = json.loads(
            (ROOT / "docs/engineering/engineering-debt-closure/quality_ledger.json").read_text(
                encoding="utf-8"
            )
        )
        expected_findings = reconciled_findings(expected_findings, ledger, ROOT)
        for tool in ("ruff", "mypy"):
            if importlib.metadata.version(tool) != baseline["tools"][tool]:
                raise ValueError("QUALITY_TOOL_VERSION_REVIEW_REQUIRED")
            code, findings = quality_findings(tool, env, sandbox)
            actual.extend(findings)
            exits[tool] = code
        comparison = compare_diagnostics(actual, expected_findings)
        comparison["raw_tool_exit_codes"] = exits
        comparison["baseline_sha256"] = hashlib.sha256(BASELINE.read_bytes()).hexdigest()
        comparison["diagnostics_clean"] = not actual
        comparison["meaning"] = "Non-regression only; does not approve existing Ruff/mypy debt"
        return int(comparison["status"] != "PASS"), comparison
    code, details = legacy.run_check(check, env, sandbox, output)
    return code, {**details, "status": "PASS" if code == 0 else "FAIL"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=(*CHECKS, "summary"))
    parser.add_argument("--reports", type=Path, default=ROOT / "ci-reports")
    parser.add_argument("--security-status")
    parser.add_argument("--operational-status")
    args = parser.parse_args()
    if args.check == "summary":
        reports = {}
        for path in args.reports.rglob("result.json"):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document["check"] in reports:
                raise ValueError("DUPLICATE_CHECK_REPORT")
            reports[document["check"]] = document
        summary = require_security_baseline(summarize_reports(reports), args.security_status)
        summary = require_operational(
            summary, reports.get("operational", {}), args.operational_status
        )
        approved_ruff = ruff_exception_findings(
            ROOT,
            json.loads((ROOT / "ci/ruff-exceptions.json").read_text(encoding="utf-8")),
            observed_version=reports.get("ruff", {}).get("ruff_version", "MISSING"),
        )
        summary = require_clean_diagnostics(summary, reports, approved_ruff)
        args.reports.mkdir(parents=True, exist_ok=True)
        (args.reports / "gate-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
        return int(summary["engineering_ci"] != "PASS")
    if (ROOT / "data").is_symlink() or (ROOT / "data").is_junction():
        raise ValueError("EXTERNAL_DATA_DIRECTORY_FORBIDDEN")
    output = args.reports / args.check
    output.mkdir(parents=True, exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix="income-governance-")).resolve()
    report = {
        "schema": 3,
        "check": args.check,
        "checkout_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_fingerprint": source_fingerprint(),
        "fingerprint_version": FINGERPRINT_VERSION,
        "governance_policy_sha256": governance_policy_identity(ROOT),
        "pr_head_sha": os.getenv("CI_PR_HEAD_SHA", ""),
        "run_id": os.getenv("GITHUB_RUN_ID", "LOCAL"),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", "1"),
        "event_sha": os.getenv("GITHUB_SHA", ""),
        "worktree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
        "python": sys.version.split()[0],
    }
    started = time.monotonic()
    try:
        code, details = run_check(args.check, legacy.isolated_environment(sandbox), sandbox, output)
        report.update(details)
    except Exception as error:
        code = 2
        report.update(status="FAIL", runner_error=type(error).__name__)
        if args.check == "operational":
            report.update(
                operational_state="OPERATIONAL_NOT_VERIFIED",
                host="HOST_NOT_VERIFIED",
                beta="BETA_NOT_AUTHORIZED",
                production="PRODUCTION_NOT_AUTHORIZED",
            )
        if args.check == "financial":
            report.update(
                financial_state="FINANCIAL_NOT_VERIFIED",
                mandatory_coverage_verified=False,
                blockers=["FINANCIAL_RUNNER_NOT_VERIFIED"],
                production_authorized=False,
            )
    report.update(exit_code=code, elapsed_seconds=round(time.monotonic() - started, 3))
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
            summary.write(
                f"### {args.check}: {report['status']}\n\nSHA `{report['checkout_sha']}`\n\n"
            )
            summary.write(
                "Engineering success is not financial certification or deploy authorization.\n"
            )
    print(f"{args.check}: {report['status']}; exit={code}; reports={output.name}")
    if "totals" in report:
        print(json.dumps(report["totals"]))
    if not os.getenv("GITHUB_ACTIONS"):
        print(f"Private raw diagnostics: {sandbox}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
