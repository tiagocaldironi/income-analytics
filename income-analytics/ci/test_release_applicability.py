"""Synthetic controls for scope-aware release applicability."""

import hashlib
import json
from pathlib import Path

import pytest
from release_applicability import evaluate, policy_digest, valid_policy_approval

ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "release-applicability-policy.json"
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def results(**overrides):
    value = {
        "CERT_48": "BLOCKED",
        "IDENTITY_PROVENANCE_UNAPPROVED": "BLOCKED",
        "22_HISTORICAL_REFERENCES_UNAPPROVED": "BLOCKED",
        "CORE_FINANCIAL_REGRESSION": "PASS",
        "SECURITY": "PASS",
        "BUILD": "PASS",
        "STAGING": "PASS",
    }
    value.update(overrides)
    return value


def test_visual_change_can_be_eligible_only_after_approved_policy():
    report = evaluate(
        ["income-analytics/src/income_analytics/api/static/css/app.css"],
        {"complete": True, "modules": []},
        results(),
        POLICY,
        approved=True,
    )
    check(report["scopes"] == ["visual_only"], "visual CSS scope was not classified")
    for control in (
        "CERT_48",
        "IDENTITY_PROVENANCE_UNAPPROVED",
        "22_HISTORICAL_REFERENCES_UNAPPROVED",
        "CORE_FINANCIAL_REGRESSION",
    ):
        check(report["controls"][control] == "NOT_APPLICABLE", f"{control} was not N/A")
    check(report["decision"] == "ELIGIBLE", "approved visual scope should be eligible")
    check(report["deployment_authorized"] is False, "evaluator must never authorize deployment")


def test_core_financial_change_requires_core_tests_and_proves_formula_independence():
    report = evaluate(
        ["income-analytics/src/income_analytics/application/treasury.py"],
        {"complete": True, "modules": ["income_analytics.application.treasury"]},
        results(),
        POLICY,
        approved=True,
    )
    check(report["controls"]["CORE_FINANCIAL_REGRESSION"] == "PASS", "core tests must pass")
    check(report["controls"]["CERT_48"] == "NOT_APPLICABLE", "Formula control should be N/A")
    check(report["decision"] == "ELIGIBLE", "independent core scope should be eligible")


def test_not_applicable_is_blocked_until_explicit_policy_approval():
    report = evaluate(
        ["income-analytics/src/income_analytics/api/static/css/app.css"],
        {"complete": True, "modules": []},
        results(),
        POLICY,
        approved=False,
    )
    check(report["decision"] == "BLOCKED", "unapproved policy must block")
    check(report["controls"]["CERT_48"] == "BLOCKED", "unapproved N/A must stay blocked")
    check(
        report["reasons"]["CERT_48"] == "RELEASE_POLICY_APPROVAL_REQUIRED",
        "approval blocker should be visible",
    )


def test_formula_change_keeps_all_historical_controls_applicable_and_blocking():
    report = evaluate(
        ["income-analytics/src/income_analytics/application/magic_formula_stocks.py"],
        {"complete": True, "modules": ["income_analytics.application.magic_formula_stocks"]},
        results(),
        POLICY,
        approved=True,
    )
    for control in (
        "CERT_48",
        "IDENTITY_PROVENANCE_UNAPPROVED",
        "22_HISTORICAL_REFERENCES_UNAPPROVED",
    ):
        check(report["controls"][control] == "BLOCKED", f"{control} must remain blocked")
    check(report["decision"] == "BLOCKED", "Formula historical blockers must block Formula")


def test_unknown_paths_and_missing_dependency_trace_fail_closed():
    unknown = evaluate(
        ["income-analytics/src/income_analytics/application/new_module.py"],
        {"complete": True, "modules": []}, results(), POLICY, approved=True
    )
    check(unknown["scopes"] == ["unknown"], "unmapped paths must remain unknown")
    check(
        all(unknown["controls"][name] == "BLOCKED" for name in POLICY["controls"]),
        "unknown scope must block each financial control",
    )
    check(unknown["decision"] == "BLOCKED", "unknown scope must block release")

    incomplete = evaluate(
        ["income-analytics/src/income_analytics/api/static/css/app.css"],
        {"complete": False, "modules": []}, results(), POLICY, approved=True
    )
    check(incomplete["controls"]["CERT_48"] == "BLOCKED", "incomplete trace must block N/A")
    check(
        incomplete["reasons"]["CERT_48"] == "DEPENDENCY_ANALYSIS_INCOMPLETE",
        "trace blocker should be explicit",
    )


