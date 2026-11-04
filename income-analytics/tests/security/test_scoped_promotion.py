"""Positive/negative promotion policy; synthetic evidence, no production state."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def ci_path(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "ci"))


def evaluate(*arguments):
    from scoped_promotion import evaluate as decision

    return decision(*arguments)


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
