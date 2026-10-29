"""Adversarial scanner contracts. All credential material is synthetic."""

import io
import json

import pytest
from security import enforce_secrets, enforce_triage, identity, query_dependencies, secrets_in, sha


def test_secret_detection_never_serializes_value():
    value = b"ghp_" + b"A" * 36
    result = secrets_in(value, "synthetic.txt")
    assert len(result) == 1
    assert value.decode() not in json.dumps(result)
    assert result[0]["fingerprint"] == sha(value)


def test_benign_marker_approval_cannot_allow_real_key():
    marker = b"-----BEGIN " + b"PRIVATE KEY-----"
    benign = secrets_in(marker, "fixture.txt")
    decision = dict(benign[0], state="FALSE_POSITIVE", reason="Bare test marker, no key")
    assert enforce_secrets(benign, [decision]) == []
    assert enforce_secrets(secrets_in(marker + b"\nactual-content", "fixture.txt"), [decision])


def test_new_sast_finding_and_high_risk_acceptance_fail():
    row = dict(tool="synthetic", rule="eval", file="example.js", code_sha256="a", severity="HIGH")
    assert enforce_triage([row], [])
    decision = dict(identity=identity(row), state="ACCEPTED_RISK", reason="Cannot waive high")
    assert enforce_triage([row], [decision])
    decision["state"] = "MITIGATED"
    assert enforce_triage([row], [decision])
    decision["evidence"] = ["synthetic regression proof"]
    assert enforce_triage([row], [decision]) == []
    assert enforce_triage([dict(row, code_sha256="changed")], [decision])


def test_vulnerable_dependency_fixture_is_rejected():
    package = dict(ecosystem="PyPI", name="synthetic-package", version="1.0")
    result = query_dependencies(
        [package],
        lambda *a, **k: io.BytesIO(
            json.dumps({"results": [{"vulns": [{"id": "SYNTHETIC-001"}]}]}).encode()
        ),
    )
    assert result["status"] == "FAIL"
    assert result["alerts"][0]["triage"] == "REQUIRED"


def test_dependency_service_unavailable_never_passes():
    def unavailable(*args, **kwargs):
        raise OSError("synthetic outage")

    with pytest.raises(OSError):
        query_dependencies([], unavailable)


def test_partial_dependency_response_rejected():
    with pytest.raises(ValueError, match="INCOMPLETE"):
        query_dependencies(
            [dict(ecosystem="PyPI", name="synthetic", version="1")],
            lambda *a, **k: io.BytesIO(b'{"results":[]}'),
        )


def test_pagination_cannot_silently_hide_advisories():
    with pytest.raises(ValueError, match="INCOMPLETE"):
        query_dependencies(
            [dict(ecosystem="PyPI", name="synthetic", version="1")],
            lambda *a, **k: io.BytesIO(b'{"results":[{"next_page_token":"more"}]}'),
        )


def test_security_failure_is_hard_dependency_of_protected_gate():
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[2]
    document = yaml.load(
        (root / ".github/workflows/ci-offline.yml").read_text(), Loader=yaml.BaseLoader
    )
    gate = document["jobs"]["engineering_gate"]
    assert gate["name"] == "CI / Engineering"
    assert "security" in gate["needs"]
    steps = "\n".join(step.get("run", "") for step in gate["steps"])
    assert "needs.security.result" in steps
    assert "-ne 'success') { exit 1 }" in steps
    security = document["jobs"]["security"]
    assert security["name"] == "CI / Security baseline"
    assert document["permissions"] == {"contents": "read"}
    assert "pull_request_target" not in document["on"]
    checkout = next(
        step for step in security["steps"] if step.get("uses", "").startswith("actions/checkout@")
    )
    assert checkout["with"]["fetch-depth"] == "0"
    assert checkout["with"]["persist-credentials"] == "false"


def test_secret_in_nested_distributable_wheel_is_rejected(tmp_path):
    import zipfile

    from security import artifact_secrets

    value = b"ghp_" + b"Z" * 36
    wheel = io.BytesIO()
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("synthetic_package/config.py", b"token = " + value)
    package = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("wheelhouse/synthetic-1.0-py3-none-any.whl", wheel.getvalue())
    findings = artifact_secrets(package)
    assert enforce_secrets(findings, [])
    assert value.decode() not in json.dumps(findings)


def test_private_persistence_and_key_files_cannot_enter_source_distribution():
    from security import forbidden_source_files

    blocked = ["data/private.db", "private.pem", "secrets/.env", "wallet.sqlite3"]
    assert forbidden_source_files(blocked + [".env.example", "src/app.py"]) == sorted(blocked)


def test_unknown_bundled_helper_version_is_not_invented():
    from security import bom_component, package_url

    package = dict(
        ecosystem="npm",
        name="tslib",
        version="NOT_VERIFIED",
        package_only=True,
        hashes=[],
        declared_range="^2.1.0",
    )

    def response(request, **kwargs):
        assert "version" not in json.loads(request.data)["queries"][0]
        return io.BytesIO(b'{"results":[{}]}')

    assert query_dependencies([package], response)["status"] == "PASS"
    assert "version" not in bom_component(package)
    assert package_url(package) == "pkg:npm/tslib"
    assert package_url(dict(ecosystem="npm", name="@firebase/auth", version="1.13.8")) == (
        "pkg:npm/%40firebase/auth@1.13.8"
    )


@pytest.mark.parametrize("status", [None, "failure", "skipped", "cancelled", "timed_out"])
def test_security_missing_or_unsuccessful_blocks_protected_aggregate(status):
    from gate_policy import require_security_baseline

    original = {
        "engineering_ci": "PASS",
        "financial_certification": "BLOCKED",
        "deployment_authorized": False,
    }
    result = require_security_baseline(original, status)
    assert result["engineering_ci"] == "FAIL"
    assert result["security_baseline"] != "PASS"
    assert original["engineering_ci"] == "PASS"
    assert result["financial_certification"] == "BLOCKED"
    assert result["deployment_authorized"] is False


def test_security_success_cannot_override_other_engineering_failures():
    from gate_policy import require_security_baseline

    assert (
        require_security_baseline({"engineering_ci": "FAIL"}, "success")["engineering_ci"] == "FAIL"
    )
    assert (
        require_security_baseline({"engineering_ci": "PASS"}, "success")["engineering_ci"] == "PASS"
    )


def test_old_ci_without_security_cannot_be_a_new_delivery_candidate():
    from delivery import BASELINE_COMMIT, BASELINE_RUN, DeliveryError, security_delivery_gate

    with pytest.raises(DeliveryError, match="SECURITY_GATE_NOT_APPROVED"):
        security_delivery_gate({}, [], BASELINE_RUN, BASELINE_COMMIT)
    assert security_delivery_gate({}, [], BASELINE_RUN, BASELINE_COMMIT, rollback=True) == (
        "LEGACY_PINNED_ROLLBACK_ONLY"
    )
    with pytest.raises(DeliveryError):
        security_delivery_gate({}, [], BASELINE_RUN + 1, BASELINE_COMMIT, rollback=True)
    with pytest.raises(DeliveryError, match="SECURITY_JOB_NOT_APPROVED"):
        security_delivery_gate({"security_baseline": "PASS"}, [], 1, "a" * 40)
    assert (
        security_delivery_gate(
            {"security_baseline": "PASS"},
            [{"name": "CI / Security baseline", "conclusion": "success"}],
            1,
            "a" * 40,
        )
        == "PASS"
    )
