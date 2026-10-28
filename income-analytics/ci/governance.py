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
from gate_policy import BASELINE, ROOT, compare_diagnostics, normalized_message, summarize_reports

CHECKS = ("runtime", "engineering", "financial", "python", "node", "ruff", "mypy", "quality")


def source_fingerprint() -> str:
    paths = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True
    ).splitlines()
    selected = []
    for file in sorted(set(paths)):
        if file.startswith(("src/", "tests/", "ci/", "alembic/")) or file in {
            "pyproject.toml",
            "alembic.ini",
            "docs/engineering/cicd-assessment/ci_quality_baseline.json",
            "docs/engineering/cicd-assessment/magic_formula_reference_provenance.json",
        }:
            path = ROOT / file
            if path.is_file():
                selected.append((file, hashlib.sha256(path.read_bytes()).hexdigest()))
    workflow = ROOT.parent / ".github/workflows/ci-offline.yml"
    selected.append(
        (".github/workflows/ci-offline.yml", hashlib.sha256(workflow.read_bytes()).hexdigest())
    )
    return hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()


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
        for line in result.stdout.splitlines():
            match = re.match(r"(.+\.py):(\d+): error: (.*)  \[([^]]+)\]$", line)
            if match:
                findings.append(
                    {
                        "tool": check,
                        "file": match[1].replace("\\", "/"),
                        "line": int(match[2]),
                        "column": None,
                        "code": match[4],
                        "message": normalized_message(match[3]),
                    }
                )
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
        details["status"] = "BLOCKED"
        details["blockers"] = [
            "CERT_48_REQUIRES_INDEPENDENT_RECONCILIATION",
            "IDENTITY_FROZEN_BYTES_UNRESOLVED",
            "22_HISTORICAL_REFERENCES_UNAPPROVED",
        ]
        return 1, details  # Explicit, non-approved check even if future assertions happen to pass.
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
    if check in {"engineering", "financial", "python"}:
        return python_check(check, env, sandbox, output)
    if check in {"ruff", "mypy"}:
        code, findings = quality_findings(check, env, sandbox)
        return code, {"status": "FAIL_WITH_DEBT" if findings else "PASS", "findings": findings}
    if check == "quality":
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        if (
            hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest()
            != baseline["quality_configuration_sha256"]
        ):
            raise ValueError("QUALITY_CONFIGURATION_REVIEW_REQUIRED")
        if (
            hashlib.sha256((ROOT / "ci/requirements-windows-py314.lock").read_bytes()).hexdigest()
            != baseline["lock_sha256"]
        ):
            raise ValueError("QUALITY_LOCK_REVIEW_REQUIRED")
        actual, exits = [], {}
        for tool in ("ruff", "mypy"):
            if importlib.metadata.version(tool) != baseline["tools"][tool]:
                raise ValueError("QUALITY_TOOL_VERSION_REVIEW_REQUIRED")
            code, findings = quality_findings(tool, env, sandbox)
            actual.extend(findings)
            exits[tool] = code
        comparison = compare_diagnostics(actual, baseline["findings"])
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
    args = parser.parse_args()
    if args.check == "summary":
        reports = {}
        for path in args.reports.rglob("result.json"):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document["check"] in reports:
                raise ValueError("DUPLICATE_CHECK_REPORT")
            reports[document["check"]] = document
        summary = summarize_reports(reports)
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
        "schema": 2,
        "check": args.check,
        "checkout_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_fingerprint": source_fingerprint(),
        "pr_head_sha": os.getenv("CI_PR_HEAD_SHA", ""),
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
