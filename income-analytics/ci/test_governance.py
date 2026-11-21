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


@pytest.mark.parametrize(
    "file",
    [
        "tests/api/test_treasury.py",
        "tests/application/test_treasury.py",
        "tests/infrastructure/test_treasury_revisions.py",
        "tests/application/test_executable_contribution.py",
        "tests/application/test_global_contribution_allocator.py",
        "tests/api/test_b3_import_contract.py",
    ],
)
def test_treasury_and_allocation_scopes_are_financial_and_remain_engineering(file):
    scope = test_scope(file + "::test_scope_probe")
    assert scope["financial"] is True
    assert scope["engineering"] is True
    assert scope["financial_critical"] is True


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
        status="PASS",
        reproducibility="PASS",
        manifest="PASS",
        independent_builds=2,
        artifact_sha256="a" * 64,
        installation={
            **{
                key: "PASS"
                for key in (
                    "status",
                    "installation",
                    "migrations_temporary_sqlite",
                    "backend_import",
                    "startup_health",
                    "static_files",
                    "cleanup",
                )
            },
            "external_network": "DENIED",
            "production_access": False,
        },
    )
    return reports


@pytest.mark.parametrize("check", ["runtime", "engineering", "node", "quality", "build"])
@pytest.mark.parametrize("invalid_exit", [False, 0.0, "0", None])
def test_malformed_exit_code_cannot_approve_engineering(check, invalid_exit):
    reports = engineering_reports()
    reports[check]["exit_code"] = invalid_exit
    assert summarize_reports(reports)["engineering_ci"] == "FAIL"


@pytest.mark.parametrize("invalid_exit", [False, 0.0, "0", None])
def test_malformed_exit_code_cannot_approve_financial_certification(invalid_exit):
    reports = engineering_reports()
    reports["financial"] = {
        **reports["engineering"],
        "status": "PASS",
        "blockers": [],
        "exit_code": invalid_exit,
    }
    result = summarize_reports(reports)
    assert result["financial_certification"] == "BLOCKED"
    assert result["release_readiness"] == "BLOCKED"
    assert result["deployment_authorized"] is False


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


def test_magic_formula_check_routes_to_python_gate(monkeypatch, tmp_path):
    import governance

    class StopBeforeExecution(Exception):
        pass

    def capture(args, *unused):
        assert "--ci-gate=magic_formula" in args
        raise StopBeforeExecution

    monkeypatch.setattr(governance.legacy, "execute", capture)
    with pytest.raises(StopBeforeExecution):
        governance.run_check("magic_formula", {}, tmp_path, tmp_path)


