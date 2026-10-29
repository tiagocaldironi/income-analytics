"""Real rejection/recovery tests on temporary metadata, files, SQLite and processes."""

import json
import socket
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest
import yaml
from artifact import sha
from delivery import (
    BASELINE_COMMIT,
    BASELINE_RUN,
    REPOSITORY,
    DeliveryError,
    Workspace,
    backup_database,
    database_check,
    immutable_copy,
    production_request,
    restore_database,
    rollback_compatibility,
    select_version,
    trusted_source,
    verify_selection,
)
from delivery_pipeline import acquire, delivery_decision, envelope
from delivery_stage import Server, environment, verify_installed
from test_build_artifact import built as built


@pytest.fixture
def owned():
    workspace = Workspace()
    try:
        yield workspace
    finally:
        workspace.cleanup()


@pytest.fixture
def source():
    run = {
        "id": 123,
        "run_attempt": 1,
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
        "workflow_id": 399392307,
        "path": ".github/workflows/ci-offline.yml",
        "event": "push",
        "head_branch": "develop",
        "head_sha": "a" * 40,
        "status": "completed",
        "run_started_at": "2026-10-29T00:00:00Z",
    }
    artifact = {
        "id": 456,
        "workflow_run": {"id": 123},
        "expired": False,
        "name": "application-" + "a" * 40 + "-windows-x64",
        "digest": "sha256:" + "b" * 64,
        "created_at": "2026-10-29T00:01:00Z",
    }
    build = {
        "schema": 3,
        "status": "PASS",
        "exit_code": 0,
        "worktree_dirty": False,
        "checkout_sha": "a" * 40,
        "event_sha": "a" * 40,
        "pr_head_sha": "",
        "independent_builds": 2,
        "reproducibility": "PASS",
        "manifest": "PASS",
        "artifact_sha256": "c" * 64,
        "build_policy_sha256": "d" * 64,
        "governance_policy_sha256": "e" * 64,
        "source_fingerprint": "f" * 64,
    }
    gate = {
        "engineering_ci": "PASS",
        "reproducible_build": "PASS",
        "consistent_identity": True,
        "financial_certification": "BLOCKED",
        "release_readiness": "BLOCKED",
        "deployment_authorized": False,
    }
    jobs = [
        {"name": n, "conclusion": "success"}
        for n in ("CI / Engineering", "CI / Reproducible build")
    ]
    return {
        "run": run,
        "artifact": artifact,
        "jobs": jobs,
        "build": build,
        "gate": gate,
        "expected": "a" * 40,
        "mode": "delivery",
    }


def validated_staging():
    checks = {
        name: {"status": "PASS"}
        for name in (
            "known_good_A",
            "installation",
            "health",
            "backup",
            "restore",
            "rollback",
            "synthetic_restore_after_block",
            "immutable_promotion",
            "cleanup",
        )
    }
    checks.update(
        {
            name: {"status": "EXPECTED_FAILURE_OBSERVED"}
            for name in (
                "negative_restore_changed_state",
                "negative_health",
                "negative_startup",
            )
        }
    )
    checks["incompatible_schema"] = {"status": "BLOCKED", "safe_block_verified": True}
    return {"status": "PASS", "checks": checks}


def test_valid_technical_candidate_never_authorizes_production(source):
    identity = trusted_source(**source)
    result = delivery_decision(identity, validated_staging(), "delivery")
    assert result["promotion_status"] == "PROMOTION_ELIGIBLE"
    assert result["financial_release"] == "BLOCKED"
    assert result["production_status"] == "PRODUCTION_NOT_AUTHORIZED"
    assert result["production_authorized"] is False


