"""Operational faults use synthetic data and owned, disposable capabilities only."""

import errno
import json
import logging
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from delivery import (
    DeliveryError,
    Workspace,
    backup_database,
    database_check,
    production_request,
    restore_database,
    rollback_compatibility,
)
from operational import evaluate, require_operational, retention_plan, validate_receipt
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from income_analytics.infrastructure import operational as runtime
from income_analytics.infrastructure.auth_config import validate_configuration


@pytest.fixture
def owned():
    workspace = Workspace()
    try:
        yield workspace
    finally:
        workspace.cleanup()


def seed(workspace, name="synthetic.db"):
    path = workspace.file(name)
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE alembic_version(version_num TEXT)")
        db.execute("INSERT INTO alembic_version VALUES ('synthetic-head')")
        db.execute("CREATE TABLE probe(id INTEGER PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO probe VALUES(1,'synthetic-only')")
        db.commit()
    return path


def healthy_details():
    cases = [{"name": f"test_failure_exercise[{i:02d}]", "status": "passed"}
             for i in range(1, 26)]
    return {"cases": cases, "totals": {"passed": 25, "failed": 0, "errors": 0, "skipped": 0}}


@pytest.mark.parametrize("scenario", [f"{i:02d}" for i in range(1, 26)])
def test_failure_exercise(scenario, owned, monkeypatch, caplog):
    path = seed(owned)
    before = path.read_bytes()
    if scenario == "01":
        assert runtime.readiness(path, "synthetic-head", started=False) == "NOT_STARTED"
    elif scenario == "02":
        assert runtime.readiness(owned.file("missing.db"), "synthetic-head", started=True) == (
            "DATABASE_UNAVAILABLE")
        assert not owned.file("missing.db").exists()
    elif scenario == "03":
        assert runtime.readiness(path, "future", started=True) == "SCHEMA_INCOMPATIBLE"
    elif scenario == "04":
        with closing(sqlite3.connect(path)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("INSERT INTO probe VALUES (2,'committed-WAL')")
            writer.commit()
            record = backup_database(owned, path, owned.file("backup.db"), "synthetic-head")
        database_check(owned, owned.file("backup.db"), "synthetic-head", record["state_signature"])
        with closing(sqlite3.connect(owned.file("backup.db"))) as reader:
            assert reader.execute("SELECT COUNT(*) FROM probe").fetchone() == (2,)
    elif scenario in {"05", "06"}:
        backup = owned.file("backup.db")
        record = backup_database(owned, path, backup, "synthetic-head")
        if scenario == "05":
            backup.write_bytes(backup.read_bytes()[:100])
        else:
            record["state_signature"] = "0" * 64
        with pytest.raises(DeliveryError):
            restore_database(owned, backup, path, record)
        assert path.read_bytes() == before
    elif scenario == "07":
        backup = owned.file("backup.db")
        record = backup_database(owned, path, backup, "synthetic-head")
        monkeypatch.setattr("delivery.os.replace", lambda *_: (_ for _ in ()).throw(
            InterruptedError("synthetic interruption")))
        with pytest.raises(InterruptedError):
            restore_database(owned, backup, path, record)
        assert path.read_bytes() == before
        assert not owned.file(path.name + ".restore-partial").exists()
    elif scenario in {"08", "09"}:
        error = PermissionError("synthetic denied") if scenario == "08" else OSError(
            errno.ENOSPC, "synthetic full disk")
        monkeypatch.setattr("delivery.os.replace", lambda *_: (_ for _ in ()).throw(error))
        with pytest.raises(OSError):
            backup_database(owned, path, owned.file("backup.db"), "synthetic-head")
        assert not owned.file("backup.db").exists()
        assert not owned.file("backup.db.partial").exists()
        assert path.read_bytes() == before
    elif scenario == "10":
        monkeypatch.setenv("INCOME_ENV", "production")
        monkeypatch.setenv("INCOME_AUTH_MODE", "local")
        monkeypatch.setenv("INCOME_DATA_ROOT", str(owned.root))
        monkeypatch.setenv("INCOME_ANALYTICS_DATABASE", str(path))
        with pytest.raises(RuntimeError, match="Firebase"):
            validate_configuration()
    elif scenario == "11":
        from firebase_admin import auth

        from income_analytics.infrastructure import firebase_identity

        monkeypatch.setattr(firebase_identity, "firebase_app", lambda: object())

        def denied(token, *, app, check_revoked):
            assert check_revoked is True
            raise ValueError("synthetic invalid or revoked token")

        monkeypatch.setattr(auth, "verify_id_token", denied)
        with pytest.raises(ValueError, match="invalid"):
            firebase_identity.identity_provider.verify_id_token("synthetic-token")
    elif scenario in {"12", "13", "14", "15"}:
        from income_analytics.infrastructure.operational_provider import (
            ProviderUnavailable,
            fetch_json,
        )

        fault = {"12": TimeoutError(), "13": 429, "14": 500, "15": b"invalid-json"}[scenario]
        calls = []

        def transport(timeout):
            calls.append(timeout)
            if isinstance(fault, Exception):
                raise fault
            return (fault, b"{}") if isinstance(fault, int) else (200, fault)

        with pytest.raises(ProviderUnavailable):
            fetch_json(transport, attempts=2, sleep=lambda _: None)
        assert len(calls) <= 2 and all(value == 5 for value in calls)
    elif scenario in {"16", "17"}:
        caplog.set_level(logging.INFO, logger="income.operations")
        runtime.Signals().event("backup_completed")
        with pytest.raises(ValueError):
            runtime.Signals().event("Bearer synthetic-token; portfolio=R$ 987654")
        assert "synthetic-token" not in caplog.text and "987654" not in caplog.text
        assert json.loads(caplog.records[-1].getMessage())["event_id"] == "backup_completed"
    elif scenario == "18":
        with pytest.raises(DeliveryError, match="PATH_NOT_OWNED"):
            backup_database(owned, path, owned.root.parent / "forbidden.db", "synthetic-head")
    elif scenario == "19":
        workspace = Workspace()
        cleanup = workspace.temporary.cleanup
        monkeypatch.setattr(workspace.temporary, "cleanup", lambda: (_ for _ in ()).throw(
            PermissionError("synthetic cleanup denied")))
        with pytest.raises(DeliveryError, match="CLEANUP_FAILED"):
            workspace.cleanup()
        cleanup()
    elif scenario == "20":
        with pytest.raises(DeliveryError, match="ROLLBACK_BLOCKED"):
            rollback_compatibility(owned, path, {"head": "old"}, {"head": "new"})
        assert path.read_bytes() == before
    elif scenario == "21":
        expected = {"checkout_sha": "a" * 40, "run_id": 1, "run_attempt": 1,
                    "source_fingerprint": "b" * 64, "governance_policy_sha256": "c" * 64,
                    "artifact_id": 2, "artifact_digest": "sha256:" + "d" * 64}
        receipt = dict(expected, operational_state="OPERATIONAL_PASS")
        assert validate_receipt(receipt, expected) == "VERIFIED"
        receipt["artifact_digest"] = "sha256:" + "e" * 64
        with pytest.raises(DeliveryError):
            validate_receipt(receipt, expected)
    elif scenario == "22":
        client = TestClient(runtime.OperationalMiddleware(Starlette()))
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}
        assert str(path) not in response.text
    elif scenario == "23":
        monkeypatch.setenv("INCOME_OPERATIONAL_TOKEN", "synthetic-operator-" + "x" * 32)
        client = TestClient(runtime.OperationalMiddleware(Starlette()))
        assert client.get("/health/status").status_code == 401
        response = client.get("/health/status", headers={"Authorization": "Bearer other-user"})
        assert response.status_code == 401
    elif scenario == "24":
        async def success(request):
            return JSONResponse({"status": "ok"})

        monkeypatch.setattr(runtime.signals, "request", lambda *_a, **_k: (_ for _ in ()).throw(
            RuntimeError("synthetic monitor failure")))
        app = runtime.OperationalMiddleware(Starlette(routes=[Route("/probe", success)]))
        client = TestClient(app)
        assert client.get("/probe").status_code == 200
        assert "OPERATIONAL_MONITORING_FAILED" in caplog.text
    elif scenario == "25":
        with pytest.raises(DeliveryError, match="PRODUCTION_NOT_AUTHORIZED"):
            production_request("production", authorization="financial-blocked")


