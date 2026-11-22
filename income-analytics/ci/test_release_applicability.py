"""Synthetic controls for scope-aware release applicability."""

import hashlib
import json
from pathlib import Path

import pytest
from release_applicability import evaluate, policy_digest, valid_policy_approval

ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "release-applicability-policy.json"
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))


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
    assert report["scopes"] == ["visual_only"]
    for control in (
        "CERT_48",
        "IDENTITY_PROVENANCE_UNAPPROVED",
        "22_HISTORICAL_REFERENCES_UNAPPROVED",
        "CORE_FINANCIAL_REGRESSION",
    ):
        assert report["controls"][control] == "NOT_APPLICABLE"
    assert report["decision"] == "ELIGIBLE"
    assert report["deployment_authorized"] is False


def test_core_financial_change_requires_core_tests_and_proves_formula_independence():
    report = evaluate(
        ["income-analytics/src/income_analytics/application/treasury.py"],
        {"complete": True, "modules": ["income_analytics.application.treasury"]},
        results(),
        POLICY,
        approved=True,
    )
    assert report["controls"]["CORE_FINANCIAL_REGRESSION"] == "PASS"
    assert report["controls"]["CERT_48"] == "NOT_APPLICABLE"
    assert report["decision"] == "ELIGIBLE"


def test_not_applicable_is_blocked_until_explicit_policy_approval():
    report = evaluate(
        ["income-analytics/src/income_analytics/api/static/css/app.css"],
        {"complete": True, "modules": []},
        results(),
        POLICY,
        approved=False,
    )
    assert report["decision"] == "BLOCKED"
    assert report["controls"]["CERT_48"] == "BLOCKED"
    assert report["reasons"]["CERT_48"] == "RELEASE_POLICY_APPROVAL_REQUIRED"


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
        assert report["controls"][control] == "BLOCKED"
    assert report["decision"] == "BLOCKED"


def test_unknown_paths_and_missing_dependency_trace_fail_closed():
    unknown = evaluate(
        ["income-analytics/src/income_analytics/application/new_module.py"],
        {"complete": True, "modules": []}, results(), POLICY, approved=True
    )
    assert unknown["scopes"] == ["unknown"]
    assert all(
        unknown["controls"][name] == "BLOCKED"
        for name in POLICY["controls"]
    )
    assert unknown["decision"] == "BLOCKED"

    incomplete = evaluate(
        ["income-analytics/src/income_analytics/api/static/css/app.css"],
        {"complete": False, "modules": []}, results(), POLICY, approved=True
    )
    assert incomplete["controls"]["CERT_48"] == "BLOCKED"
    assert incomplete["reasons"]["CERT_48"] == "DEPENDENCY_ANALYSIS_INCOMPLETE"


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
    assert report["controls"]["CERT_48"] == "BLOCKED"
    assert report["reasons"]["CERT_48"] == "PROTECTED_DEPENDENCY_OBSERVED"


def test_applicable_financial_failure_stays_fail():
    report = evaluate(
        ["income-analytics/src/income_analytics/application/treasury.py"],
        {"complete": True, "modules": ["income_analytics.application.treasury"]},
        results(CORE_FINANCIAL_REGRESSION="FAIL"),
        POLICY,
        approved=True,
    )
    assert report["controls"]["CORE_FINANCIAL_REGRESSION"] == "FAIL"
    assert report["decision"] == "BLOCKED"


@pytest.mark.parametrize("mandatory", ["SECURITY", "BUILD", "STAGING"])
def test_security_build_and_staging_remain_mandatory(mandatory):
    report = evaluate(
        ["income-analytics/src/income_analytics/api/static/css/app.css"],
        {"complete": True, "modules": []},
        results(**{mandatory: "FAIL"}),
        POLICY,
        approved=True,
    )
    assert report["controls"][mandatory] == "FAIL"
    assert report["decision"] == "BLOCKED"


def test_n_a_cannot_be_supplied_as_result_of_an_applicable_control():
    report = evaluate(
        ["income-analytics/src/income_analytics/application/magic_formula_stocks.py"],
        {"complete": True, "modules": []},
        results(CERT_48="NOT_APPLICABLE"),
        POLICY,
        approved=True,
    )
    assert report["controls"]["CERT_48"] == "BLOCKED"
    assert report["reasons"]["CERT_48"] == "APPLICABLE_CONTROL_RESULT_MISSING_OR_INVALID"


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
    assert valid_policy_approval(policy_path, record, comment)
    comment["body"] += " edited"
    assert not valid_policy_approval(policy_path, record, comment)
    assert not valid_policy_approval(policy_path, record, {**comment, "body": body, "id": 43})


@pytest.mark.parametrize("path", [[], ["income-analytics/README.md"]])
def test_empty_or_unmapped_changes_block(path):
    report = evaluate(
        path,
        {"complete": True, "modules": []},
        results(),
        POLICY,
        approved=True,
    )
    assert report["decision"] == "BLOCKED"
    assert "unknown" in report["scopes"]
