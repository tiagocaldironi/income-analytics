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
