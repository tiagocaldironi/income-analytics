"""Synthetic negative evidence, never modifications of certified fixtures."""

import hashlib
import json
from copy import deepcopy

import pytest
from financial_certification import (
    ROOT,
    classify_results,
    evaluate,
    failure_causes,
    frozen_integrity,
    historical_provenance,
    validate_evidence,
)
from gate_policy import require_security_baseline, summarize_reports


def synthetic_contract():
    document = {
        "snapshot_id": "synthetic-original-1",
        "engine_version": "synthetic-v1",
        "policy_id": "synthetic-policy",
        "period": "2025",
        "source_id": "synthetic-source",
        "price_date": "2025-12-30",
        "source_kind": "B3_COTAHIST",
        "generator": "INDEPENDENT_SYNTHETIC_TEST_ONLY",
        "canonical_order": ["A3", "B3"],
        "expected_result_sha256": hashlib.sha256(b"independent synthetic expectation").hexdigest(),
    }
    payload = json.dumps(document).encode()
    record_hash = hashlib.sha256(b"synthetic independent approval record").hexdigest()
    requirement = {
        **document,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "price_cutoff": "2025-12-31",
        "approval_record_sha256": record_hash,
        "approval_authority": "synthetic independent authority",
        "approval_record": "synthetic approval record",
    }
    approval = {
        "origin": "INDEPENDENT_ORIGINAL",
        "authority": requirement["approval_authority"],
        "record": requirement["approval_record"],
        "record_sha256": record_hash,
        "sha256": requirement["sha256"],
    }
    return document, payload, requirement, approval


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("snapshot_id", "other", "SNAPSHOT_ID_MISMATCH"),
        ("engine_version", "future-engine", "ENGINE_VERSION_MISMATCH"),
        ("policy_id", "other-policy", "POLICY_ID_MISMATCH"),
        ("period", "2026", "PERIOD_MISMATCH"),
        ("price_date", "2026-10-29", "FUTURE_PRICE_FOR_HISTORICAL_REFERENCE"),
        ("source_kind", "CVM_ITR", "INCOMPATIBLE_B3_CVM_SOURCE"),
        ("source_id", "current-cvm-archive", "SOURCE_ID_MISMATCH"),
        ("canonical_order", ["B3", "A3"], "NONDETERMINISTIC_OR_DUPLICATE_ORDER"),
        ("canonical_order", ["A3", "A3"], "NONDETERMINISTIC_OR_DUPLICATE_ORDER"),
        ("expected_result_sha256", "artificial-result", "EXPECTED_RESULT_NOT_INDEPENDENTLY_PINNED"),
        ("generator", "IMPLEMENTATION_UNDER_TEST", "SELF_GENERATED_EXPECTATION_FORBIDDEN"),
    ],
)
def test_invalid_evidence_cannot_be_self_authorized(field, value, reason):
    document, _, requirement, approval = synthetic_contract()
    document[field] = value
    forged = json.dumps(document).encode()
    # Attacker can supply a claimed digest, but cannot redefine the independent pins.
    approval["sha256"] = hashlib.sha256(forged).hexdigest()
    problems = validate_evidence(forged, requirement, approval)
    assert "EVIDENCE_DIGEST_MISMATCH" in problems
    assert reason in problems


def test_hash_equality_does_not_replace_provenance():
    _, payload, requirement, approval = synthetic_contract()
    assert validate_evidence(payload, requirement, approval) == []
    approval["origin"] = "CURRENT_ENGINE_RECONSTRUCTION"
    assert "INDEPENDENT_PROVENANCE_MISSING" in validate_evidence(payload, requirement, approval)
    assert "INDEPENDENT_PROVENANCE_MISSING" in validate_evidence(payload, requirement, {})


def test_changed_authority_or_approval_record_is_rejected():
    _, payload, requirement, approval = synthetic_contract()
    for field in ("record", "record_sha256", "authority"):
        altered = {**approval, field: "self-approved"}
        assert "INDEPENDENT_PROVENANCE_MISSING" in validate_evidence(payload, requirement, altered)


