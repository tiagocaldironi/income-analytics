"""Versioned execution and policy identities; no financial manifest changes."""

import hashlib
import json
import subprocess
from pathlib import Path

FINGERPRINT_VERSION = 2
POLICY_FILES = (
    "income-analytics/ci/artifact.py",
    "income-analytics/ci/build_pipeline.py",
    "income-analytics/ci/smoke_artifact.py",
    "income-analytics/ci/build_policy.json",
    "income-analytics/ci/build_installation.md",
    "income-analytics/ci/test_build_artifact.py",
    ".github/CODEOWNERS",
    ".github/workflows/ci-offline.yml",
    "income-analytics/ci/gate_policy.py",
    "income-analytics/ci/gate_plugin.py",
    "income-analytics/ci/governance.py",
    "income-analytics/ci/pipeline_identity.py",
    "income-analytics/ci/test-groups.json",
    "income-analytics/ci/test_ci.py",
    "income-analytics/ci/test_governance.py",
    "income-analytics/ci/test_pr52_governance.py",
    "income-analytics/docs/engineering/cicd-assessment/ci_quality_baseline.json",
    "income-analytics/docs/engineering/cicd-assessment/ci_branch_protection_bootstrap.json",
)


def digest_files(git_root: Path, paths) -> str:
    records = [(name, hashlib.sha256((git_root / name).read_bytes()).hexdigest()) for name in paths]
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()


def governance_policy_identity(root: Path) -> str:
    # Missing policy or governance tests is fatal, even for non-Python jobs.
    return digest_files(root.parent, POLICY_FILES)


def execution_fingerprint(root: Path) -> str:
    paths = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root, text=True
    ).splitlines()
    selected = set(POLICY_FILES)
    for file in paths:
        if file.startswith(("src/", "tests/", "ci/", "alembic/")) or file in {
            "pyproject.toml",
            "alembic.ini",
            "docs/engineering/cicd-assessment/magic_formula_reference_provenance.json",
        }:
            if (root / file).is_file():
                selected.add("income-analytics/" + file)
    content = digest_files(root.parent, sorted(selected))
    return hashlib.sha256(f"execution-v{FINGERPRINT_VERSION}:{content}".encode()).hexdigest()
