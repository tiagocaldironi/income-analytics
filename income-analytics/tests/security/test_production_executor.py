"""Fault-injected production state-machine tests; all host state is disposable."""

import hashlib
import os
import socket
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def ci_path(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "ci"))


class FakeHost:
    def __init__(self, fault=None):
        self.fault = fault
        self.events = []
        self.db = b"synthetic-db-state"

    def maybe(self, step):
        self.events.append(step)
        if self.fault == step:
            self.fault = None
            raise RuntimeError("injected")

    def verify_package(self, *_): self.maybe("verify")
    def create_and_verify_online_backup(self):
        self.maybe("backup")
        return {"status": "PASS", "schema_head": "same", "sha256": hashlib.sha256(self.db).hexdigest()}
    def preserve_previous_release(self):
        self.maybe("preserve")
        return {"previous_candidate": {"source_commit": "b" * 40}}
    def stage_candidate(self, *_): self.maybe("stage")
    def require_schema_compatible(self, *_): self.maybe("schema")
    def discard_candidate(self): self.events.append("discard")
    def stop_application(self): self.maybe("stop")
    def stop_candidate_application(self): self.events.append("stop_candidate")
    def activate_candidate(self, *_): self.maybe("activate")
    def start_application(self): self.maybe("start")
    def health_check(self, candidate):
        self.maybe("health")
        if self.fault == "version" and candidate.get("source_commit") == "a" * 40:
            return {"status": "ok", "release_commit": "c" * 40}
        return {"status": "ok", "release_commit": candidate["source_commit"]}
    def restore_previous_release(self, *_): self.maybe("rollback")


def fixture_inputs(tmp_path):
    package = tmp_path / "candidate.zip"
    package.write_bytes(b"synthetic-package")
    commit = "a" * 40
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    candidate = {"source_commit": commit, "package_sha256": digest, "artifact_id": 71,
                 "build_run_id": 72, "build_run_attempt": 1}
    checks = {name: {"status": "PASS"} for name in (
        "known_good_A", "installation", "health", "backup", "restore", "rollback",
        "rollback_restore", "synthetic_restore_after_block", "immutable_promotion", "cleanup",
    )}
    checks.update({name: {"status": "EXPECTED_FAILURE_OBSERVED"} for name in (
        "negative_restore_changed_state", "negative_health", "negative_startup",
    )})
    staging = {"status": "PASS", "staging_status": "STAGING_VALIDATED", "checks": checks}
    staging["candidate"] = {"source_commit": commit, "package_sha256": digest}
    staging["candidate"].update({"artifact_id": 71, "build_run_id": 72, "build_run_attempt": 1})
    staging["workflow_identity"] = {"delivery_run_id": "73"}
    staging["workflow_identity"]["controller_checkout_sha"] = commit
    scope = {"decision": "GO", "checkout_sha": commit, "deployment_authorized": False,
             "control_applicability": {"policy_sha256": "d" * 64,
                                       "controls": {"SECURITY": "PASS", "CERT_48": "NOT_APPLICABLE"}}}
    authorization = {"approval": {"state": "APPROVED", "comment_id": 74,
                                   "source_commit": commit, "package_sha256": digest,
                                   "policy_sha256": "d" * 64, "artifact_id": 71,
                                   "build_run_id": 72, "staging_run_id": "73"}}
    phrase = f"DEPLOY {commit} {digest}"
    return package, candidate, staging, scope, authorization, phrase


def test_only_exact_fully_bound_candidate_can_publish(tmp_path):
    from production_executor import execute

    package, candidate, staging, scope, approval, phrase = fixture_inputs(tmp_path)
    host = FakeHost()
    result = execute(host, candidate=candidate, staging=staging, scope=scope,
                     authorization=approval, package=package, confirmation=phrase)
    assert result["status"] == "PUBLISHED"
    assert result["database_restored"] is False
    assert host.events == ["verify", "backup", "preserve", "stage", "schema", "stop",
                           "activate", "start", "health"]