def test_observed_formula_dependency_prevents_not_applicable():
    report = evaluate(
        ["income-analytics/src/income_analytics/application/treasury.py"],
        {
            "complete": True,
            "modules": ["income_analytics.application.magic_formula_stocks"],
        },
        results(),
        POLICY,
        approved=True,
    )
    check(report["controls"]["CERT_48"] == "BLOCKED", "observed dependency must block N/A")
    check(
        report["reasons"]["CERT_48"] == "PROTECTED_DEPENDENCY_OBSERVED",
        "dependency blocker should be explicit",
    )


def test_applicable_financial_failure_stays_fail():
    report = evaluate(
        ["income-analytics/src/income_analytics/application/treasury.py"],
        {"complete": True, "modules": ["income_analytics.application.treasury"]},
        results(CORE_FINANCIAL_REGRESSION="FAIL"),
        POLICY,
        approved=True,
    )
    check(report["controls"]["CORE_FINANCIAL_REGRESSION"] == "FAIL", "financial failure hidden")
    check(report["decision"] == "BLOCKED", "financial failure must block release")


@pytest.mark.parametrize("mandatory", ["SECURITY", "BUILD", "STAGING"])
def test_security_build_and_staging_remain_mandatory(mandatory):
    report = evaluate(
        ["income-analytics/src/income_analytics/api/static/css/app.css"],
        {"complete": True, "modules": []},
        results(**{mandatory: "FAIL"}),
        POLICY,
        approved=True,
    )
    check(report["controls"][mandatory] == "FAIL", f"{mandatory} failure was hidden")
    check(report["decision"] == "BLOCKED", f"{mandatory} must block release")


def test_n_a_cannot_be_supplied_as_result_of_an_applicable_control():
    report = evaluate(
        ["income-analytics/src/income_analytics/application/magic_formula_stocks.py"],
        {"complete": True, "modules": []},
        results(CERT_48="NOT_APPLICABLE"),
        POLICY,
        approved=True,
    )
    check(report["controls"]["CERT_48"] == "BLOCKED", "applicable control cannot be N/A")
    check(
        report["reasons"]["CERT_48"] == "APPLICABLE_CONTROL_RESULT_MISSING_OR_INVALID",
        "invalid applicable state should be explained",
    )


def test_n_a_requires_a_real_exact_policy_approval_record(tmp_path):
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(POLICY), encoding="utf-8")
    digest = policy_digest(policy_path)
    body = f"RELEASE_POLICY_APPROVED {digest}"
    approval = {
        "state": "APPROVED",
        "policy_sha256": digest,
        "approver": "tiagocaldironi",
        "comment_id": 42,
        "comment_url": "https://example.invalid/comment/42",
        "comment_body_sha256": hashlib.sha256(body.encode()).hexdigest(),
    }
    comment = {
        "id": 42,
        "html_url": approval["comment_url"],
        "user": {"login": "tiagocaldironi"},
        "body": body,
    }
    record = {"approval": approval}
    check(valid_policy_approval(policy_path, record, comment), "valid approval record was rejected")
    comment["body"] += " edited"
    check(not valid_policy_approval(policy_path, record, comment), "edited approval was accepted")
    check(
        not valid_policy_approval(policy_path, record, {**comment, "body": body, "id": 43}),
        "wrong comment identity was accepted",
    )


@pytest.mark.parametrize("path", [[], ["income-analytics/README.md"]])
def test_empty_or_unmapped_changes_block(path):
    report = evaluate(
        path,
        {"complete": True, "modules": []},
        results(),
        POLICY,
        approved=True,
    )
    check(report["decision"] == "BLOCKED", "unmapped changes must block")
    check("unknown" in report["scopes"], "unmapped changes should report unknown scope")


def test_release_candidate_workflow_reuses_one_python_run_and_skips_diagnostic_duplicate():
    import yaml

    workflow_root = ROOT.parents[1] / ".github" / "workflows"

    def load_workflow(name):
        loader = yaml.BaseLoader((workflow_root / name).read_text(encoding="utf-8"))
        try:
            return loader.get_single_data()
        finally:
            loader.dispose()

    core = load_workflow("ci-offline.yml")
    diagnostics = load_workflow("ci-diagnostics.yml")
    label = "release-candidate"
    check(
        label in core["jobs"]["release_python"]["if"],
        "release label must trigger evidence job",
    )
    check(
        "release_python" in core["jobs"]["release_scoped"]["needs"],
        "promotion must wait for evidence",
    )
    check(
        "labeled" in core["on"]["pull_request"]["types"],
        "label addition must trigger candidate CI",
    )
    check(
        label in diagnostics["jobs"]["full_python"]["if"],
        "diagnostic duplicate must be skipped",
    )
    check(
        label in diagnostics["jobs"]["financial"]["if"],
        "duplicate financial job must be skipped",
    )
