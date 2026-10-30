"""Negative controls for occurrence accounting and promoted diagnostics."""

import hashlib
import importlib.metadata
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace

import pytest
from engineering_debt import (
    classify_ruff,
    reconciled_findings,
    require_clean_diagnostics,
    ruff_exception_findings,
)
from gate_policy import compare_diagnostics


def sample():
    before = dict(tool="mypy", file="src/a.py", line=4, column=None, code="type-arg", message="M")
    ledger = {
        "reviewed_source_sha256": {},
        "occurrences": [
            dict(id="one", before=before, after=before, status="OPEN", evidence="review")
        ],
    }
    return before, ledger


def test_remaining_occurrence_and_multiplicity_are_not_waived(tmp_path):
    before, ledger = sample()
    expected = reconciled_findings([before], ledger, tmp_path)
    assert compare_diagnostics([before], expected)["status"] == "PASS"
    assert compare_diagnostics([before, before], expected)["status"] == "FAIL"


def test_resolved_occurrence_cannot_be_reintroduced(tmp_path):
    before, ledger = sample()
    ledger["occurrences"][0].update(after=None, status="RESOLVED")
    assert (
        compare_diagnostics([before], reconciled_findings([before], ledger, tmp_path))["status"]
        == "FAIL"
    )


def test_duplicate_ids_cannot_obscure_distinct_original_occurrences(tmp_path):
    before, ledger = sample()
    other = dict(before, line=8)
    ledger["occurrences"].append(
        dict(id="one", before=other, after=other, status="OPEN", evidence="review")
    )
    with pytest.raises(ValueError, match="DEBT_LEDGER_DUPLICATE_ID"):
        reconciled_findings([before, other], ledger, tmp_path)


def test_ledger_cannot_read_paths_outside_checkout(tmp_path):
    before, ledger = sample()
    ledger["reviewed_source_sha256"] = {"../outside.py": "0" * 64}
    with pytest.raises(ValueError, match="DEBT_LEDGER_PATH_ESCAPE"):
        reconciled_findings([before], ledger, tmp_path)


def test_onboarding_missing_row_fails_before_financial_facts_are_read(monkeypatch):
    from income_analytics.api import onboarding_v2

    class MissingRow:
        def execute(self, statement):
            pass

        def get(self, model, key):
            return None

    @contextmanager
    def begin():
        yield MissingRow()

    def forbidden_facts(*args):
        pytest.fail("Financial facts must not be consulted after a failed onboarding invariant")

    monkeypatch.setattr(onboarding_v2, "SessionFactory", SimpleNamespace(begin=begin))
    monkeypatch.setattr(onboarding_v2, "facts", forbidden_facts)
    with pytest.raises(AssertionError, match="Onboarding insert did not persist its journey"):
        onboarding_v2.update("local", "wallet", "Wallet", None, SimpleNamespace(action="START"))


@pytest.mark.parametrize("mutation", ["omit", "duplicate", "message", "evidence", "status", "hash"])
def test_invalid_ledger_fails_closed(tmp_path, mutation):
    before, ledger = sample()
    if mutation == "omit":
        ledger["occurrences"] = []
    elif mutation == "duplicate":
        ledger["occurrences"] *= 2
    elif mutation == "hash":
        (tmp_path / "a.py").write_text("changed", encoding="utf-8")
        ledger["reviewed_source_sha256"] = {"a.py": "0" * 64}
    else:
        row = ledger["occurrences"][0]
        row["after"] = dict(row["after"])
        if mutation == "message":
            row["after"]["message"] = "different"
        else:
            row[mutation] = ""
    with pytest.raises(ValueError):
        reconciled_findings([before], ledger, tmp_path)


def clean_reports():
    identity = dict(
        checkout_sha="sha",
        source_fingerprint="source",
        governance_policy_sha256="policy",
        fingerprint_version=2,
        run_id="run",
        run_attempt="1",
    )
    return {
        "engineering": dict(identity),
        "ruff": dict(
            identity,
            check="ruff",
            status="PASS",
            exit_code=0,
            findings=[],
            raw_tool_exit_code=0,
            justified_findings=[],
            unjustified_findings=[],
            missing_approved_observations=[],
        ),
    }


def test_clean_ruff_is_mandatory_without_promoting_unresolved_checks():
    result = require_clean_diagnostics({"engineering_ci": "PASS"}, clean_reports())
    assert result["engineering_ci"] == "PASS"
    assert result["unpromoted_diagnostics"] == ["mypy", "python"]


@pytest.mark.parametrize(
    "failure",
    [
        "missing",
        "failed",
        "cancelled",
        "skipped",
        "no-evidence",
        "findings",
        "mixed-sha",
        "mixed-policy",
        "mixed-source",
        "missing-exit",
        "wrong-check",
        "existing-failure",
        "boolean-exit",
        "mixed-run",
        "mixed-attempt",
    ],
)
def test_promoted_check_never_approves_silently(failure):
    reports = deepcopy(clean_reports())
    summary = {"engineering_ci": "PASS"}
    if failure == "missing":
        del reports["ruff"]
    elif failure == "existing-failure":
        summary["engineering_ci"] = "FAIL"
    else:
        row = reports["ruff"]
        if failure == "failed":
            row["exit_code"] = 1
        elif failure in {"cancelled", "skipped"}:
            row["status"] = failure.upper()
        elif failure == "no-evidence":
            del row["findings"]
        elif failure == "findings":
            row["findings"] = [{"code": "E501"}]
        elif failure == "missing-exit":
            del row["exit_code"]
        elif failure == "wrong-check":
            row["check"] = "mypy"
        elif failure == "boolean-exit":
            row["exit_code"] = False
        else:
            row[
                {
                    "mixed-sha": "checkout_sha",
                    "mixed-policy": "governance_policy_sha256",
                    "mixed-source": "source_fingerprint",
                    "mixed-run": "run_id",
                    "mixed-attempt": "run_attempt",
                }[failure]
            ] = "different"
    assert require_clean_diagnostics(summary, reports)["engineering_ci"] == "FAIL"