@pytest.mark.parametrize("fault", ["backup", "stage", "schema", "stop"])
def test_pre_activation_failures_never_activate_candidate(tmp_path, fault):
    from production_executor import execute

    package, candidate, staging, scope, approval, phrase = fixture_inputs(tmp_path)
    host = FakeHost(fault)
    with pytest.raises((RuntimeError, ValueError)):
        execute(host, candidate=candidate, staging=staging, scope=scope,
                 authorization=approval, package=package, confirmation=phrase)
    assert "activate" not in host.events
    assert host.db == b"synthetic-db-state"


@pytest.mark.parametrize("fault", ["start", "health", "version"])
def test_failed_live_validation_restores_code_and_never_database(tmp_path, fault):
    from production_executor import ProductionExecutionError, execute

    package, candidate, staging, scope, approval, phrase = fixture_inputs(tmp_path)
    host = FakeHost(fault)
    with pytest.raises(ProductionExecutionError, match="DEPLOYMENT_FAILED_ROLLED_BACK"):
        execute(host, candidate=candidate, staging=staging, scope=scope,
                 authorization=approval, package=package, confirmation=phrase)
    assert "rollback" in host.events
    assert host.db == b"synthetic-db-state"


def test_missing_applicable_controls_or_wrong_artifact_hash_stays_blocked(tmp_path):
    from production_executor import ProductionExecutionError, execute

    package, candidate, staging, scope, approval, phrase = fixture_inputs(tmp_path)
    scope["control_applicability"]["controls"]["RUNTIME_DEPENDENCY"] = "BLOCKED"
    with pytest.raises(ProductionExecutionError, match="PRODUCTION_EVIDENCE_BLOCKED"):
        execute(FakeHost(), candidate=candidate, staging=staging, scope=scope,
                 authorization=approval, package=package, confirmation=phrase)
    scope["control_applicability"]["controls"]["RUNTIME_DEPENDENCY"] = "PASS"
    package.write_bytes(b"mutated package")
    with pytest.raises(ProductionExecutionError, match="PACKAGE_DIGEST_MISMATCH"):
        execute(FakeHost(), candidate=candidate, staging=staging, scope=scope,
                 authorization=approval, package=package, confirmation=phrase)


def test_explicit_comment_must_be_exact_and_from_release_authority():
    from production_authorization import valid_production_comment

    approval = {"state": "APPROVED", "approver": "owner", "comment_id": 5,
                "comment_url": "https://github.com/tiagocaldironi/income-analytics/pull/88#issuecomment-5",
                "comment_body_sha256": hashlib.sha256(
                    f"PRODUCTION_ARTIFACT_APPROVED {'a' * 40} {'b' * 64} {'c' * 64} 5".encode()
                ).hexdigest(),
                "source_commit": "a" * 40, "package_sha256": "b" * 64,
                "policy_sha256": "c" * 64, "artifact_id": 5}
    body = f"PRODUCTION_ARTIFACT_APPROVED {'a' * 40} {'b' * 64} {'c' * 64} 5"
    comment = {"id": 5, "html_url": approval["comment_url"], "body": body,
               "user": {"login": "owner"}}
    assert valid_production_comment(approval, comment, "owner")
    assert not valid_production_comment(approval, comment, "other")