def test_manifest_and_frozen_bytes_are_independently_pinned(tmp_path):
    original = b"synthetic frozen source\n"
    (tmp_path / "engine.txt").write_bytes(original)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"files": {"engine.txt": hashlib.sha256(original).hexdigest()}}))
    pins = [
        {
            "manifest": "manifest.json",
            "key": "files",
            "sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        }
    ]
    assert frozen_integrity(tmp_path, pins)[0]["code"] == "VERIFIED_BYTES"
    (tmp_path / "engine.txt").write_bytes(b"changed")
    assert frozen_integrity(tmp_path, pins)[0]["code"] == "FROZEN_IDENTITY_MISMATCH"
    manifest.write_text(
        json.dumps({"files": {"engine.txt": hashlib.sha256(b"changed").hexdigest()}})
    )
    assert frozen_integrity(tmp_path, pins)[0]["code"] == "FROZEN_MANIFEST_MISMATCH"


def synthetic_results(status="passed"):
    totals = {key: int(key == status) for key in ("passed", "failed", "errors", "skipped")}
    return {
        "cases": [{"class": "tests.synthetic", "name": "test_original", "status": status}],
        "totals": totals,
    }


@pytest.mark.parametrize("blocker", ["MISSING_REFERENCE", "CERT_48", "FROZEN_IDENTITY_MISMATCH"])
def test_successful_assertions_do_not_override_missing_certification(blocker):
    result = classify_results(
        synthetic_results(), {"tests/synthetic.py::test_original"}, set(), [blocker]
    )
    assert result["financial_state"] == "FINANCIAL_BLOCKED"
    assert not result["release_authorized"]


def test_new_failure_is_not_relabelled_as_historical_blockage():
    result = classify_results(synthetic_results("failed"), set(), set(), ["CERT_48"])
    assert result["financial_state"] == "FINANCIAL_FAIL"
    assert result["unexpected_failures"] == ["tests/synthetic.py::test_original"]


@pytest.mark.parametrize("mutation", ["empty", "skip", "missing", "counts", "duplicate"])
def test_missing_execution_or_coverage_never_passes(mutation):
    details = synthetic_results("skipped" if mutation == "skip" else "passed")
    if mutation == "empty":
        details["cases"] = []
    elif mutation == "counts":
        details["totals"]["passed"] = 99
    elif mutation == "duplicate":
        details["cases"] *= 2
    required = {"missing.py::test_original"} if mutation == "missing" else set()
    assert (
        classify_results(details, required, set(), [])["financial_state"]
        == "FINANCIAL_NOT_VERIFIED"
    )


def test_real_policy_keeps_independent_approval_blocked_and_finance_unchanged():
    policy = json.loads((ROOT / "ci/financial_certification_policy.json").read_text())
    details = {"cases": [], "totals": {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}}
    result = evaluate(ROOT, details)
    assert "CERT_48_REQUIRES_INDEPENDENT_RECONCILIATION" in result["blockers"]
    assert "22_HISTORICAL_REFERENCES_UNAPPROVED" in result["blockers"]
    assert not result["production_authorized"]
    assert all(
        row["sha256"] == hashlib.sha256((ROOT / row["manifest"]).read_bytes()).hexdigest()
        for row in policy["frozen_manifests"]
    )


def test_financial_evidence_controls_cannot_authorize_engineering_security_or_production():
    summary = summarize_reports({})
    before = deepcopy(summary)
    result = require_security_baseline(summary, "skipped")
    assert summary == before
    assert result["engineering_ci"] == "FAIL"
    assert result["security_baseline"] != "PASS"
    assert result["financial_certification"] == "BLOCKED"
    assert not result["deployment_authorized"]


def test_changed_failure_cause_in_known_case_is_a_real_failure():
    policy = json.loads((ROOT / "ci/financial_certification_policy.json").read_text())
    node = next(iter(policy["known_failure_causes"]))
    cases = []
    for name in policy["mandatory_financial_tests"]:
        file, test = name.split("::", 1)
        cases.append(
            {
                "class": file[:-3].replace("/", "."),
                "name": test,
                "status": "failed" if name == node else "passed",
            }
        )
    details = {
        "cases": cases,
        "totals": {"passed": 96, "failed": 1, "errors": 0, "skipped": 0},
        "failure_causes": {node: "UNCLASSIFIED_FAILURE"},
    }
    assert evaluate(ROOT, details)["financial_state"] == "FINANCIAL_FAIL"


@pytest.mark.parametrize(
    "payload",
    [
        b'<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///forbidden">]><testsuite/>',
        b"<testsuite>\x00</testsuite>",
        b"x" * (16 * 1024 * 1024 + 1),
    ],
    ids=["entity", "nul-encoding", "oversize"],
)
def test_junit_diagnostics_reject_entities_encodings_and_unbounded_input(tmp_path, payload):
    path = tmp_path / "synthetic-junit.xml"
    path.write_bytes(payload)
    with pytest.raises(ValueError, match="JUNIT_"):
        failure_causes(path)


def test_removing_labels_or_evidence_requirements_does_not_approve_history():
    policy = json.loads((ROOT / "ci/financial_certification_policy.json").read_text())
    policy["unresolved_approvals"] = []
    assert all(row["state"] != "VERIFIED" for row in historical_provenance(ROOT, policy))
    policy["required_reference_ids"] = []
    assert historical_provenance(ROOT, policy) == [
        {"id": "REQUIRED_REFERENCE_SCOPE", "state": "CONFLICTING"}
    ]


def test_financial_runner_failure_is_explicitly_not_verified(tmp_path, monkeypatch):
    import governance

    def unavailable(*args):
        raise ValueError("SYNTHETIC_PRIVATE_PAYLOAD_DO_NOT_EMIT")

    monkeypatch.setattr(governance, "run_check", unavailable)
    monkeypatch.setattr(governance, "source_fingerprint", lambda: "synthetic-fingerprint")
    monkeypatch.setattr(governance, "governance_policy_identity", lambda root: "synthetic-policy")
    monkeypatch.setattr("sys.argv", ["governance.py", "financial", "--reports", str(tmp_path)])
    assert governance.main() == 2
    report = json.loads((tmp_path / "financial/result.json").read_text())
    assert report["status"] == "FAIL" and report["financial_state"] == "FINANCIAL_NOT_VERIFIED"
    assert not report["mandatory_coverage_verified"] and not report["production_authorized"]
    assert report["blockers"] == ["FINANCIAL_RUNNER_NOT_VERIFIED"]
    assert "SYNTHETIC_PRIVATE_PAYLOAD_DO_NOT_EMIT" not in json.dumps(report)
