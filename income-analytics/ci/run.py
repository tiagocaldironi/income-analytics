"""Run isolated checks and publish only allowlisted, payload-free reports."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "ca627ac72f110d0f4d62faaa9c51a08eaed54965"
CERT_TEST = "tests/application/test_historical_shares_units.py::test_shares_unit_020_frozen_engine"
CHECKS = ("ruff", "mypy", "python", "cert48", "node", "runtime")


def isolated_environment(sandbox: Path) -> dict[str, str]:
    # Hosted Windows can expose TEMP through an 8.3 alias (RUNNER~1).
    # Keep database_url(), Path.resolve() and tempfile on the same canonical path.
    sandbox = sandbox.resolve()
    allowed = {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "SYSTEMDRIVE",
        "PROCESSOR_ARCHITECTURE",
        "NUMBER_OF_PROCESSORS",
        "LANG",
        "LC_ALL",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    temp = sandbox / "tmp"
    temp.mkdir(parents=True)
    env.update(
        {
            "TEMP": str(temp),
            "TMP": str(temp),
            "TMPDIR": str(temp),
            "HOME": str(sandbox),
            "USERPROFILE": str(sandbox),
            "PYTHONPATH": os.pathsep.join((str(ROOT / "ci"), str(ROOT / "src"))),
            "PYTHONUTF8": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "INCOME_CI_OFFLINE": "1",
            "INCOME_AUTH_MODE": "local",
            "INCOME_ENV": "development",
            "INCOME_ANALYTICS_TESTING": "1",
            "INCOME_ANALYTICS_DISABLE_BACKGROUND_JOBS": "1",
            "INCOME_ANALYTICS_DATABASE": str(temp / "bootstrap.db"),
            "INCOME_ANALYTICS_COTAHIST_CACHE": str(sandbox / "cotahist"),
            "INCOME_RUN_FIREBASE_EMULATOR_TESTS": "0",
            "INCOME_RUN_FIREBASE_LIVE_TESTS": "0",
            "INCOME_PUBLIC_SIGNUP_ENABLED": "0",
            "COVERAGE_FILE": str(sandbox / ".coverage"),
            "GOOGLE_APPLICATION_CREDENTIALS": str(sandbox / "no-credentials.json"),
            "CLOUDSDK_CONFIG": str(sandbox / "no-gcloud"),
            "PYTHONHASHSEED": "0",
        }
    )
    return env


def safe_junit(raw: Path, destination: Path) -> dict:
    totals = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    cases = []
    suite = ET.Element("testsuite", name="offline")
    if raw.exists():
        for case in ET.parse(raw).getroot().iter("testcase"):
            name, classname = case.get("name", ""), case.get("classname", "")
            status = "passed"
            for tag, state in (("failure", "failed"), ("error", "errors"), ("skipped", "skipped")):
                if case.find(tag) is not None:
                    status = state
                    break
            totals[status] += 1
            cases.append({"class": classname, "name": name, "status": status})
            clean = ET.SubElement(suite, "testcase", name=name, classname=classname)
            if status != "passed":
                tag = {"failed": "failure", "errors": "error", "skipped": "skipped"}[status]
                ET.SubElement(clean, tag, message="See source test; payload intentionally omitted")
    suite.attrib.update(
        {
            "tests": str(sum(totals.values())),
            "failures": str(totals["failed"]),
            "errors": str(totals["errors"]),
            "skipped": str(totals["skipped"]),
        }
    )
    ET.ElementTree(suite).write(destination, encoding="utf-8", xml_declaration=True)
    return {"totals": totals, "cases": cases}


def execute(
    command: list[str], env: dict[str, str], sandbox: Path, label: str
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1200,
    )
    # Raw output stays in a private temporary directory, never the artifact directory.
    (sandbox / f"{label}.raw.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    return result


def run_check(check: str, env: dict[str, str], sandbox: Path, output: Path) -> tuple[int, dict]:
    if check == "runtime":
        code = (
            "import importlib.util; "
            "assert importlib.util.find_spec('pytest') is None, 'Use runtime-only environment'; "
            "from income_analytics.main import app; "
            "import alembic; assert app.title == 'Income Analytics'"
        )
        result = execute([sys.executable, "-c", code], env, sandbox, check)
        return result.returncode, {"scope": "Runtime startup; migrations only in disposable SQLite"}
    if check in {"python", "cert48"}:
        raw = sandbox / "junit.xml"
        targets = [CERT_TEST] if check == "cert48" else ["tests", "ci/test_ci.py"]
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "offline_plugin",
            "-p",
            "pytest_cov",
            *targets,
            "-ra",
            "--continue-on-collection-errors",
            "--tb=short",
            f"--basetemp={sandbox / 'pytest'}",
            f"--junitxml={raw}",
        ]
        if check == "python":
            command += ["--cov=income_analytics", f"--cov-report=xml:{sandbox / 'coverage.xml'}"]
        result = execute(command, env, sandbox, check)
        report = safe_junit(raw, output / f"{check}-junit.xml")
        coverage = sandbox / "coverage.xml"
        if coverage.exists():
            tree = ET.parse(coverage)
            for source in tree.getroot().iter("source"):
                source.text = "src/income_analytics"
            tree.write(output / "coverage.xml", encoding="utf-8", xml_declaration=True)
            report["coverage_line_rate"] = tree.getroot().get("line-rate")
        report["external_policy"] = (
            "Firebase Emulator and cloud tests are explicitly skipped offline"
        )
        report["cert48"] = "BLOCKED_PENDING_INDEPENDENT_RECONCILIATION"
        return result.returncode, report
    if check == "ruff":
        result = execute(
            [sys.executable, "-m", "ruff", "check", ".", "--no-cache", "--output-format=json"],
            env,
            sandbox,
            check,
        )
        findings = json.loads(result.stdout or "[]")
        return result.returncode, {
            "findings": [
                {
                    "file": Path(item["filename"]).relative_to(ROOT).as_posix(),
                    "code": item["code"],
                    "line": item["location"]["row"],
                }
                for item in findings
            ]
        }
    if check == "mypy":
        result = execute(
            [
                sys.executable,
                "-m",
                "mypy",
                "src",
                "--no-incremental",
                "--show-error-codes",
                "--no-pretty",
            ],
            env,
            sandbox,
            check,
        )
        findings = []
        for line in result.stdout.splitlines():
            match = re.match(r"(.+\.py):(\d+): (error|note):.*", line)
            if match and match[3] == "error":
                code = re.search(r"\[([a-z0-9-]+)\]$", line)
                findings.append(
                    {
                        "file": match[1].replace("\\", "/"),
                        "line": int(match[2]),
                        "code": code[1] if code else "unknown",
                    }
                )
        return result.returncode, {"findings": findings}
    suites = []
    paths = [ROOT / "ci/node-self-test.mjs", *sorted((ROOT / "tests/frontend").glob("*.mjs"))]
    for path in paths:
        result = execute(
            ["node", "--import", (ROOT / "ci/node-offline.mjs").as_uri(), str(path)],
            env,
            sandbox,
            path.stem,
        )
        suites.append({"suite": path.name, "exit_code": result.returncode})
    if not suites:
        raise RuntimeError("No frontend suites collected")
    return int(any(item["exit_code"] != 0 for item in suites)), {"suites": suites}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=CHECKS)
    args = parser.parse_args()
    if (ROOT / "data").is_symlink() or (ROOT / "data").is_junction():
        raise SystemExit("Refusing a worktree linked to external reference data")
    output = ROOT / "ci-reports" / args.check
    output.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    sandbox = Path(tempfile.mkdtemp(prefix="income-offline-ci-")).resolve()
    env = isolated_environment(sandbox)
    started = time.monotonic()
    report = {
        "schema": 1,
        "check": args.check,
        "baseline": BASELINE,
        "checkout_sha": sha,
        "event_sha": os.getenv("GITHUB_SHA", ""),
        "pr_head_sha": os.getenv("CI_PR_HEAD_SHA", ""),
        "python": sys.version.split()[0],
        "lock_sha256": hashlib.sha256(
            (
                ROOT
                / "ci"
                / (
                    "runtime-windows-py314.lock"
                    if args.check == "runtime"
                    else "requirements-windows-py314.lock"
                )
            ).read_bytes()
        ).hexdigest()
        if args.check != "node"
        else None,
        "worktree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
    }
    try:
        code, details = run_check(args.check, env, sandbox, output)
        report.update(details)
    except Exception as error:
        code = 2
        # Do not include exception text (which can contain captured test payloads).
        report["runner_error"] = type(error).__name__
    report.update(exit_code=code, elapsed_seconds=round(time.monotonic() - started, 3))
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
            summary.write(f"### {args.check}\n\nCheckout: `{sha}`; exit: `{code}`.\n\n")
            summary.write("Payload-free details are in the per-SHA artifact.\n\n")
            if "totals" in report:
                summary.write(f"Counts: `{json.dumps(report['totals'])}`.\n\n")
            if "findings" in report:
                summary.write(f"Findings: {len(report['findings'])}.\n\n")
    print(f"{args.check}: exit={code}; checkout={sha}; report=ci-reports/{args.check}/result.json")
    if "totals" in report:
        print(json.dumps(report["totals"]))
    if "findings" in report:
        print(f"Findings: {len(report['findings'])}")
    if not os.getenv("GITHUB_ACTIONS"):
        print(f"Local raw diagnostics (not uploaded): {sandbox}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