@pytest.mark.parametrize(
    "missing",
    [
        "known_good_A",
        "installation",
        "health",
        "backup",
        "restore",
        "rollback",
        "synthetic_restore_after_block",
        "immutable_promotion",
        "cleanup",
        "negative_restore_changed_state",
        "negative_health",
        "negative_startup",
        "incompatible_schema",
    ],
)
def test_missing_or_not_run_operational_evidence_never_passes_staging(source, missing):
    identity = trusted_source(**source)
    result = validated_staging()
    result["checks"][missing] = {"status": "NOT_RUN"}
    with pytest.raises(DeliveryError):
        delivery_decision(identity, result, "delivery")


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("run", "repository", {"full_name": "other/repo"}),
        ("run", "head_repository", {"full_name": "fork/repo"}),
        ("run", "workflow_id", 1),
        ("run", "path", ".github/workflows/untrusted.yml"),
        ("run", "event", "pull_request"),
        ("run", "head_branch", "feature"),
        ("run", "status", "in_progress"),
        ("run", "head_sha", "b" * 40),
        ("build", "checkout_sha", "b" * 40),
        ("build", "event_sha", "b" * 40),
        ("build", "pr_head_sha", "b" * 40),
        ("build", "worktree_dirty", True),
        ("build", "status", "FAIL"),
        ("build", "independent_builds", 1),
        ("gate", "engineering_ci", "FAIL"),
        ("gate", "financial_certification", "PASS"),
        ("gate", "release_readiness", "PASS"),
        ("gate", "deployment_authorized", True),
        ("artifact", "expired", True),
        ("artifact", "name", "wrong-artifact"),
        ("artifact", "workflow_run", {"id": 999}),
        ("artifact", "created_at", "2020-01-01T00:00:00Z"),
    ],
)
def test_untrusted_or_inconsistent_metadata_is_really_rejected(source, section, key, value):
    source[section][key] = value
    with pytest.raises(DeliveryError):
        trusted_source(**source)


def test_failed_engineering_job_cannot_be_overridden_by_report(source):
    source["jobs"][0]["conclusion"] = "failure"
    with pytest.raises(DeliveryError, match="REQUIRED_JOB_FAILED"):
        trusted_source(**source)


def test_absent_artifact_is_rejected(source):
    source["artifact"] = None
    with pytest.raises(DeliveryError, match="ARTIFACT_UNAVAILABLE"):
        trusted_source(**source)


def test_transport_digest_mismatch_before_extraction():
    class Client:
        def bytes(self, path):
            return b"different remote artifact"

    with pytest.raises(DeliveryError, match="TRANSPORT_DIGEST"):
        envelope(Client(), {"id": 1, "expired": False, "digest": "sha256:" + "0" * 64})


def test_nonexistent_artifact_no_fallback_to_local_build(source, owned):
    class Client:
        def json(self, path):
            if path.startswith("compare/"):
                return {"merge_base_commit": {"sha": source["expected"]}}
            if path.endswith("artifacts?per_page=100"):
                return {"artifacts": []}
            if "jobs?" in path:
                return {"jobs": source["jobs"]}
            return source["run"]

    with pytest.raises(DeliveryError, match="ARTIFACT_UNAVAILABLE"):
        acquire(Client(), 123, source["expected"], "delivery", owned.file("candidate.zip"))
    assert not owned.file("candidate.zip").exists()


def test_premerge_exercise_is_explicitly_not_a_promotion(source):
    source["run"].update(event="pull_request", status="in_progress")
    source["build"]["pr_head_sha"] = source["run"]["head_sha"]
    source.update(mode="premerge", current_run=123)
    identity = trusted_source(**source)
    decision = delivery_decision(identity, validated_staging(), "premerge")
    assert identity["promotion_status"] == decision["promotion_status"] == "PROMOTION_BLOCKED"
    source["mode"] = "delivery"
    with pytest.raises(DeliveryError, match="UNMERGED_PR"):
        trusted_source(**source)


@pytest.mark.parametrize(
    "target,authorization",
    [("production", None), ("production", "synthetic"), ("staging", "synthetic-approval")],
)
def test_production_path_does_not_exist_even_with_purported_authorization(target, authorization):
    with pytest.raises(DeliveryError, match="PRODUCTION_NOT_AUTHORIZED"):
        production_request(target, authorization)


def test_failed_staging_or_false_financial_release_never_eligible(source):
    identity = trusted_source(**source)
    with pytest.raises(DeliveryError, match="STAGING_FAILED"):
        delivery_decision(identity, {"status": "FAIL"}, "delivery")
    identity["financial_release"] = "PASS"
    with pytest.raises(DeliveryError, match="FALSE_RELEASE"):
        delivery_decision(identity, validated_staging(), "delivery")


def seed(workspace):
    path = workspace.file("synthetic.db")
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE alembic_version (version_num TEXT)")
        db.execute("INSERT INTO alembic_version VALUES ('synthetic-head')")
        db.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO probe VALUES (1,'synthetic-initial')")
        db.commit()
    return path