def test_health_failure_and_recovery_do_not_load_financial_session(owned, monkeypatch):
    path = seed(owned)
    monkeypatch.setenv("INCOME_ANALYTICS_DATABASE", str(path))
    monkeypatch.setattr(runtime, "expected_schema", lambda: "synthetic-head")
    collector = runtime.Signals()
    monkeypatch.setattr(runtime, "signals", collector)
    with TestClient(runtime.OperationalMiddleware(Starlette())) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 200
        path.rename(path.with_suffix(".offline"))
        assert client.get("/health/ready").status_code == 503
        path.with_suffix(".offline").rename(path)
        assert client.get("/health/ready").status_code == 200
    assert collector.snapshot()["process_up"] == 0
    assert collector.counts["readiness_recovered"] == 2
    assert collector.counts["health_degraded"] == 1


@pytest.mark.parametrize("fault", ["failed", "errors", "skipped", "missing", "duplicate", "empty"])
def test_gate_incomplete_execution_never_passes(fault):
    details = healthy_details()
    if fault in {"failed", "errors", "skipped"}:
        details["totals"][fault] = 1
    elif fault == "missing":
        details["cases"].pop()
    elif fault == "duplicate":
        details["cases"].append(details["cases"][0])
    else:
        details = {}
    assert evaluate(details) != "OPERATIONAL_PASS"


