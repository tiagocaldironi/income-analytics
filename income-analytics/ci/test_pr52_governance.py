"""Manual PR5.2 checks of proposed governance; no remote writes or financial changes.

Not added to the published workflow: run explicitly alongside existing CI tests.
Server-side review enforcement cannot be proven by these local checks.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from gate_policy import ROOT, compare_diagnostics, summarize_reports
from governance import parse_mypy_output

DOCS = ROOT / "docs/engineering/cicd-assessment"
GIT_ROOT = ROOT.parent


def owner_rules(text):
    rules = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        pattern, *owners = line.split()
        # Validate only the intentionally simple anchored path subset used here.
        assert pattern.startswith("/") and not any(c in pattern for c in "!*?[]\\")
        assert owners and all(owner == "@tiagocaldironi" for owner in owners)
        assert (GIT_ROOT / pattern.lstrip("/")).exists()
        rules.append((pattern, owners))
    return rules


def owners_for(path, rules):
    owners = []
    for pattern, proposed in rules:
        name = pattern.lstrip("/")
        if path == name or (pattern.endswith("/") and path.startswith(name)):
            owners = proposed
    return owners


def protection():
    return json.loads((DOCS / "ci_branch_protection_proposal.json").read_text())


def test_critical_paths_have_verified_owner_and_valid_anchored_patterns():
    rules = owner_rules((GIT_ROOT / ".github/CODEOWNERS").read_text())
    paths = [
        ".github/CODEOWNERS",
        ".github/workflows/ci-offline.yml",
        "income-analytics/ci/gate_policy.py",
        "income-analytics/ci/gate_plugin.py",
        "income-analytics/ci/test-groups.json",
        "income-analytics/ci/governance.py",
        "income-analytics/docs/engineering/cicd-assessment/ci_quality_baseline.json",
        "income-analytics/docs/engineering/cicd-assessment/ci_gate_policy.md",
        "income-analytics/docs/engineering/cicd-assessment/ci_branch_protection_proposal.json",
    ]
    assert all(owners_for(p, rules) == ["@tiagocaldironi"] for p in paths)
    assert not owners_for("other-project/ci/governance.py", rules)


def test_missing_workflow_ownership_is_detected():
    rules = owner_rules((GIT_ROOT / ".github/CODEOWNERS").read_text())
    mutated = [(p, o) for p, o in rules if p != "/.github/workflows/"]
    assert not owners_for(".github/workflows/ci-offline.yml", mutated)


def test_proposal_requires_independent_review_before_activation():
    plan = protection()
    assert plan["state"] == "PROPOSAL_ONLY_DO_NOT_APPLY"
    assert len(plan["activation_blockers"]) == 4
    payload = plan["proposed_branch_protection_payload"]
    reviews = payload["required_pull_request_reviews"]
    assert reviews["required_approving_review_count"] == 1
    assert reviews["require_last_push_approval"] and reviews["dismiss_stale_reviews"]
    assert reviews["require_code_owner_reviews"] and payload["enforce_admins"]
    assert payload["required_conversation_resolution"]
    assert payload["allow_force_pushes"] is payload["allow_deletions"] is False


def test_required_check_name_and_app_match_published_workflow():
    workflow = yaml.load(
        (GIT_ROOT / ".github/workflows/ci-offline.yml").read_text(), Loader=yaml.BaseLoader
    )
    expected = protection()["proposed_branch_protection_payload"]["required_status_checks"]
    assert expected == {
        "strict": True,
        "checks": [{"context": "CI / Engineering", "app_id": 15368}],
    }
    assert workflow["jobs"]["engineering_gate"]["name"] == "CI / Engineering"
    assert "merge_group" not in workflow["on"]
    assert protection()["merge_queue"] == "DISABLED_NO_MERGE_GROUP_SUPPORT"


def test_workflow_has_no_auto_approval_or_write_token():
    text = (GIT_ROOT / ".github/workflows/ci-offline.yml").read_text()
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request_target" not in workflow["on"]
    assert all(s not in text for s in ("gh pr review", "--approve", "enablePullRequestAutoMerge"))
    # This does NOT prove review enforcement: develop currently has no protection.


@pytest.mark.parametrize("tool", ["ruff", "mypy"])
def test_real_new_tool_diagnostic_rejects_non_regression(tool, tmp_path):
    source = tmp_path / "new_regression.py"
    source.write_text("value: int = 'wrong'\nprint(undefined_name)\n", encoding="utf-8")
    args = [sys.executable, "-m", tool]
    if tool == "ruff":
        args += ["check", str(source), "--no-cache", "--select=F821", "--output-format=json"]
    else:
        args += [str(source), "--no-incremental", "--show-error-codes", "--no-pretty"]
    result = subprocess.run(args, cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    if tool == "ruff":
        findings = [
            {
                "tool": tool,
                "file": "temporary/new_regression.py",
                "line": x["location"]["row"],
                "column": x["location"]["column"],
                "code": x["code"],
                "message": x["message"],
            }
            for x in json.loads(result.stdout)
        ]
    else:
        findings = parse_mypy_output(result.stdout)
    assert findings
    assert compare_diagnostics(findings, [])["status"] == "FAIL"


def test_baseline_mutation_is_identifiable_without_changing_original(tmp_path):
    baseline = DOCS / "ci_quality_baseline.json"
    original = baseline.read_bytes()
    archive = json.loads((DOCS / "ci_evidence_archive_manifest.json").read_text())
    quality = next(a for a in archive["artifacts"] if a["name"].startswith("governance-quality-"))
    expected_file = next(f for f in quality["files"] if f["path"] == "result.json")
    archived = Path(os.environ["PR52_ARCHIVE_ROOT"]) / "reports" / quality["name"] / "result.json"
    assert hashlib.sha256(archived.read_bytes()).hexdigest() == expected_file["sha256"]
    expected = json.loads(archived.read_text())["baseline_sha256"]
    assert hashlib.sha256(original).hexdigest() == expected
    mutated = json.loads(original)
    mutated["findings"] = []
    copy = tmp_path / "altered_baseline.json"
    copy.write_text(json.dumps(mutated), encoding="utf-8")
    assert hashlib.sha256(copy.read_bytes()).hexdigest() != expected
    assert baseline.read_bytes() == original


def test_real_financial_blockers_are_not_green():
    manifest = json.loads((DOCS / "ci_evidence_archive_manifest.json").read_text())
    reports = {}
    for artifact in manifest["artifacts"]:
        if artifact["name"].startswith("governance-"):
            path = (
                Path(os.environ["PR52_ARCHIVE_ROOT"]) / "reports" / artifact["name"] / "result.json"
            )
            doc = json.loads(path.read_text())
            reports[doc["check"]] = doc
    summary = summarize_reports(reports)
    assert summary["engineering_ci"] == "PASS"
    assert summary["financial_certification"] == summary["release_readiness"] == "BLOCKED"
    assert summary["deployment_authorized"] is False
    assert reports["financial"]["exit_code"] == 1
    blocked = [c for c in reports["financial"]["cases"] if c["status"] in {"failed", "errors"}]
    assert any(c["name"] == "test_shares_unit_020_frozen_engine" for c in blocked)
