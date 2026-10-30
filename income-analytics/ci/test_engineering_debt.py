"""Negative controls for occurrence accounting and promoted diagnostics."""

from copy import deepcopy

import pytest
from engineering_debt import reconciled_findings, require_clean_diagnostics
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
        "ruff": dict(identity, check="ruff", status="PASS", exit_code=0, findings=[]),
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
