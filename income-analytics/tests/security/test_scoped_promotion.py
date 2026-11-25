"""Positive/negative promotion policy; synthetic evidence, no production state."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def ci_path(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "ci"))


def evaluate(*arguments, applicability=None):
    from release_scoped_promotion import apply_applicability
    from scoped_promotion import evaluate as decision

    if applicability is None:
        applicability = {"decision": "ELIGIBLE", "controls": {"synthetic": "PASS"}}
    return apply_applicability(decision(*arguments), applicability)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def cases(rows):
    result = [{"class": "tests.example", "name": name, "status": state} for name, state in rows]
    return {
        "cases": result,
        "totals": {
            key: sum(row["status"] == key for row in result)
            for key in ("passed", "failed", "errors", "skipped")
        },
    }


@pytest.fixture
def evidence(tmp_path):
    from test_delivery import validated_staging
    from test_governance import engineering_reports

    inventory = {}
    for i in range(41):
        name = f"file-{i}.txt"
        (tmp_path / name).write_bytes(b"synthetic")
        inventory[name] = hashlib.sha256(b"synthetic").hexdigest()
    (tmp_path / "inventory.json").write_text(json.dumps({"files": inventory}))
    (tmp_path / "ci").mkdir()
    policy = {
        "test_targets": ["tests/example.py"],
        "required_executed_modules": ["income_analytics.feature"],
        "required_executed_functions": ["income_analytics.feature:calculate"],
        "cert48_modules": ["income_analytics.frozen"],
        "immutable_inventory": "inventory.json",
        "historical_baseline_sha": "old",
        "historical_out_of_scope_proposal": {
            "tests/example.py::historical": {
                "baseline_status": "failed",
                "cause": "MISSING",
                "issue": 58,
                "baseline_sha": "old",
            }
        },
    }
    policy_path = tmp_path / "ci/scoped-financial-policy.json"
    policy_path.write_text(json.dumps(policy))
    baseline_dir = tmp_path / "docs/engineering/release-policy-65"
    baseline_dir.mkdir(parents=True)
    baseline_dir.joinpath("candidate_python.json").write_text(
        json.dumps(cases([("historical", "failed"), ("old", "passed")]))
    )
    reports = engineering_reports()
    reports["quality"]["accepted_typing_nonregression"] = {"status": "PASS", "added": []}
    reports["python"] = {
        **cases([("historical", "failed"), ("old", "passed"), ("new", "passed")]),
        "exit_code": 1,
    }
    scoped = {
        "technical_state": "PASS",
        "dependency_calls": ["income_analytics.feature:calculate"],
        "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "cases": cases([("scope", "passed")])["cases"],
        "scoped_totals": cases([("scope", "passed")])["totals"],
        "checkout_sha": "candidate-sha",
        "source_fingerprint": "content-id",
    }
    reports["financial"] = {
        **cases([("historical", "failed")]),
        "exit_code": 1,
        "failure_causes": {"tests/example.py::historical": "MISSING"},
        "scoped_release_assessment": scoped,
    }
    reports["operational"] = {
        "status": "PASS",
        "exit_code": 0,
        "operational_state": "OPERATIONAL_PASS",
        "cases": [
            {"name": f"test_failure_exercise[{i:02d}]", "status": "passed"} for i in range(1, 26)
        ],
        "totals": {"passed": 25, "failed": 0, "errors": 0, "skipped": 0},
        "recovery": {"status": "PASS", "synthetic_rows_lost": 0, "host_rpo_rto_certified": False},
    }
    for name, row in reports.items():
        row.update(
            check=name,
            checkout_sha="candidate-sha",
            source_fingerprint="content-id",
            governance_policy_sha256="policy-id",
            fingerprint_version=2,
            run_id="123",
            pr_head_sha="head",
            worktree_dirty=False,
        )
    security = {**reports["engineering"], "status": "PASS", "artifact_sha256": "a" * 64}
    for control in (
        "source_policy",
        "gitleaks",
        "security_tests",
        "findings_policy",
        "sast",
        "secret_scanning",
        "dependencies",
    ):
        security[control] = {"status": "PASS"}
    security["gitleaks"]["negative_fixture"] = "REJECTED"
    for group, key in [
        ("gitleaks", "untriaged"),
        ("sast", "untriaged"),
        ("secret_scanning", "untriaged"),
        ("dependencies", "alerts"),
        ("source_policy", "forbidden_files"),
        ("findings_policy", "high_critical_unresolved"),
    ]:
        security[group][key] = []
    security["security_tests"].update(cases([("security", "passed")]))
    gate = {
        "engineering_ci": "PASS",
        "consistent_identity": True,
        "promoted_diagnostics": {"ruff": "PASS"},
        "security_baseline": "PASS",
    }
    staging = validated_staging()
    staging["workflow_identity"] = {
        "delivery_run_id": "123",
        "controller_checkout_sha": "candidate-sha",
    }
    staging["candidate"] = {
        "source_commit": "candidate-sha",
        "source_fingerprint": "content-id",
        "governance_policy_identity": "policy-id",
        "build_run_id": 123,
        "package_sha256": "a" * 64,
        "financial_release": "BLOCKED",
        "production_status": "PRODUCTION_NOT_AUTHORIZED",
    }
    body = "OWNER_APPROVED " + "a" * 40
    comment = {"user": {"login": "tiagocaldironi"}, "id": 1, "html_url": "synthetic", "body": body}
    record = {
        "state": "OWNER_APPROVED",
        "owner": "tiagocaldironi",
        "comment_id": 1,
        "comment_url": "synthetic",
        "comment_body_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "approved_sha": "a" * 40,
        "certified_surface_sha256": "surface",
        "merge_authorized": False,
        "production_deploy_authorized": False,
    }
    identity = {
        "checkout_sha": "candidate-sha",
        "source_fingerprint": "content-id",
        "governance_policy_sha256": "policy-id",
        "run_id": "123",
        "pr_head_sha": "head",
        "engineering_job": "success",
        "security_job": "success",
        "staging_job": "success",
    }
    return [
        tmp_path,
        reports,
        security,
        staging,
        gate,
        comment,
        record,
        identity,
        ("surface", "surface"),
    ]


def test_certified_scope_can_go_with_visible_historical_failure(evidence):
    result = evaluate(*evidence)
    assert result["decision"] == "GO", result["blockers"]
    assert result["gates"]["HISTORICAL_DEBT"] == "KNOWN_DEBT_VISIBLE"
    assert result["merge_authorized"] is result["deployment_authorized"] is False
    assert result["historical_test_totals"]["failed"] == 1


@pytest.mark.parametrize(
    "field",
    [
        "checkout_sha",
        "source_fingerprint",
        "governance_policy_sha256",
        "run_id",
        "pr_head_sha",
        "worktree_dirty",
    ],
)
def test_wrong_commit_run_or_dirty_report_blocks(evidence, field):
    evidence[1]["financial"][field] = "different"
    assert evaluate(*evidence)["decision"] == "NO_GO"


@pytest.mark.parametrize("control", ["gitleaks", "sast", "dependencies", "secret_scanning"])
def test_security_is_mandatory(evidence, control):
    evidence[2][control]["status"] = "FAIL"
    assert evaluate(*evidence)["decision"] == "NO_GO"


@pytest.mark.parametrize("field", ["engineering_job", "security_job", "staging_job"])
def test_skipped_cancelled_or_failed_jobs_block(evidence, field):
    evidence[7][field] = "skipped"
    assert evaluate(*evidence)["decision"] == "NO_GO"


def test_frozen_dependency_changed_surface_and_missing_approval_block(evidence):
    changed = deepcopy(evidence)
    changed[1]["financial"]["scoped_release_assessment"]["dependency_calls"].append(
        "income_analytics.frozen:metrics"
    )
    assert evaluate(*changed)["decision"] == "NO_GO"
    evidence[-1] = ("surface", "changed")
    assert evaluate(*evidence)["decision"] == "NO_GO"
    evidence[-1] = ("surface", "surface")
    evidence[5]["body"] = "revoked"
    assert evaluate(*evidence)["decision"] == "NO_GO"


def test_unapproved_or_ineligible_control_applicability_blocks_promotion(evidence):
    result = evaluate(
        *evidence,
        applicability={
            "decision": "BLOCKED",
            "controls": {"CERT_48": "BLOCKED", "SECURITY": "PASS"},
            "reasons": {"CERT_48": "RELEASE_POLICY_APPROVAL_REQUIRED"},
        },
    )
    require(result["decision"] == "NO_GO", "unapproved policy must block promotion")
    require(
        "RELEASE_APPLICABILITY_NOT_APPROVED_OR_NOT_ELIGIBLE" in result["blockers"],
        "policy approval blocker must be reported",
    )
    require(
        result["control_applicability"]["controls"]["CERT_48"] == "BLOCKED",
        "CERT_48 cannot be N/A without policy approval",
    )


def test_new_failure_and_uncertified_dependency_block(evidence):
    evidence[1]["python"].update(
        cases([("historical", "failed"), ("old", "passed"), ("new", "failed")])
    )
    assert evaluate(*evidence)["decision"] == "NO_GO"
    evidence[1]["financial"]["scoped_release_assessment"]["dependency_calls"] = []
    assert evaluate(*evidence)["decision"] == "NO_GO"


@pytest.mark.parametrize("check", ["rollback", "rollback_restore", "health", "backup", "restore"])
def test_missing_operational_or_rollback_evidence_blocks(evidence, check):
    evidence[3]["checks"][check]["status"] = "NOT_RUN"
    assert evaluate(*evidence)["decision"] == "NO_GO"


def test_new_or_missing_test_cannot_be_hidden_as_debt():
    from scoped_promotion import no_test_regressions

    before = cases([("old", "passed")])
    assert not no_test_regressions(before, cases([("old", "skipped")]))
    assert not no_test_regressions(before, cases([("other", "passed")]))
    assert not no_test_regressions(before, cases([("old", "passed"), ("new", "failed")]))


def test_other_author_and_modified_comment_cannot_approve(evidence):
    from scoped_promotion import valid_owner

    record, comment = evidence[6], evidence[5]
    assert valid_owner(record, comment, "surface", "surface")
    comment["user"]["login"] = "someone-else"
    assert not valid_owner(record, comment, "surface", "surface")


def test_applicability_policy_and_evaluator_are_protected_but_approval_record_is_external():
    from scoped_promotion import PROTECTED

    require("ci/release_applicability.py" in PROTECTED, "evaluator must be protected")
    require("ci/release-applicability-policy.json" in PROTECTED, "policy must be protected")
    require("ci/financial_projection.py" in PROTECTED, "financial projection must be protected")
    require("ci/release_scoped_promotion.py" in PROTECTED, "release wrapper must be protected")
    require("ci/governance_controller.py" in PROTECTED, "evidence binder must be protected")
    require(
        "tests/security/test_scoped_promotion.py" in PROTECTED,
        "policy tests must be protected",
    )
    require(
        "ci/release-applicability-approval.json" not in PROTECTED,
        "authenticated external approval metadata must be updateable",
    )


def test_financial_projection_must_share_full_python_run_identity():
    from financial_projection import bind_to_python

    identity = {
        "checkout_sha": "a" * 40,
        "source_fingerprint": "b" * 64,
        "fingerprint_version": 2,
        "governance_policy_sha256": "c" * 64,
        "pr_head_sha": "d" * 40,
        "run_id": "1234",
        "run_attempt": "1",
        "event_sha": "a" * 40,
        "worktree_dirty": False,
    }
    projection = {
        "check": "financial",
        "financial_state": "FINANCIAL_BLOCKED",
        "exit_code": 1,
        "scoped_release_assessment": {
            "checkout_sha": identity["checkout_sha"],
            "source_fingerprint": identity["source_fingerprint"],
        },
    }
    require(
        bind_to_python(projection, {"check": "python", **identity})["check"] == "financial",
        "valid projection should be bound to financial check",
    )
    projection["run_id"] = "different"
    with pytest.raises(ValueError, match="FINANCIAL_PROJECTION_IDENTITY_MISMATCH"):
        bind_to_python(projection, {"check": "python", **identity})


@pytest.mark.parametrize(
    "control,key",
    [
        ("gitleaks", "untriaged"),
        ("sast", "untriaged"),
        ("dependencies", "alerts"),
        ("secret_scanning", "untriaged"),
    ],
)
def test_hidden_findings_cannot_be_approved_by_status_label(evidence, control, key):
    evidence[2][control][key] = ["unreviewed"]
    assert evaluate(*evidence)["decision"] == "NO_GO"


def test_quality_added_findings_and_failed_build_block(evidence):
    changed = deepcopy(evidence)
    changed[1]["quality"]["accepted_typing_nonregression"]["added"] = ["new"]
    assert evaluate(*changed)["decision"] == "NO_GO"
    evidence[1]["build"]["exit_code"] = False
    assert evaluate(*evidence)["decision"] == "NO_GO"


def test_staging_from_other_candidate_or_run_blocks(evidence):
    evidence[3]["workflow_identity"]["delivery_run_id"] = "other"
    assert evaluate(*evidence)["decision"] == "NO_GO"


def test_missing_operational_recovery_blocks(evidence):
    evidence[1]["operational"]["recovery"]["status"] = "FAIL"
    assert evaluate(*evidence)["decision"] == "NO_GO"


@pytest.mark.parametrize(
    "field",
    [
        "approved_sha",
        "comment_id",
        "comment_url",
        "merge_authorized",
        "production_deploy_authorized",
    ],
)
def test_wrong_approval_commit_record_or_extra_authority_blocks(evidence, field):
    evidence[6][field] = True if field.endswith("authorized") else "changed"
    assert evaluate(*evidence)["decision"] == "NO_GO"

APP_ROOT = Path(__file__).resolve().parents[3] / "income-analytics" / "ci"
POLICY_PATH = APP_ROOT / "release-applicability-policy.json"
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def evaluate_scope(*args, **kwargs):
    from release_applicability import evaluate

    return evaluate(*args, **kwargs)


def release_policy_digest(path):
    from release_applicability import policy_digest

    return policy_digest(path)


def release_valid_policy_approval(policy_path, record, comment):
    from release_applicability import valid_policy_approval

    return valid_policy_approval(policy_path, record, comment)


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
    report = evaluate_scope(
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
    report = evaluate_scope(
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
    report = evaluate_scope(
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
    report = evaluate_scope(
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
    unknown = evaluate_scope(
        ["income-analytics/src/income_analytics/application/new_module.py"],
        {"complete": True, "modules": []}, results(), POLICY, approved=True
    )
    check(unknown["scopes"] == ["unknown"], "unmapped paths must remain unknown")
    check(
        all(unknown["controls"][name] == "BLOCKED" for name in POLICY["controls"]),
        "unknown scope must block each financial control",
    )
    check(unknown["decision"] == "BLOCKED", "unknown scope must block release")

    incomplete = evaluate_scope(
        ["income-analytics/src/income_analytics/api/static/css/app.css"],
        {"complete": False, "modules": []}, results(), POLICY, approved=True
    )
    check(incomplete["controls"]["CERT_48"] == "BLOCKED", "incomplete trace must block N/A")
    check(
        incomplete["reasons"]["CERT_48"] == "DEPENDENCY_ANALYSIS_INCOMPLETE",
        "trace blocker should be explicit",
    )

    malformed = evaluate_scope(
        ["income-analytics/src/income_analytics/api/static/css/app.css"],
        {"complete": True, "modules": [None]},
        results(),
        POLICY,
        approved=True,
    )
    check(malformed["controls"]["CERT_48"] == "BLOCKED", "malformed trace must block N/A")
    check(
        malformed["reasons"]["CERT_48"] == "DEPENDENCY_ANALYSIS_INCOMPLETE",
        "malformed dependency trace should be explicit",
    )


def test_observed_formula_dependency_prevents_not_applicable():
    report = evaluate_scope(
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
    report = evaluate_scope(
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
    report = evaluate_scope(
        ["income-analytics/src/income_analytics/api/static/css/app.css"],
        {"complete": True, "modules": []},
        results(**{mandatory: "FAIL"}),
        POLICY,
        approved=True,
    )
    check(report["controls"][mandatory] == "FAIL", f"{mandatory} failure was hidden")
    check(report["decision"] == "BLOCKED", f"{mandatory} must block release")


def test_n_a_cannot_be_supplied_as_result_of_an_applicable_control():
    report = evaluate_scope(
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
    digest = release_policy_digest(policy_path)
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
    check(
        release_valid_policy_approval(policy_path, record, comment),
        "valid approval record was rejected",
    )
    comment["body"] += " edited"
    check(
        not release_valid_policy_approval(policy_path, record, comment),
        "edited approval was accepted",
    )
    check(
        not release_valid_policy_approval(policy_path, record, {**comment, "body": body, "id": 43}),
        "wrong comment identity was accepted",
    )


@pytest.mark.parametrize("path", [[], ["income-analytics/README.md"]])
def test_empty_or_unmapped_changes_block(path):
    report = evaluate_scope(
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

    workflow_root = APP_ROOT.parents[1] / ".github" / "workflows"

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