def test_online_backup_restore_exact_semantics_with_open_wal_writer(owned):
    path = seed(owned)
    backup = owned.file("backup.db")
    with closing(sqlite3.connect(path)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("INSERT INTO probe VALUES (2,'committed-in-WAL')")
        writer.commit()
        record = backup_database(owned, path, backup, "synthetic-head")
        writer.execute("DELETE FROM probe")
        writer.commit()
    with pytest.raises(DeliveryError, match="RESTORE_STATE_MISMATCH"):
        database_check(owned, path, "synthetic-head", record["state_signature"])
    assert restore_database(owned, backup, path, record)["status"] == "PASS"
    with closing(sqlite3.connect(path)) as reader:
        assert reader.execute("SELECT * FROM probe ORDER BY id").fetchall() == [
            (1, "synthetic-initial"),
            (2, "committed-in-WAL"),
        ]


@pytest.mark.parametrize(
    "fault", ["missing", "wrong-digest", "corrupt", "wrong-schema", "incomplete-state"]
)
def test_bad_backup_and_restore_cannot_report_success(owned, fault):
    path = seed(owned)
    backup = owned.file("backup.db")
    record = backup_database(owned, path, backup, "synthetic-head")
    if fault == "missing":
        backup.unlink()
    elif fault == "wrong-digest":
        record["sha256"] = "0" * 64
    elif fault == "corrupt":
        backup.write_bytes(b"not a SQLite file")
        record["sha256"] = sha(backup.read_bytes())
    elif fault == "wrong-schema":
        record["schema_head"] = "future-head"
    else:
        record["state_signature"] = "0" * 64
    with pytest.raises(DeliveryError):
        restore_database(owned, backup, path, record)


def test_sqlite_structural_integrity_damage_is_rejected(owned):
    path = seed(owned)
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE INDEX probe_value ON probe(value)")
        db.execute("PRAGMA writable_schema=ON")
        db.execute("UPDATE sqlite_master SET rootpage=999999 WHERE name='probe_value'")
        db.commit()
    with pytest.raises(DeliveryError, match="SQLITE_"):
        database_check(owned, path, "synthetic-head")


def test_incompatible_schema_blocks_rollback_without_downgrade(owned):
    path = seed(owned)
    before = path.read_bytes()
    contract = {"head": "synthetic-head", "migrations_sha256": "a" * 64}
    changed = {**contract, "migrations_sha256": "b" * 64}
    with pytest.raises(DeliveryError, match="ROLLBACK_BLOCKED_SCHEMA"):
        rollback_compatibility(owned, path, contract, changed)
    assert path.read_bytes() == before
    with closing(sqlite3.connect(path)) as db:
        db.execute("UPDATE alembic_version SET version_num='future-schema'")
        db.commit()
    with pytest.raises(DeliveryError, match="SCHEMA_INCOMPATIBLE"):
        rollback_compatibility(owned, path, contract, contract)


@pytest.mark.parametrize(
    "name",
    [
        "C:/Users/tiago/.codex/worktrees/firebase-official-merge/Projetos/income-analytics/income_analytics.db",
        "C:/Users/tiago/AppData/Local/IncomeAnalytics/production.db",
    ],
)
def test_known_production_paths_rejected_before_database_access(owned, name):
    with pytest.raises(DeliveryError, match="PATH_NOT_OWNED"):
        database_check(owned, Path(name), "any-head")


def test_production_secret_overrides_rejected_and_inherited_credentials_removed(owned, monkeypatch):
    monkeypatch.setenv("BRAPI_TOKEN", "synthetic-secret")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "synthetic-production-project")
    monkeypatch.setenv("INCOME_ENV", "production")
    root, database = owned.file("app"), owned.file("test.db")
    root.mkdir()
    with pytest.raises(DeliveryError, match="PRODUCTION_CONFIGURATION"):
        environment(owned, root, database, {"BRAPI_TOKEN": "synthetic-secret"})
    env = environment(owned, root, database)
    assert env["INCOME_ENV"] == "development" and env["INCOME_AUTH_MODE"] == "local"
    assert "BRAPI_TOKEN" not in env and "FIREBASE_PROJECT_ID" not in env
    assert Path(env["INCOME_ANALYTICS_DATABASE"]).is_relative_to(owned.root)
    assert "synthetic-secret" not in json.dumps(env)


