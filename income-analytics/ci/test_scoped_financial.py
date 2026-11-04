"""Fail-closed controls for a review-only financial applicability proposal."""

import hashlib
import json
from copy import deepcopy

import pytest
from scoped_financial import assess
from scoped_financial_trace import CALLS, DEFINITIONS, observe


@pytest.fixture
def evidence(tmp_path):
    files = {}
    for index in range(41):
        name = f"immutable-{index}.txt"
        (tmp_path / name).write_bytes(b"synthetic control only")
        files[name] = hashlib.sha256(b"synthetic control only").hexdigest()
    (tmp_path / "immutable.json").write_text(json.dumps({"files": files}))
    policy = {
        "test_targets": ["tests/feature.py"],
        "required_executed_modules": ["income_analytics.feature"],
        "required_executed_functions": ["income_analytics.feature:calculate"],
        "cert48_modules": ["income_analytics.frozen"],
        "immutable_inventory": "immutable.json",
        "historical_baseline_sha": "a" * 40,
        "historical_out_of_scope_proposal": {
            "tests/history.py::old": {
                "baseline_status": "failed", "cause": "MISSING_HISTORICAL_FILE",
                "issue": 58, "baseline_sha": "a" * 40,
            }
        },
    }
    details = {
        "cases": [{"class": "tests.feature", "name": "works", "status": "passed"}],
        "totals": {"passed": 1, "failed": 0, "errors": 0, "skipped": 0},
    }
    trace = {"calls": ["income_analytics.feature:calculate"]}
    history = {
        "cases": [{"class": "tests.history", "name": "old", "status": "failed"}],
        "failure_causes": {"tests/history.py::old": "MISSING_HISTORICAL_FILE"},
    }
    return policy, details, trace, history, tmp_path


def test_passing_technical_evidence_does_not_approve_itself(evidence):
    result = assess(*evidence)
    assert result["technical_state"] == "PASS"
    assert result["financial_release_decision"] == "NO_GO"
    assert result["financial_approval"] == "PENDING_INDEPENDENT_REVIEW"
    assert result["deployment_authorized"] is False
    assert result["historical_out_of_scope_proposal"][0]["observed"] == "failed"


@pytest.mark.parametrize("state", ["failed", "errors", "skipped", "unknown"])
def test_every_new_bad_status_blocks(evidence, state):
    policy, details, trace, history, root = evidence
    details["cases"][0]["status"] = state
    assert assess(policy, details, trace, history, root)["technical_state"] == "BLOCKED"


def test_missing_test_module_dependency_and_duplicate_cases_block(evidence):
    policy, details, trace, history, root = evidence
    for changed in ({"cases": []}, {"cases": details["cases"] * 2}):
        assert assess(policy, {**details, **changed}, trace, history, root)[
            "technical_state"
        ] == "BLOCKED"
    policy["test_targets"].append("tests/missing.py")
    assert assess(policy, details, trace, history, root)["technical_state"] == "BLOCKED"
    policy["test_targets"].pop()
    assert assess(policy, details, {"calls": []}, history, root)["technical_state"] == "BLOCKED"


def test_actual_frozen_dependency_cannot_be_excluded(evidence):
    policy, details, trace, history, root = evidence
    trace["calls"].append("income_analytics.frozen:metrics")
    assert "CERT48_DEPENDENCY_EXECUTED" in assess(
        policy, details, trace, history, root
    )["technical_blockers"]


def test_immutable_change_blocks_without_rewriting_hashes(evidence):
    policy, details, trace, history, root = evidence
    (root / "immutable-0.txt").write_bytes(b"changed")
    assert "IMMUTABLE_BYTES_CHANGED:immutable-0.txt" in assess(
        policy, details, trace, history, root
    )["technical_blockers"]


@pytest.mark.parametrize("change", ["missing", "cause", "status", "new", "duplicate"])
def test_historical_status_or_cause_cannot_hide_a_regression(evidence, change):
    policy, details, trace, original, root = evidence
    history = deepcopy(original)
    if change == "missing":
        history["cases"] = []
    elif change == "cause":
        history["failure_causes"] = {}
    elif change == "status":
        history["cases"][0]["status"] = "errors"
    elif change == "new":
        history["cases"].append({"class": "tests.feature", "name": "new", "status": "failed"})
    else:
        history["cases"] *= 2
    assert assess(policy, details, trace, history, root)["technical_state"] == "BLOCKED"


def test_resolved_history_is_visible_and_does_not_block(evidence):
    policy, details, trace, history, root = evidence
    history["cases"][0]["status"] = "passed"
    history["failure_causes"] = {}
    assert assess(policy, details, trace, history, root)["technical_state"] == "PASS"


def test_profiler_distinguishes_class_definition_from_executed_method():
    from types import SimpleNamespace

    saved_calls, saved_definitions = set(CALLS), set(DEFINITIONS)
    for flags, name in [(0, "Sample"), (2, "Sample.metrics")]:
        frame = SimpleNamespace(
            f_code=SimpleNamespace(co_name=name, co_qualname=name, co_flags=flags),
            f_globals={"__name__": "income_analytics.synthetic_trace_control"},
        )
        observe(frame, "call", None)
    assert "income_analytics.synthetic_trace_control:Sample" in DEFINITIONS
    assert "income_analytics.synthetic_trace_control:Sample.metrics" in CALLS
    CALLS.clear()
    CALLS.update(saved_calls)
    DEFINITIONS.clear()
    DEFINITIONS.update(saved_definitions)