def legacy_policy(tmp_path):
    file = "alembic/versions/legacy.py"
    target = tmp_path / file
    target.parent.mkdir(parents=True)
    target.write_bytes(b"immutable historical migration\n")
    (tmp_path / "pyproject.toml").write_bytes(b"original configuration\n")
    finding = dict(tool="ruff", file=file, line=2, column=101, code="E501", message="Legacy style")
    return {
        "ruff_version": importlib.metadata.version("ruff"),
        "configuration_sha256": hashlib.sha256(
            (tmp_path / "pyproject.toml").read_bytes()
        ).hexdigest(),
        "source_sha256": {file: hashlib.sha256(target.read_bytes()).hexdigest()},
        "occurrences": [{"finding": finding, "reason": "Byte-immutable rollback contract"}],
    }


def test_exact_legacy_exception_preserves_raw_tool_failure_and_visibility(tmp_path):
    policy = legacy_policy(tmp_path)
    approved = ruff_exception_findings(tmp_path, policy)
    code, report = classify_ruff(1, approved, approved)
    assert code == 0 and report["status"] == "PASS"
    assert report["raw_tool_exit_code"] == 1 and report["findings"] == approved
    assert report["unjustified_findings"] == []
    reports = clean_reports()
    reports["ruff"].update(report)
    assert (
        require_clean_diagnostics({"engineering_ci": "PASS"}, reports, approved)["engineering_ci"]
        == "PASS"
    )


def test_report_version_is_checked_without_local_ruff_dependency(tmp_path, monkeypatch):
    policy = legacy_policy(tmp_path)

    def unavailable_package(name):
        raise AssertionError("Aggregator must use the producing job's tool version")

    monkeypatch.setattr(importlib.metadata, "version", unavailable_package)
    assert ruff_exception_findings(tmp_path, policy, observed_version=policy["ruff_version"]) == [
        row["finding"] for row in policy["occurrences"]
    ]
    for invalid in ("MISSING", "", "different"):
        with pytest.raises(ValueError, match="RUFF_EXCEPTION_TOOL_VERSION_MISMATCH"):
            ruff_exception_findings(tmp_path, policy, observed_version=invalid)


@pytest.mark.parametrize(
    "fault",
    [
        "bytes",
        "config",
        "version",
        "runtime-rule",
        "source-file",
        "escape",
        "duplicate",
        "missing-reason",
        "extra-source",
    ],
)
def test_legacy_style_exception_cannot_expand_or_survive_source_changes(tmp_path, fault):
    policy = legacy_policy(tmp_path)
    row = policy["occurrences"][0]
    if fault == "bytes":
        (tmp_path / row["finding"]["file"]).write_bytes(b"changed\n")
    elif fault == "config":
        (tmp_path / "pyproject.toml").write_bytes(b"changed rules\n")
    elif fault == "version":
        policy["ruff_version"] = "different"
    elif fault == "runtime-rule":
        row["finding"]["code"] = "F821"
    elif fault == "source-file":
        row["finding"]["file"] = "src/runtime.py"
    elif fault == "escape":
        row["finding"]["file"] = "alembic/versions/../../outside.py"
    elif fault == "duplicate":
        policy["occurrences"].append(deepcopy(row))
    elif fault == "missing-reason":
        row["reason"] = ""
    else:
        policy["source_sha256"]["alembic/versions/extra.py"] = "0" * 64
    with pytest.raises(ValueError):
        ruff_exception_findings(tmp_path, policy)


@pytest.mark.parametrize(
    "fault", ["new-line", "new-rule", "duplicate", "missing", "different-file"]
)
def test_ruff_rejects_any_unapproved_or_missing_occurrence(tmp_path, fault):
    approved = ruff_exception_findings(tmp_path, legacy_policy(tmp_path))
    findings = deepcopy(approved)
    if fault == "duplicate":
        findings *= 2
    elif fault == "missing":
        findings = []
    else:
        findings[0][{"new-line": "line", "new-rule": "code", "different-file": "file"}[fault]] = {
            "new-line": 3,
            "new-rule": "F821",
            "different-file": "src/new.py",
        }[fault]
    code, report = classify_ruff(1 if findings else 0, findings, approved)
    assert code == 1 and report["status"] == "FAIL"


@pytest.mark.parametrize("code", [2, False, 0])
def test_raw_ruff_error_or_inconsistent_success_cannot_be_waived(tmp_path, code):
    approved = ruff_exception_findings(tmp_path, legacy_policy(tmp_path))
    with pytest.raises(ValueError, match="RUFF_RAW_RESULT_INCONSISTENT"):
        classify_ruff(code, approved, approved)