def test_immutable_copy_digest_manifest_and_logical_id(built, owned):
    _, _, archive, commit = built
    identity = {"source_commit": commit, "package_sha256": sha(archive.read_bytes())}
    target = owned.file("A.zip")
    immutable_copy(owned, archive, target, identity)
    assert archive.read_bytes() == target.read_bytes()
    with pytest.raises(DeliveryError, match="ALREADY_EXISTS"):
        immutable_copy(owned, archive, target, identity)
    identity["package_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="DIGEST_MISMATCH"):
        immutable_copy(owned, archive, owned.file("B.zip"), identity)


def test_altered_manifest_is_not_promotable(built, owned):
    from test_build_artifact import rewrite

    _, _, archive, commit = built
    rewrite(archive, {"manifest.json": b"{}"})
    identity = {"source_commit": commit, "package_sha256": sha(archive.read_bytes())}
    with pytest.raises((ValueError, KeyError)):
        immutable_copy(owned, archive, owned.file("A.zip"), identity)


def test_partial_rollback_pointer_rejected(owned):
    archive = owned.file("A.zip")
    archive.write_bytes(b"synthetic-package")
    identity = {"source_commit": "a" * 40, "package_sha256": sha(archive.read_bytes())}
    select_version(owned, "A", identity)
    verify_selection(owned, "A", archive, identity)
    bad = {**identity, "package_sha256": "0" * 64}
    select_version(owned, "A", bad)
    with pytest.raises(DeliveryError, match="PARTIAL_ROLLBACK"):
        verify_selection(owned, "A", archive, identity)


def installed_synthetic(built, owned):
    import zipfile

    _, _, archive, commit = built
    copy = owned.file("A.zip")
    copy.write_bytes(archive.read_bytes())
    root = owned.file("app")
    root.mkdir()
    with zipfile.ZipFile(copy) as bundle:
        bundle.extractall(root)
    identity = {"source_commit": commit, "package_sha256": sha(copy.read_bytes())}
    select_version(owned, "A", identity)
    return {
        "slot": "A",
        "archive": copy,
        "identity": identity,
        "root": root,
        "python": Path(sys.executable),
        "env": environment(owned, root, owned.file("test.db")),
    }


def test_installed_content_or_wrong_slot_cannot_fake_rollback(built, owned):
    installed = installed_synthetic(built, owned)
    verify_installed(owned, installed)
    (installed["root"] / "src/income_analytics/main.py").write_text("# altered after install")
    with pytest.raises(DeliveryError, match="INSTALLATION_CONTENT_CHANGED"):
        verify_installed(owned, installed)


def test_real_startup_failure_terminates_owned_process(built, owned):
    installed = installed_synthetic(built, owned)
    server = Server(owned, installed, fault="startup")
    try:
        assert server.process.wait(timeout=20) != 0
        with pytest.raises(DeliveryError, match="STARTUP_FAILED"):
            server.health()
    finally:
        server.stop()


def test_real_port_leak_blocks_cleanup_then_can_be_recovered():
    workspace = Workspace()
    listener = socket.socket()
    try:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        workspace.ports.append(listener.getsockname()[1])
        with pytest.raises(DeliveryError, match="PROCESS_OR_PORT_LEAK"):
            workspace.cleanup()
    finally:
        listener.close()
        workspace.cleanup()


def test_real_locked_file_cleanup_failure_is_not_passed():
    workspace = Workspace()
    locked = workspace.file("held-open.txt").open("w")
    try:
        locked.write("synthetic file lock")
        locked.flush()
        with pytest.raises(DeliveryError, match="CLEANUP_FAILED"):
            workspace.cleanup()
    finally:
        locked.close()
        workspace.cleanup()


def test_delivery_workflow_and_preview_preserve_read_only_boundary():
    root = Path(__file__).resolve().parents[2]
    delivery = yaml.load(
        (root / ".github/workflows/delivery-validation.yml").read_text(), Loader=yaml.BaseLoader
    )
    ci = yaml.load((root / ".github/workflows/ci-offline.yml").read_text(), Loader=yaml.BaseLoader)
    assert delivery["permissions"] == {"contents": "read", "actions": "read"}
    assert "pull_request_target" not in delivery["on"]
    assert delivery["on"]["workflow_run"]["branches"] == ["develop"]
    assert delivery["jobs"]["staging"]["runs-on"] == "windows-2025"
    assert ci["jobs"]["staging_preview"]["needs"] == ["engineering_gate", "build"]
    for job in (delivery["jobs"]["staging"], ci["jobs"]["staging_preview"]):
        assert job["name"] == "CD / Staging validation"
        assert any(s.get("run") == "python ci/delivery_pipeline.py" for s in job["steps"])
        for step in job["steps"]:
            if "uses" in step:
                assert len(step["uses"].split("@")[1]) == 40
    assert (
        BASELINE_RUN == 40856571402
        and BASELINE_COMMIT == "cc71b0be65d6fe34b97cd3305dfc7956c9a4a065"
    )
