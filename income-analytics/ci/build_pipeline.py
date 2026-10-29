"""Two independent Git checkouts/wheel downloads, byte comparison, clean startup."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from artifact import build, sha, verify
from governance import source_fingerprint
from pipeline_identity import FINGERPRINT_VERSION, governance_policy_identity
from smoke_artifact import smoke

ROOT = Path(__file__).resolve().parents[1]


def execute(args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, timeout=600)
    if result.returncode:
        raise RuntimeError("BUILD_SUBPROCESS_FAILED")


def compare_builds(first, second):
    if sha(first.read_bytes()) != sha(second.read_bytes()):
        raise ValueError("BUILD_CONTENT_DIVERGENCE")


def main():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    output = ROOT / "ci-reports/build"
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": 3, "check": "build", "checkout_sha": commit,
        "source_fingerprint": source_fingerprint(), "fingerprint_version": FINGERPRINT_VERSION,
        "governance_policy_sha256": governance_policy_identity(ROOT),
        "pr_head_sha": os.getenv("CI_PR_HEAD_SHA", ""), "event_sha": os.getenv("GITHUB_SHA", ""),
        "worktree_dirty": bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        "python": sys.version.split()[0], "status": "FAIL", "exit_code": 2,
    }
    try:
        if report["worktree_dirty"]:
            raise ValueError("BUILD_REQUIRES_CLEAN_CHECKOUT")
        with tempfile.TemporaryDirectory(prefix="income-build-") as temporary:
            sandbox = Path(temporary).resolve()
            archives = []
            for label in ("first", "second"):
                clone = sandbox / label
                execute(["git", "-c", "core.autocrlf=false", "clone", "--shared",
                         "--no-checkout", str(ROOT.parent), str(clone)], sandbox)
                execute(["git", "config", "core.autocrlf", "false"], clone)
                execute(["git", "checkout", "--detach", commit], clone)
                wheels = sandbox / (label + "-wheels")
                execute([
                    sys.executable, "-m", "pip", "--isolated", "download", "--no-cache-dir",
                    "--index-url", "https://pypi.org/simple", "--only-binary=:all:",
                    "--require-hashes", "-r", "income-analytics/ci/runtime-windows-py314.lock",
                    "--dest", str(wheels),
                ], clone)
                archive = sandbox / (label + ".zip")
                build(clone, wheels, archive, commit)
                archives.append(archive)
            compare_builds(*archives)
            identity = verify(archives[0], commit)
            installation = smoke(archives[0], commit, identity["sha256"])
            name = f"income-analytics-{commit}-windows-x64.zip"
            destination = output / name
            destination.write_bytes(archives[0].read_bytes())
            destination.with_suffix(".sha256").write_text(identity["sha256"] + "  " + name + "\n")
            import zipfile

            with zipfile.ZipFile(destination) as bundle:
                manifest = json.loads(bundle.read("manifest.json"))
            (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            report.update(
                status="PASS", exit_code=0, reproducibility="PASS", independent_builds=2,
                artifact=name, artifact_sha256=identity["sha256"], manifest="PASS",
                packaged_files=identity["files"], installation=installation,
                artifact_source_fingerprint=manifest["source_fingerprint"],
                build_policy_sha256=manifest["build_policy_sha256"],
            )
    except Exception as error:
        report["failure_category"] = (
            str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__
        )
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"build: {report['status']}")
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
