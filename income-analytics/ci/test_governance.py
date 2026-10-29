"""Governance regression tests; induced failures live only in temporary files."""

import json
import os
import subprocess
import sys
from copy import deepcopy

import pipeline_identity
import pytest
import yaml
from gate_policy import (
    GROUPS,
    ROOT,
    compare_diagnostics,
    normalized_message,
    summarize_reports,
    test_scope,
)
from governance import parse_mypy_output


def diagnostic(**changes):
    return {
        "tool": "mypy",
        "file": "src/example.py",
        "line": 2,
        "column": None,
        "code": "arg-type",
        "message": "Incompatible argument",
        **changes,
    }


def test_existing_debt_is_visible_and_unchanged_is_allowed():
    result = compare_diagnostics([diagnostic()], [diagnostic()])
    assert result["status"] == "PASS" and result["current_debt"] == 1


@pytest.mark.parametrize(
    "change",
    [
        {"file": "src/new.py"},
        {"line": 3},
        {"column": 4},
        {"code": "operator"},
        {"message": "Different error"},
        {"tool": "ruff"},
    ],
)
def test_new_identity_cannot_be_compensated_by_old_error_removal(change):
    result = compare_diagnostics([diagnostic(**change)], [diagnostic()])
    assert result["status"] == "FAIL"
    assert len(result["added"]) == len(result["removed"]) == 1


def test_increased_multiplicity_fails_even_with_identical_location():
    assert compare_diagnostics([diagnostic(), diagnostic()], [diagnostic()])["status"] == "FAIL"


def test_removing_debt_is_allowed_without_refreshing_baseline():
    assert compare_diagnostics([], [diagnostic()])["status"] == "PASS"


def test_historical_and_frozen_cases_are_explicit_and_distinct():
    historical = GROUPS["historical_reference_tests"]
    frozen = GROUPS["frozen_integrity_tests"]
    assert len(historical) == len(set(historical)) == 22
    assert len(frozen) == len(set(frozen)) == 2
    for nodeid in historical + frozen:
        entry = test_scope(nodeid)
        assert entry["financial"] and not entry["engineering"]
    assert all(test_scope(nodeid)["hermetic_capable"] for nodeid in frozen)


def test_unrecognized_new_test_remains_in_engineering():
    assert test_scope("tests/test_new_regression.py::test_new")["engineering"]


def test_external_scope_requires_documented_real_dependency():
    for file in GROUPS["external_modules"]:
        entry = test_scope(file + "::test_case")
        assert entry["category"] == "external_integration" and entry["exclusion_reason"]


def engineering_reports():
    reports = {
        name: {
            "checkout_sha": "candidate-sha",
            "source_fingerprint": "content-id",
            "exit_code": 0,
            "fingerprint_version": 2,
            "governance_policy_sha256": "policy-id",
        }
        for name in ("runtime", "engineering", "node", "quality", "build")
    }
    reports["build"].update(
        status="PASS", reproducibility="PASS", manifest="PASS", independent_builds=2,
        artifact_sha256="a" * 64,
        installation={
            **{key: "PASS" for key in (
                "status", "installation", "migrations_temporary_sqlite", "backend_import",
                "startup_health", "static_files", "cleanup",
            )},
            "external_network": "DENIED", "production_access": False,
        },
    )
    return reports


def test_engineering_pass_never_authorizes_financial_release_or_deploy():
    reports = engineering_reports()
    reports["financial"] = {
        "status": "BLOCKED",
        "exit_code": 1,
        "blockers": ["CERT_48"],
        "checkout_sha": "candidate-sha",
        "source_fingerprint": "content-id",
        "fingerprint_version": 2,
        "governance_policy_sha256": "policy-id",
    }
    result = summarize_reports(reports)
    assert result["engineering_ci"] == "PASS"
    assert result["financial_certification"] == result["release_readiness"] == "BLOCKED"
    assert result["deployment_authorization"] == "NOT_IMPLEMENTED"
    assert result["deployment_authorized"] is False


@pytest.mark.parametrize("check", ["runtime", "engineering", "node", "quality", "build"])
def test_missing_or_failed_required_check_blocks_engineering(check):
    reports = engineering_reports()
    failed = deepcopy(reports)
    failed[check]["exit_code"] = 1
    assert summarize_reports(failed)["engineering_ci"] == "FAIL"
    del reports[check]
    assert summarize_reports(reports)["engineering_ci"] == "FAIL"


def test_mixed_commit_or_source_reports_cannot_approve():
    reports = engineering_reports()
    reports["node"]["source_fingerprint"] = "different"
    assert summarize_reports(reports)["engineering_ci"] == "FAIL"


def test_normalization_removes_personal_absolute_paths_without_hiding_error():
    message = normalized_message("Missing member in C:\\Users\\Private\\file.py")
    assert "Private" not in message and "Missing member" in message