class TestModuleGateGovernance(__import__('unittest').TestCase):
    def test_financial_and_full_python_diagnostics_are_separate_from_core_workflow(self):
        workflow = yaml.safe_load((ROOT.parent / ".github/workflows/ci-offline.yml").read_text())
        matrix = workflow["jobs"]["python"]["strategy"]["matrix"]["include"]
        checks = {item["check"] for item in matrix}
        self.assertTrue({"runtime", "engineering", "magic_formula"}.issubset(checks))
        self.assertTrue({"financial", "python", "ruff", "mypy", "quality"}.isdisjoint(checks))
        self.assertEqual(workflow["jobs"]["quality"]["needs"], ["ruff", "mypy"])
        diagnostics_path = ROOT.parent / ".github/workflows/ci-diagnostics.yml"
        diagnostics = yaml.safe_load(diagnostics_path.read_text())
        self.assertEqual(diagnostics["env"]["GIT_CONFIG_VALUE_0"], "false")
        self.assertEqual(diagnostics["jobs"]["full_python"]["name"], "CI / Full Python diagnostic")
        self.assertEqual(diagnostics["jobs"]["financial"]["name"], "CI / Financial certification")
        self.assertIn("[69,79,81]", diagnostics["jobs"]["financial"]["if"])
        self.assertEqual(
            workflow["jobs"]["financial_scoped"]["name"], "CI / Financial certification"
        )
        self.assertIn("financial_scoped", workflow["jobs"]["release_scoped"]["needs"])

    def test_baseline_a_pin_preserves_original_provenance_and_hashes(self):
        pin = json.loads((ROOT / "ci/baseline-a.json").read_text())
        self.assertEqual(pin["original_run_id"], 40856571402)
        self.assertEqual(pin["source_commit"], "cc71b0be65d6fe34b97cd3305dfc7956c9a4a065")
        self.assertEqual(
            pin["package_sha256"],
            "5fe747f55179b82e166761cd7c8adca0a643123bc809086c716e19ee0ddd38b2",
        )
        self.assertEqual(
            pin["manifest_sha256"],
            "008b349f9a2f17332292fdf0cad2fd690a5d00ef21a37e8f7e0124ce367cee04",
        )

    def test_magic_formula_gate_excludes_historical_cases_but_full_keeps_them(self):
        from gate_plugin import selected_for_gate

        historical = {
            "ownership": "magic_formula",
            "category": "historical_certification",
            "financial": True,
        }
        hermetic = {
            "ownership": "magic_formula",
            "category": "hermetic_integration",
            "financial": False,
        }
        self.assertFalse(selected_for_gate("magic_formula", historical))
        self.assertTrue(selected_for_gate("full", historical))
        self.assertTrue(selected_for_gate("financial", historical))
        self.assertTrue(selected_for_gate("magic_formula", hermetic))

    def test_magic_formula_test_ownership_is_explicit(self):
        from module_impact import classify_path

        for path in (
            'src/income_analytics/application/magic_formula_stocks.py',
            'tests/application/test_magic_formula_ranking_engine.py',
        ):
            self.assertEqual(classify_path(path), 'magic_formula')
            self.assertFalse(test_scope(path + '::test_case')['engineering'])

    def test_shared_and_unknown_paths_fail_closed(self):
        from module_impact import classify_changes, classify_path

        paths = (
            'src/income_analytics/api/routers/dashboard.py',
            'src/income_analytics/infrastructure/b3_cotahist_market_data.py',
            'alembic/versions/0015_magic_formula_fundamentals_snapshots.py',
            'ci/new_policy.py',
            'docs/new_file.md',
        )
        for path in paths:
            self.assertEqual(classify_path(path), 'shared')
            self.assertEqual(classify_changes([path]), {'shared'})

    def test_core_paths_are_core_owned(self):
        from module_impact import classify_changes, classify_path

        path = 'src/income_analytics/application/treasury.py'
        self.assertEqual(classify_path(path), 'core')
        self.assertEqual(classify_changes([path]), {'core'})

    def test_engineering_decision_requires_domain_and_shared_gates(self):
        from module_impact import engineering_decision

        matrix = (
            ({'core'}, True, False, True, True),
            ({'core'}, False, False, True, False),
            ({'magic_formula'}, False, True, True, True),
            ({'magic_formula'}, False, False, True, False),
            ({'shared'}, True, False, True, False),
            ({'shared'}, True, True, True, True),
        )
        for scopes, core, magic, shared, expected in matrix:
            self.assertEqual(
                engineering_decision(
                    scopes,
                    core_pass=core,
                    magic_formula_pass=magic,
                    shared_pass=shared,
                    security_pass=True,
                    build_pass=True,
                ),
                expected,
            )

    def test_security_and_build_fail_every_scope(self):
        from module_impact import engineering_decision

        for scopes in ({'core'}, {'magic_formula'}, {'shared'}):
            for security, build in ((False, True), (True, False)):
                self.assertFalse(
                    engineering_decision(
                        scopes,
                        core_pass=True,
                        magic_formula_pass=True,
                        shared_pass=True,
                        security_pass=security,
                        build_pass=build,
                    )
                )

    def test_core_gate_ignores_magic_formula_before_test_import(self):
        import gate_plugin

        class Config:
            @staticmethod
            def getoption(name):
                return 'engineering' if name == '--ci-gate' else None

        fm_test = ROOT / 'tests/application/test_magic_formula_canonical_ranking.py'
        core_test = ROOT / 'tests/application/test_treasury.py'
        self.assertTrue(gate_plugin.pytest_ignore_collect(fm_test, Config()))
        self.assertFalse(gate_plugin.pytest_ignore_collect(core_test, Config()))

    def test_core_scope_does_not_require_historical_magic_formula_gate(self):
        reports = engineering_reports()
        result = summarize_reports(reports, scopes={'core'})
        self.assertEqual(result['engineering_ci'], 'PASS')
        self.assertEqual(result['magic_formula_gate'], 'NOT_REQUIRED')

    def test_magic_formula_and_shared_scopes_require_module_gate(self):
        for scopes in ({'magic_formula'}, {'shared'}):
            reports = engineering_reports()
            self.assertEqual(summarize_reports(reports, scopes=scopes)['engineering_ci'], 'FAIL')
            reports['magic_formula'] = {'status': 'PASS', 'exit_code': 0}
            self.assertEqual(summarize_reports(reports, scopes=scopes)['engineering_ci'], 'PASS')

    def test_shared_security_build_and_core_failures_still_block(self):
        reports = engineering_reports()
        reports['magic_formula'] = {'status': 'PASS', 'exit_code': 0}
        self.assertEqual(summarize_reports(reports, scopes={'shared'})['engineering_ci'], 'PASS')
        reports['engineering']['exit_code'] = 1
        self.assertEqual(summarize_reports(reports, scopes={'shared'})['engineering_ci'], 'FAIL')