@pytest.mark.parametrize("status", ["failure", "skipped", "cancelled", None])
def test_operational_job_blocks_engineering(status):
    report = dict(
        healthy_details(), operational_state="OPERATIONAL_PASS", status="PASS", exit_code=0
    )
    result = require_operational({"engineering_ci": "PASS"}, report, status)
    assert result["engineering_ci"] == "FAIL"
    assert result["production"] == "PRODUCTION_NOT_AUTHORIZED"


def test_retention_parameterized_validated_and_never_deletes(owned):
    path = seed(owned)
    now = datetime(2026, 10, 29, tzinfo=UTC)
    records = []
    for day in (0, 1, 8, 40, 110):
        destination = owned.file(f"backup-{day}.db")
        record = backup_database(owned, path, destination, "synthetic-head")
        record.update(path=str(destination), created_at=(now - timedelta(days=day)).isoformat())
        records.append(record)
    plan = retention_plan(owned, records, now=now)
    assert plan["deletion_authorized"] is False
    assert "backup-0.db" in plan["keep"] and "backup-110.db" in plan["candidates"]
    assert all(Path(row["path"]).is_file() for row in records)
    records[0]["sha256"] = "0" * 64
    with pytest.raises(DeliveryError, match="DIGEST"):
        retention_plan(owned, records, now=now)


def test_backup_repeated_and_retry_after_failure(owned, monkeypatch):
    path = seed(owned)
    destination = owned.file("backup.db")
    replace = __import__("os").replace
    with monkeypatch.context() as patch:
        patch.setattr("delivery.os.replace", lambda *_: (_ for _ in ()).throw(PermissionError()))
        with pytest.raises(PermissionError):
            backup_database(owned, path, destination, "synthetic-head")
    assert __import__("os").replace is replace
    record = backup_database(owned, path, destination, "synthetic-head")
    with pytest.raises(DeliveryError, match="BACKUP_ALREADY_EXISTS"):
        backup_database(owned, path, destination, "synthetic-head")
    result = restore_database(owned, destination, owned.file("alternate.db"), record)
    assert result["status"] == "PASS"


def test_metrics_fixed_labels_and_no_payload():
    collector = runtime.Signals()
    collector.request(500, 0.2, importing=True)
    collector.request(401, 0.1)
    collector.request(403, 0.1)
    metrics = collector.snapshot()
    assert metrics["counts"]["http_5xx"] == 1
    assert metrics["counts"]["import_failed"] == 1
    assert metrics["counts"]["authentication_failed"] == 1
    assert metrics["http_5xx_rate"] == 1 / 3


