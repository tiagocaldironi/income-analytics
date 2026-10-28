"""Regression checks for CI isolation and report redaction, not financial behavior."""

import importlib.util
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("ci_runner", Path(__file__).with_name("run.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_environment_drops_inherited_credentials_and_production_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAPI_TOKEN", "synthetic-private-token")
    monkeypatch.setenv("INCOME_ANALYTICS_DATABASE", "outside-production.db")
    monkeypatch.setenv("FIREBASE_AUTH_EMULATOR_HOST", "localhost:9099")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "production-project")
    env = runner.isolated_environment(tmp_path)
    assert "BRAPI_TOKEN" not in env
    assert "FIREBASE_AUTH_EMULATOR_HOST" not in env
    assert "FIREBASE_PROJECT_ID" not in env
    assert Path(env["INCOME_ANALYTICS_DATABASE"]).is_relative_to(tmp_path)
    assert env["INCOME_ANALYTICS_DISABLE_BACKGROUND_JOBS"] == "1"
    assert env["INCOME_RUN_FIREBASE_LIVE_TESTS"] == "0"


def test_report_omits_failure_payload_and_captured_output(tmp_path):
    raw, clean = tmp_path / "raw.xml", tmp_path / "safe.xml"
    raw.write_text(
        '<testsuites><testsuite><testcase name="test_fixture" classname="tests.fixture">'
        '<failure message="SYNTHETIC_PRIVATE">SYNTHETIC_PRIVATE</failure>'
        "<system-out>SYNTHETIC_PRIVATE</system-out></testcase>"
        '<testcase name="test_external"><skipped message="SYNTHETIC_PRIVATE" />'
        "</testcase></testsuite></testsuites>",
        encoding="utf-8",
    )
    report = runner.safe_junit(raw, clean)
    assert report["totals"] == {"passed": 0, "failed": 1, "errors": 0, "skipped": 1}
    assert "SYNTHETIC_PRIVATE" not in clean.read_text(encoding="utf-8")
    assert "SYNTHETIC_PRIVATE" not in json.dumps(report)


def test_network_is_blocked_in_python_and_inherited_subprocess():
    with pytest.raises(RuntimeError, match="CI_OFFLINE_NETWORK_BLOCKED"):
        socket.create_connection(("127.0.0.1", 8002))
    result = subprocess.run(
        [sys.executable, "-c", "import socket; socket.getaddrinfo('example.com',443)"],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    assert result.returncode != 0
    assert "CI_OFFLINE_NETWORK_BLOCKED" in result.stderr


def test_internal_asyncio_socketpair_remains_available():
    first, second = socket.socketpair()
    try:
        first.send(b"synthetic")
        assert second.recv(9) == b"synthetic"
    finally:
        first.close()
        second.close()