def test_runtime_lock_audit_traces_exact_otel_update_and_google_consumer(tmp_path, monkeypatch):
    import release_dependency_analysis as analysis

    repo = tmp_path
    app = repo / "income-analytics"
    lock_dir = app / "ci"
    lock_dir.mkdir(parents=True)
    current = (Path(__file__).resolve().parents[2] / "ci/runtime-windows-py314.lock").read_bytes()
    old = current.replace(
        b"opentelemetry-api==1.45.2 --hash=sha256:2cbd737377e710ee740d261c94e93fa0f08e6d037c18f17513cc0a2d94479a34",
        b"opentelemetry-api==1.45.1 --hash=sha256:b31553efa588ae44bc306f863c785c5333a9ecc091248c6ee68b4b6c87fdedfb",
    )
    (lock_dir / "runtime-windows-py314.lock").write_bytes(old)
    (lock_dir / "requirements-windows-py314.lock").write_bytes(current)
    source = app / "src/income_analytics"
    source.mkdir(parents=True)
    (source / "main.py").write_text("def app():\n    return None\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "ci@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "CI"], cwd=repo, check=True)
    subprocess.run(["git", "add", "income-analytics"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base lock"], cwd=repo, check=True)
    base_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    (lock_dir / "runtime-windows-py314.lock").write_bytes(current)
    locked = analysis._lock_entries(current)

    def metadata(name, version):
        requirements = []
        if name == "google-api-core":
            requirements = ["opentelemetry-api<2.0.0,>=1.44.0"]
        elif name == "opentelemetry-api":
            requirements = ["typing-extensions>=4.5.0"]
        return {"info": {"version": version, "requires_dist": requirements},
                "urls": [{"packagetype": "bdist_wheel", "digests": {"sha256": locked[name][1]}}]}

    monkeypatch.setattr(analysis, "_pypi_release", metadata)
    report = analysis.analyze_runtime_dependency(
        app, ["ci/runtime-windows-py314.lock"], base_sha
    )
    assert report["status"] == "PASS"
    assert report["changes"] == [{"path": "ci/runtime-windows-py314.lock",
                                  "name": "opentelemetry-api",
                                  "before": ("1.45.1", "b31553efa588ae44bc306f863c785c5333a9ecc091248c6ee68b4b6c87fdedfb"),
                                  "after": ("1.45.2", "2cbd737377e710ee740d261c94e93fa0f08e6d037c18f17513cc0a2d94479a34")}]
    assert report["consumers"] == [{"consumer": "google-api-core",
                                    "requirement": "opentelemetry-api<2.0.0,>=1.44.0"}]
    assert report["application_direct_references"] == []


@pytest.mark.skipif(os.name != "nt", reason="real Windows process and named-event adapter")
def test_real_windows_adapter_installs_starts_stops_and_rolls_back_disposable_release(
    tmp_path, monkeypatch,
):
    """Use a temporary Git checkout, launcher, random port and SQLite database only."""
    from production_executor import WindowsHost

    python = sys.executable
    assert subprocess.run([python, "-c", "import uvicorn, fastapi"], check=False).returncode == 0
    old_root = tmp_path / "old"
    (old_root / "src" / "income_analytics").mkdir(parents=True)
    (old_root / "alembic" / "versions").mkdir(parents=True)
    old_main = (
        "from fastapi import FastAPI\napp=FastAPI()\n"
        "@app.get('/health')\ndef health(): return {'status':'ok'}\n"
    )
    (old_root / "src" / "income_analytics" / "main.py").write_text(old_main, encoding="utf-8")
    wrapper = Path(__file__).resolve().parents[2] / "src/income_analytics/windows_server.py"
    (old_root / "src" / "income_analytics" / "windows_server.py").write_bytes(wrapper.read_bytes())
    (old_root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    migration = "revision='schema1'\ndown_revision=None\n"
    (old_root / "alembic" / "versions" / "0001.py").write_text(migration, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=old_root, check=True)
    subprocess.run(["git", "config", "user.email", "ci@example.invalid"], cwd=old_root, check=True)
    subprocess.run(["git", "config", "user.name", "CI"], cwd=old_root, check=True)
    subprocess.run(["git", "add", "."], cwd=old_root, check=True)
    subprocess.run(["git", "commit", "-qm", "disposable previous release"],
                   cwd=old_root, check=True)

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    if os.environ.get("INCOME_CI_OFFLINE") == "1":
        import sitecustomize

        # The offline suite denies loopback too. Permit only this fixture's
        # numeric endpoint, without changing the guard for other destinations.
        guarded_connect = socket.socket.connect
        guarded_dns = socket.getaddrinfo

        def connect(sock, address):
            if address == ("127.0.0.1", port):
                return sitecustomize._connect(sock, address)
            return guarded_connect(sock, address)

        def resolve(host, service, *args, **kwargs):
            if host == "127.0.0.1" and service == port:
                return sitecustomize._getaddrinfo(host, service, *args, **kwargs)
            return guarded_dns(host, service, *args, **kwargs)

        monkeypatch.setattr(socket.socket, "connect", connect)
        monkeypatch.setattr(socket, "getaddrinfo", resolve)
        monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    database = tmp_path / "disposable.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        db.execute("INSERT INTO alembic_version VALUES ('schema1')")
        db.execute("CREATE TABLE synthetic_financial_fixture (value INTEGER NOT NULL)")
        db.execute("INSERT INTO synthetic_financial_fixture VALUES (42)")
    db_before = hashlib.sha256(database.read_bytes()).hexdigest()
    launcher = tmp_path / "DisposableLauncher.ps1"
    test_site_packages = os.pathsep.join(
        path for path in sys.path
        if path.lower().endswith(("site-packages", "dist-packages"))
    )
    old_python_path = f"{old_root / 'src'}{os.pathsep}{test_site_packages}"
    launcher.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        f"Set-Location -LiteralPath '{old_root}'\n"
        f"$env:PYTHONPATH = '{old_python_path}'\n"
        "$env:PYTHONDONTWRITEBYTECODE = '1'\n"
        f"& '{python}' -X utf8 -m income_analytics.windows_server "
        f"income_analytics.main:app --app-dir src --host 127.0.0.1 --port {port}\n",
        encoding="utf-8",
    )

    package = tmp_path / "candidate.zip"
    candidate_commit = "a" * 40
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("src/income_analytics/main.py",
                         "import os\nfrom fastapi import FastAPI\napp=FastAPI()\n"
                         "@app.get('/health')\ndef health(): return "
                         "{'status':'ok','release_commit':os.environ.get('INCOME_ANALYTICS_RELEASE_COMMIT','')}\n")
        archive.writestr("src/income_analytics/windows_server.py", wrapper.read_bytes())
        archive.writestr("alembic/versions/0001.py", migration)
        archive.writestr("requirements.lock", "")
    candidate = {"source_commit": candidate_commit}
    host = WindowsHost(
        release_root=tmp_path / "releases", database=database, launcher=launcher,
        health_url=f"http://127.0.0.1:{port}/health", test_mode=True, port=port,
    )
    host.start_application()
    snapshot = {}
    try:
        old_health = host.health_check({})
        assert old_health["status"] == "ok" and "release_commit" not in old_health
        snapshot = host.preserve_previous_release()
        backup = host.create_and_verify_online_backup()
        assert backup["status"] == "PASS" and backup["schema_head"] == "schema1"
        host.stage_candidate(package, candidate)
        host.require_schema_compatible(candidate, backup["schema_head"])
        installed_python = host.package_root / ".venv/Scripts/python.exe"
        subprocess.run(
            [str(installed_python), "-c", "import uvicorn, fastapi"],
            env={**os.environ, "PYTHONPATH": test_site_packages},
            check=True,
        )

        host.stop_application()
        assert host.stopped
        host.activate_candidate(candidate)
        host.start_application()
        assert host.health_check(candidate)["release_commit"] == candidate_commit

        # Exercise the actual adapter's code/config rollback after candidate served health.
        host.stop_candidate_application()
        host.restore_previous_release(snapshot)
        host.start_application()
        rolled_back = host.health_check(snapshot["previous_candidate"])
        assert rolled_back["status"] == "ok" and "release_commit" not in rolled_back
        assert hashlib.sha256(database.read_bytes()).hexdigest() == db_before
    finally:
        try:
            host.stop_candidate_application()
        except Exception:
            pass
        if snapshot:
            host.restore_previous_release(snapshot)
        host.discard_candidate()