def test_backup_snapshot_handles_commit_between_validation_and_copy(owned, monkeypatch):
    import delivery

    path = seed(owned)
    check = delivery.database_check
    changed = False

    def validate_then_commit(workspace, file, head, signature=None):
        nonlocal changed
        result = check(workspace, file, head, signature)
        if file == path and not changed:
            with closing(sqlite3.connect(path)) as writer:
                writer.execute("PRAGMA journal_mode=WAL")
                writer.execute("INSERT INTO probe VALUES (2,'committed-after-precheck')")
                writer.commit()
            changed = True
        return result

    monkeypatch.setattr(delivery, "database_check", validate_then_commit)
    record = backup_database(owned, path, owned.file("backup.db"), "synthetic-head")
    assert changed
    check(owned, owned.file("backup.db"), "synthetic-head", record["state_signature"])
    with closing(sqlite3.connect(owned.file("backup.db"))) as reader:
        assert reader.execute("SELECT COUNT(*) FROM probe").fetchone() == (2,)


def test_restore_refuses_live_wal_and_preserves_it(owned):
    path = seed(owned)
    backup = owned.file("backup.db")
    record = backup_database(owned, path, backup, "synthetic-head")
    with closing(sqlite3.connect(path)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("INSERT INTO probe VALUES (2,'uncheckpointed')")
        writer.commit()
        wal = path.with_name(path.name + "-wal")
        data = wal.read_bytes()
        with pytest.raises(DeliveryError, match="QUIESCENT"):
            restore_database(owned, backup, path, record)
        assert wal.read_bytes() == data


def test_readonly_probe_lock_and_recovery(owned):
    path = seed(owned)
    with closing(sqlite3.connect(path)) as writer:
        writer.execute("BEGIN EXCLUSIVE")
        assert runtime.readiness(path, "synthetic-head", started=True) == "DATABASE_UNAVAILABLE"
        writer.rollback()
    assert runtime.readiness(path, "synthetic-head", started=True) == "READY"


@pytest.mark.parametrize("fault", ["dns", "invalid", "partial", "quota", "missing-credential"])
def test_actual_brapi_batch_transport_fails_without_fabricating_quotes(monkeypatch, fault):
    from urllib.error import HTTPError, URLError

    from income_analytics.application.market_data import MarketDataUnavailable
    from income_analytics.infrastructure import brapi_market_data

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"invalid-json" if fault == "invalid" else b'{"results":[]}'

    def transport(request, timeout):
        assert timeout == 5
        if fault == "dns":
            raise URLError("synthetic-DNS")
        if fault in {"quota", "missing-credential"}:
            raise HTTPError("https://synthetic.invalid", 429 if fault == "quota" else 401,
                            "synthetic", {}, None)
        return Response()

    monkeypatch.setattr(brapi_market_data, "urlopen", transport)
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)
    provider = brapi_market_data.BrapiMarketDataProvider()
    if fault == "partial":
        assert provider.latest_prices(("SYNTHETIC",)) == {}
    else:
        with pytest.raises(MarketDataUnavailable):
            provider.latest_prices(("SYNTHETIC",))


def test_status_requires_distinct_operator_credential_and_never_discloses_it(monkeypatch):
    key = "synthetic-operator-" + "x" * 32
    monkeypatch.setenv("INCOME_OPERATIONAL_TOKEN", key)
    client = TestClient(runtime.OperationalMiddleware(Starlette()))
    response = client.get("/health/status", headers={"Authorization": "Bearer " + key})
    assert response.status_code == 200
    assert key not in response.text and "Bearer" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert client.post("/health/live").status_code == 405


def test_recovery_receipt_measures_semantic_state_without_certifying_host():
    from operational import recovery_exercise

    result = recovery_exercise()
    assert result["status"] == "PASS" and result["synthetic_rows_lost"] == 0
    assert result["host_rpo_rto_certified"] is False


def test_backup_during_concurrent_wal_commits(owned):
    from threading import Event, Thread

    path = seed(owned)
    started, stop = Event(), Event()
    errors = []

    def writer():
        try:
            with closing(sqlite3.connect(path)) as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                for number in range(2, 102):
                    connection.execute("INSERT INTO probe VALUES (?,?)", (number, "synthetic"))
                    connection.commit()
                    started.set()
                    if stop.wait(0.001):
                        break
        except Exception as error:
            errors.append(type(error).__name__)
            started.set()

    thread = Thread(target=writer)
    thread.start()
    try:
        assert started.wait(5)
        record = backup_database(owned, path, owned.file("concurrent.db"), "synthetic-head")
    finally:
        stop.set()
        thread.join(5)
    assert not thread.is_alive() and not errors
    database_check(owned, owned.file("concurrent.db"), "synthetic-head", record["state_signature"])
    with closing(sqlite3.connect(owned.file("concurrent.db"))) as reader:
        count, maximum = reader.execute("SELECT COUNT(*),MAX(id) FROM probe").fetchone()
        assert count == maximum and count >= 2


