"""Hermetic PR5.2 governance checks, explicitly included in Engineering.

Server-side review enforcement cannot be proven by these local checks.
"""

import hashlib
import json
import subprocess
import sys

import pytest
import yaml
from gate_policy import ROOT, compare_diagnostics, summarize_reports
from governance import parse_mypy_output
from test_governance import engineering_reports

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
    return json.loads((DOCS / "ci_branch_protection_bootstrap.json").read_text())


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
        "income-analytics/docs/engineering/cicd-assessment/ci_branch_protection_bootstrap.json",
    ]
    assert all(owners_for(p, rules) == ["@tiagocaldironi"] for p in paths)
    assert not owners_for("other-project/ci/governance.py", rules)


def test_missing_workflow_ownership_is_detected():
    rules = owner_rules((GIT_ROOT / ".github/CODEOWNERS").read_text())
    mutated = [(p, o) for p, o in rules if p != "/.github/workflows/"]
    assert not owners_for(".github/workflows/ci-offline.yml", mutated)


def test_single_maintainer_proposal_defers_independent_review_to_level_two():
    plan = protection()
    assert plan["state"] == "PROPOSAL_ONLY_NOT_APPLIED"
    assert plan["risk"] == "INDEPENDENT_REVIEW_NOT_AVAILABLE"
    payload = plan["proposed_branch_protection_payload"]
    reviews = payload["required_pull_request_reviews"]
    assert reviews["required_approving_review_count"] == 0
    assert not any(
        reviews[k]
        for k in (
            "require_last_push_approval",
            "dismiss_stale_reviews",
            "require_code_owner_reviews",
        )
    )
    assert payload["enforce_admins"]
    assert plan["future_level"]["required_approving_review_count"] == 1
    assert plan["future_level"]["require_code_owner_reviews"]
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
    # Versioned blob is the reference, not a personal archive or invented hosted result.
    versioned = subprocess.check_output(
        [
            "git",
            "show",
            "HEAD:income-analytics/docs/engineering/cicd-assessment/ci_quality_baseline.json",
        ],
        cwd=ROOT,
    )
    expected = hashlib.sha256(versioned).hexdigest()
    assert hashlib.sha256(original).hexdigest() == expected
    mutated = json.loads(original)
    mutated["findings"] = []
    copy = tmp_path / "altered_baseline.json"
    copy.write_text(json.dumps(mutated), encoding="utf-8")
    assert hashlib.sha256(copy.read_bytes()).hexdigest() != expected
    assert baseline.read_bytes() == original


def test_financial_blockers_cannot_be_relabelled_as_pass():
    # Synthetic unit inputs only; actual financial tests still run in their own job.
    identity = {
        "checkout_sha": "unit-sha",
        "source_fingerprint": "unit-content",
        "fingerprint_version": 2,
        "governance_policy_sha256": "unit-policy",
    }
    reports = engineering_reports()
    for report in reports.values():
        report.update(identity)
    reports["financial"] = {
        **identity,
        "exit_code": 0,
        "status": "PASS",
        "blockers": ["CERT_48"],
    }
    summary = summarize_reports(reports)
    assert summary["engineering_ci"] == "PASS"
    assert summary["financial_certification"] == summary["release_readiness"] == "BLOCKED"
    assert summary["deployment_authorized"] is False


def test_bootstrap_local_model_requires_pr_checks_and_conversations_not_reviewers():
    """Policy simulation only, not evidence of remote enforcement."""
    payload = protection()["proposed_branch_protection_payload"]

    def allowed(action, *, check=True, current=True, conversations=True):
        if action == "force_push":
            return payload["allow_force_pushes"]
        if action == "delete":
            return payload["allow_deletions"]
        if action != "merge_pr" and payload["required_pull_request_reviews"] is not None:
            return False
        return (
            check
            and (current or not payload["required_status_checks"]["strict"])
            and (conversations or not payload["required_conversation_resolution"])
            and payload["required_pull_request_reviews"]["required_approving_review_count"] == 0
        )

    assert allowed("merge_pr")
    assert not allowed("direct_push")
    assert not allowed("force_push")
    assert not allowed("delete")
    assert not allowed("merge_pr", check=False)
    assert not allowed("merge_pr", current=False)
    assert not allowed("merge_pr", conversations=False)