def test_junit_nodeid_normalizes_function_class_method_and_parameterized_cases():
    from governance import _junit_nodeid

    expected = (
        (_junit_nodeid("ci.test_governance", "test_simple"), "ci/test_governance.py::test_simple"),
        (
            _junit_nodeid("ci.test_governance.TestModuleGateGovernance", "test_case"),
            "ci/test_governance.py::TestModuleGateGovernance::test_case",
        ),
        (
            _junit_nodeid("ci.test_governance", "test_parameterized[value]"),
            "ci/test_governance.py::test_parameterized[value]",
        ),
    )
    if any(actual != wanted for actual, wanted in expected):
        raise AssertionError(f"JUnit IDs were normalized incorrectly: {expected}")


def test_junit_inventory_match_rejects_duplicate_inventory_ids():
    from governance import _match_junit_inventory

    case = {"class": "ci.test_governance", "name": "test_case", "status": "passed"}
    result, error = _match_junit_inventory(
        ["ci/test_governance.py::test_case"] * 2, [case]
    )
    if result or error != "INVENTORY_ID_DUPLICATE":
        raise AssertionError(f"Duplicate inventory ID was accepted: {result}, {error}")


def test_junit_inventory_match_rejects_duplicate_junit_ids():
    from governance import _match_junit_inventory

    nodeid = "ci/test_governance.py::test_case"
    case = {"class": "ci.test_governance", "name": "test_case", "status": "passed"}
    result, error = _match_junit_inventory([nodeid], [case, case])
    if result or error != "JUNIT_ID_DUPLICATE":
        raise AssertionError(f"Duplicate JUnit ID was accepted: {result}, {error}")


def test_junit_inventory_match_rejects_missing_junit_case():
    from governance import _match_junit_inventory

    result, error = _match_junit_inventory(["ci/test_governance.py::test_missing"], [])
    if result or error != "JUNIT_CASE_MISSING":
        raise AssertionError(f"Missing JUnit case was accepted: {result}, {error}")


def test_junit_inventory_match_rejects_unexpected_junit_case():
    from governance import _match_junit_inventory

    case = {"class": "ci.test_governance", "name": "test_extra", "status": "passed"}
    result, error = _match_junit_inventory([], [case])
    if result or error != "JUNIT_CASE_UNEXPECTED":
        raise AssertionError(f"Unexpected JUnit case was accepted: {result}, {error}")


def test_junit_inventory_match_rejects_malformed_inventory_and_junit_ids():
    from governance import _match_junit_inventory

    inventory_result, inventory_error = _match_junit_inventory(["ci/test_governance.py::"], [])
    malformed_case = {"class": "ci..test_governance", "name": "test_case", "status": "passed"}
    junit_result, junit_error = _match_junit_inventory(
        ["ci/test_governance.py::test_case"], [malformed_case]
    )
    if inventory_result or inventory_error != "INVENTORY_ID_MALFORMED":
        raise AssertionError(
            f"Malformed inventory ID was accepted: {inventory_result}, {inventory_error}"
        )
    if junit_result or junit_error != "JUNIT_ID_MALFORMED":
        raise AssertionError(f"Malformed JUnit ID was accepted: {junit_result}, {junit_error}")


def test_junit_inventory_match_preserves_status_for_a_valid_case():
    from governance import _match_junit_inventory

    nodeid = "ci/test_governance.py::TestModuleGateGovernance::test_case"
    case = {
        "class": "ci.test_governance.TestModuleGateGovernance",
        "name": "test_case",
        "status": "passed",
    }
    result, error = _match_junit_inventory([nodeid], [case])
    if result != {nodeid: "passed"} or error is not None:
        raise AssertionError(f"Valid JUnit result was not preserved: {result}, {error}")