def test_controlled_temporary_pytest_regression_fails_engineering_selection(tmp_path):
    source = tmp_path / "test_induced.py"
    source.write_text("def test_induced_regression():\n    assert False\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "gate_plugin",
            "--ci-gate=engineering",
            str(source),
            "-q",
            "--tb=no",
        ],
        env={key: value for key, value in os.environ.items() if key != "CI_TEST_INVENTORY"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1 and "1 failed" in result.stdout
    reports = engineering_reports()
    reports["engineering"]["exit_code"] = result.returncode
    assert summarize_reports(reports)["engineering_ci"] == "FAIL"
    assert "test_induced" not in json.dumps(GROUPS)


def test_workflow_preserves_read_only_untrusted_pr_boundary():
    text = (ROOT.parent / ".github/workflows/ci-offline.yml").read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request_target" not in workflow["on"]
    assert "secrets." not in text and "continue-on-error" not in text
    assert "persist-credentials: false" in text
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            if "uses" in step:
                action, revision = step["uses"].split("@")
                assert action.startswith("actions/") and len(revision) == 40
    assert workflow["jobs"]["engineering_gate"]["if"] == "always()"


@pytest.mark.parametrize("suffix", ["py", "pyi"])
def test_mypy_parser_includes_source_and_stub_errors(suffix):
    findings = parse_mypy_output(
        f"src/types.{suffix}:7: error: Incompatible assignment  [assignment]\n"
        "Found 1 error in 1 file (checked 1 source file)\n"
    )
    assert len(findings) == 1
    assert findings[0]["file"] == f"src/types.{suffix}"
    assert findings[0]["code"] == "assignment"


@pytest.mark.parametrize(
    "unknown",
    [
        "error: unexpected diagnostic format",
        "src/config.txt:8: error: Unsupported input",
    ],
)
def test_mypy_partial_parse_fails_instead_of_approving_old_debt(unknown):
    with pytest.raises(ValueError, match="UNPARSED_MYPY_DIAGNOSTIC"):
        parse_mypy_output("src/a.py:2: error: Existing error  [arg-type]\n" + unknown)


def test_mypy_summary_must_match_all_parsed_diagnostics():
    with pytest.raises(ValueError, match="MYPY_DIAGNOSTIC_COUNT_MISMATCH"):
        parse_mypy_output(
            "src/a.py:2: error: Existing error  [arg-type]\n"
            "Found 2 errors in 1 file (checked 1 source file)\n"
        )


@pytest.fixture
def policy_tree(tmp_path, monkeypatch):
    """Temporary unit inputs, never a replacement for remote/financial evidence."""
    root = tmp_path / "income-analytics"
    root.mkdir()
    for file in pipeline_identity.POLICY_FILES:
        target = tmp_path / file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("unit-policy-content\n", encoding="utf-8")
    monkeypatch.setattr(pipeline_identity.subprocess, "check_output", lambda *a, **k: "")
    return root


@pytest.mark.parametrize("file", pipeline_identity.POLICY_FILES)
def test_each_governance_file_changes_both_identities(policy_tree, file):
    before_policy = pipeline_identity.governance_policy_identity(policy_tree)
    before_execution = pipeline_identity.execution_fingerprint(policy_tree)
    (policy_tree.parent / file).write_text("changed-unit-input\n", encoding="utf-8")
    assert pipeline_identity.governance_policy_identity(policy_tree) != before_policy
    assert pipeline_identity.execution_fingerprint(policy_tree) != before_execution


def test_missing_governance_test_is_fatal_before_check_execution(policy_tree):
    missing = policy_tree / "ci/test_pr52_governance.py"
    missing.unlink()
    with pytest.raises(FileNotFoundError):
        pipeline_identity.governance_policy_identity(policy_tree)
    with pytest.raises(FileNotFoundError):
        pipeline_identity.execution_fingerprint(policy_tree)


@pytest.mark.parametrize(
    "field,value",
    [
        ("governance_policy_sha256", "other-policy"),
        ("fingerprint_version", 1),
        ("governance_policy_sha256", None),
    ],
)
def test_inconsistent_or_legacy_policy_identity_cannot_approve(field, value):
    reports = engineering_reports()
    reports["node"][field] = value
    assert summarize_reports(reports)["engineering_ci"] == "FAIL"


def test_pr52_tests_are_explicit_inputs_to_the_actual_python_command(monkeypatch, tmp_path):
    import governance

    class StopBeforeExecution(Exception):
        pass

    def capture(args, *unused):
        assert "tests" in args
        assert "ci/test_ci.py" in args
        assert "ci/test_governance.py" in args
        assert "ci/test_pr52_governance.py" in args
        assert "--ci-gate=engineering" in args
        raise StopBeforeExecution

    monkeypatch.setattr(governance.legacy, "execute", capture)
    with pytest.raises(StopBeforeExecution):
        governance.python_check("engineering", {}, tmp_path, tmp_path)