def test_startup_failure_never_sets_ready(monkeypatch):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def failed_startup(app):
        raise RuntimeError("synthetic startup failure")
        yield

    collector = runtime.Signals()
    monkeypatch.setattr(runtime, "signals", collector)
    with pytest.raises(RuntimeError, match="synthetic startup"):
        with TestClient(runtime.OperationalMiddleware(Starlette(lifespan=failed_startup))):
            pass
    assert collector.started is False
    assert collector.counts["application_startup_failed"] == 1


def test_operational_missing_or_invalid_semantic_receipt_blocks_even_successful_job():
    report = dict(
        healthy_details(), operational_state="OPERATIONAL_PASS", status="PASS", exit_code=0
    )
    result = require_operational({"engineering_ci": "PASS"}, report, "success")
    assert result["engineering_ci"] == "FAIL"
    report["recovery"] = {"status": "PASS", "synthetic_rows_lost": 0,
                          "host_rpo_rto_certified": False}
    result = require_operational({"engineering_ci": "PASS"}, report, "success")
    assert result["engineering_ci"] == "PASS"


def test_backup_lifecycle_events_are_allowlisted_and_payload_free(owned, caplog, monkeypatch):
    caplog.set_level(logging.INFO, logger="income.operations")
    path = seed(owned)
    backup_database(owned, path, owned.file("backup.db"), "synthetic-head")
    monkeypatch.setattr("delivery.os.replace", lambda *_: (_ for _ in ()).throw(
        PermissionError("synthetic-sensitive-payload")))
    with pytest.raises(PermissionError):
        backup_database(owned, path, owned.file("failed.db"), "synthetic-head")
    events = [json.loads(record.getMessage())["event_id"] for record in caplog.records
              if record.name == "income.operations"]
    assert events == ["backup_started", "backup_completed", "backup_started", "backup_failed"]
    assert str(path) not in caplog.text and "synthetic-sensitive-payload" not in caplog.text


def test_dependency_latency_metrics_have_no_provider_or_financial_labels():
    collector = runtime.Signals()
    collector.dependency(0.2)
    collector.dependency(0.4)
    result = collector.snapshot()
    assert result["counts"]["dependency_checks"] == 2
    assert result["dependency_mean_seconds"] == pytest.approx(0.3)


@pytest.mark.parametrize("mode", ["success", "timeout", "nonzero"])
def test_graceful_shutdown_failure_cannot_be_waived(owned, mode):
    import subprocess

    from delivery_stage import Server

    class Process:
        returncode = None
        calls = 0

        def poll(self):
            return self.returncode

        def wait(self, timeout):
            self.calls += 1
            if self.calls == 1:
                assert timeout == 30
                if mode == "timeout":
                    raise subprocess.TimeoutExpired("synthetic-process", timeout)
            self.returncode = 1 if mode == "nonzero" else 0

        def terminate(self):
            self.returncode = -1

    server = Server.__new__(Server)
    server.stop_file = owned.file("synthetic-stop.flag")
    server.process = Process()
    if mode == "success":
        server.stop()
        assert server.stop_seconds >= 0 and server.stop_file.read_text() == "stop"
    else:
        with pytest.raises(DeliveryError, match="GRACEFUL_STOP_FAILED_"):
            server.stop()


def test_retention_bucket_counts_respect_exact_limits_at_calendar_boundaries(owned):
    source = seed(owned)
    now = datetime(2026, 10, 29, 12, tzinfo=UTC)
    records = []
    for day in range(0, 90):
        path = owned.file(f"daily-{day}.db")
        record = backup_database(owned, source, path, "synthetic-head")
        record.update(path=str(path), created_at=(now - timedelta(days=day)).isoformat())
        records.append(record)
    result = retention_plan(owned, records, now=now, daily=7, weekly=4, monthly=3)
    assert result["bucket_counts"] == {"daily": 7, "weekly": 4, "monthly": 3}
    assert len(result["keep"]) <= 14 and result["deletion_authorized"] is False
