"""Parametrized disposable installation and real process/SQLite recovery exercises."""

import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from contextlib import closing

from artifact import PYTHON, sha, verify
from delivery import (
    DeliveryError,
    Workspace,
    backup_database,
    database_check,
    immutable_copy,
    require,
    restore_database,
    rollback_compatibility,
    schema_contract,
    select_version,
    verify_selection,
)
from smoke_artifact import GUARD

RUN_SERVER = """import os, sys, threading, time
from pathlib import Path
import uvicorn
import importlib.util
source = Path(importlib.util.find_spec("income_analytics.main").origin).resolve()
assert source.is_relative_to((Path.cwd() / "src").resolve()), "WRONG_APPLICATION_SOURCE"
server = uvicorn.Server(uvicorn.Config(sys.argv[1], host="127.0.0.1",
    port=int(sys.argv[2]), access_log=False, log_level="warning"))
def wait_for_stop():
    while not Path(os.environ["DELIVERY_STOP_FILE"]).exists():
        time.sleep(0.05)
    server.should_exit = True
threading.Thread(target=wait_for_stop, daemon=True).start()
try:
    server.run()
finally:
    from income_analytics.infrastructure.database import engine
    engine.dispose()
"""


def execute(args, cwd, env, label):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=240)
    require(result.returncode == 0, "INSTALLATION_FAILED_" + label)


def environment(workspace, root, database, overrides=None):
    require(overrides is None, "PRODUCTION_CONFIGURATION_NOT_ALLOWED")
    root, database = workspace.safe(root), workspace.safe(database)
    state = workspace.file("state")
    state.mkdir(exist_ok=True)
    guard = workspace.file("guard")
    guard.mkdir(exist_ok=True)
    (guard / "sitecustomize.py").write_text(GUARD, encoding="utf-8")
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"}
    }
    env.update(
        {
            "HOME": str(state),
            "USERPROFILE": str(state),
            "TEMP": str(state),
            "TMP": str(state),
            "TMPDIR": str(state),
            "PYTHONUTF8": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": os.pathsep.join((str(guard), str(root / "src"))),
            "INCOME_ENV": "development",
            "INCOME_AUTH_MODE": "local",
            "INCOME_PUBLIC_SIGNUP_ENABLED": "0",
            "INCOME_ANALYTICS_TESTING": "1",
            "INCOME_ANALYTICS_DISABLE_BACKGROUND_JOBS": "1",
            "INCOME_ANALYTICS_DATABASE": str(database),
            "INCOME_ANALYTICS_COTAHIST_CACHE": str(state / "cotahist"),
            "GOOGLE_APPLICATION_CREDENTIALS": str(state / "absent-credentials.json"),
            "CLOUDSDK_CONFIG": str(state / "absent-cloud"),
        }
    )
    return env


def install(workspace, archive, identity, slot, database):
    require(sys.version.split()[0] == PYTHON and sys.platform == "win32", "WRONG_TARGET_RUNTIME")
    require(slot in {"A", "B"}, "INVALID_VERSION_SLOT")
    verify(archive, identity["source_commit"], identity["package_sha256"])
    root = workspace.file("application-" + slot)
    require(not root.exists(), "VERSION_SLOT_ALREADY_INSTALLED")
    root.mkdir()
    with zipfile.ZipFile(archive) as package:
        package.extractall(root)
    env = environment(workspace, root, database)
    venv = workspace.file("venv-" + slot)
    execute([sys.executable, "-m", "venv", str(venv)], root, env, "VENV")
    python = venv / "Scripts/python.exe"
    execute(
        [
            str(python),
            "-m",
            "pip",
            "--isolated",
            "install",
            "--no-index",
            "--find-links",
            str(root / "wheelhouse"),
            "--require-hashes",
            "--only-binary=:all:",
            "-r",
            "requirements.lock",
        ],
        root,
        env,
        "WHEELS_OFFLINE",
    )
    execute([str(python), "-m", "pip", "check"], root, env, "PIP_CHECK")
    execute(
        [str(python), "-c", "from income_analytics.main import app; assert app"],
        root,
        env,
        "IMPORT",
    )
    return {
        "slot": slot,
        "archive": archive,
        "root": root,
        "python": python,
        "env": env,
        "identity": identity,
        "contract": schema_contract(archive),
    }


def verify_installed(workspace, installed):
    verify_selection(workspace, installed["slot"], installed["archive"], installed["identity"])
    with zipfile.ZipFile(installed["archive"]) as package:
        manifest = json.loads(package.read("manifest.json"))
    for name, record in manifest["files"].items():
        path = workspace.safe(installed["root"] / name)
        require(
            path.is_file() and sha(path.read_bytes()) == record["sha256"],
            "INSTALLATION_CONTENT_CHANGED",
        )


class Server:
    def __init__(self, workspace, installed, fault=None):
        require(fault in {None, "startup"}, "INVALID_FAULT_INJECTION")
        self.expected_startup_failure = fault == "startup"
        verify_installed(workspace, installed)
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            self.port = reserve.getsockname()[1]
        target = "income_analytics.main:app"
        if fault == "startup":
            target = "income_analytics.__delivery_missing__:app"
        self.stop_file = workspace.file(f"stop-{len(workspace.processes)}.flag")
        env = {**installed["env"], "DELIVERY_STOP_FILE": str(self.stop_file)}
        # Private owned diagnostics are cleaned with the disposable workspace.
        # Never publish raw child output or productive process information.
        self.diagnostics = workspace.file(f"server-{len(workspace.processes)}.private.log")
        with self.diagnostics.open("wb") as output:
            self.process = subprocess.Popen(
                [str(installed["python"]), "-c", RUN_SERVER, target, str(self.port)],
                cwd=installed["root"], env=env, stdout=output, stderr=output,
            )
        workspace.processes.append(self.process)
        workspace.ports.append(self.port)

    def health(self, path="/health", timeout=45):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic() + timeout
        while True:
            require(self.process.poll() is None, "STARTUP_FAILED")
            try:
                with opener.open(f"http://127.0.0.1:{self.port}{path}", timeout=2) as response:
                    require(
                        response.status == 200 and json.load(response) == {"status": "ok"},
                        "HEALTH_REJECTED",
                    )
                    return "PASS"
            except urllib.error.HTTPError:
                raise DeliveryError("HEALTH_REJECTED") from None
            except urllib.error.URLError, TimeoutError:
                require(time.monotonic() < deadline, "HEALTH_TIMEOUT")
                time.sleep(0.1)

    def static(self):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for path, content in (("/", b"<!"), ("/static/css/app.css", b"{")):
            with opener.open(f"http://127.0.0.1:{self.port}{path}", timeout=5) as response:
                require(response.status == 200 and content in response.read(), "STATIC_FAILED")

    def stop(self):
        started = time.monotonic()
        if self.process.poll() is None:
            # File-based control belongs to this disposable process only; no
            # console signal, production PID or application endpoint is targeted.
            self.stop_file.write_text("stop", encoding="ascii")
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=10)
                raise DeliveryError("GRACEFUL_STOP_FAILED_TIMEOUT") from None
        require(self.process.poll() is not None, "PROCESS_STOP_FAILED")
        require(self.process.returncode == 0 or self.expected_startup_failure,
                "GRACEFUL_STOP_FAILED_EXIT")
        self.stop_seconds = round(time.monotonic() - started, 6)


def expect_failure(action, codes):
    try:
        action()
    except DeliveryError as error:
        require(str(error) in codes, "UNEXPECTED_FAULT_RESULT")
        return {"status": "EXPECTED_FAILURE_OBSERVED", "reason": str(error)}
    raise DeliveryError("EXPECTED_FAILURE_NOT_OBSERVED")


def exercise(previous_archive, candidate_archive, previous, candidate, result):
    workspace = Workspace()
    result["cleanup"] = {"status": "NOT_RUN"}
    try:
        database = workspace.file("state/staging.db")
        database.parent.mkdir()
        a = immutable_copy(workspace, previous_archive, workspace.file("version-A.zip"), previous)
        b = immutable_copy(workspace, candidate_archive, workspace.file("version-B.zip"), candidate)
        require(
            previous["package_sha256"] != candidate["package_sha256"],
            "ROLLBACK_REQUIRES_DISTINCT_ARTIFACT_VERSIONS",
        )
        version_a = install(workspace, a, previous, "A", database)
        execute(
            [str(version_a["python"]), "-m", "alembic", "upgrade", "head"],
            version_a["root"],
            version_a["env"],
            "TEMPORARY_MIGRATIONS",
        )
        select_version(workspace, "A", previous)
        server_a = Server(workspace, version_a)
        try:
            server_a.health()
            server_a.static()
        finally:
            server_a.stop()
        result["known_good_A"] = {
            "status": "PASS",
            "commit": previous["source_commit"],
            "sha256": previous["package_sha256"],
        }
        # WAL remains open while backing up; SQLite's backup API sees committed
        # pages that a naive copy of the main file would miss.
        with closing(sqlite3.connect(database)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("CREATE TABLE delivery_probe (id INTEGER PRIMARY KEY, value TEXT)")
            writer.execute("INSERT INTO delivery_probe VALUES (1,'known-synthetic-state')")
            writer.commit()
            backup = workspace.file("before-candidate.db")
            record = backup_database(workspace, database, backup, version_a["contract"]["head"])
            writer.execute("UPDATE delivery_probe SET value='changed-after-backup'")
            writer.commit()
        result["backup"] = record
        result["negative_restore_changed_state"] = expect_failure(
            lambda: database_check(
                workspace, database, record["schema_head"], record["state_signature"]
            ),
            {"RESTORE_STATE_MISMATCH"},
        )
        result["restore"] = restore_database(workspace, backup, database, record)
        version_b = install(workspace, b, candidate, "B", database)
        rollback_compatibility(workspace, database, version_a["contract"], version_b["contract"])
        execute(
            [str(version_b["python"]), "-m", "alembic", "upgrade", "head"],
            version_b["root"],
            version_b["env"],
            "CANDIDATE_TEMPORARY_MIGRATIONS",
        )
        select_version(workspace, "B", candidate)
        server_b = Server(workspace, version_b)
        try:
            server_b.health()
            server_b.static()
            result["installation"] = {"status": "PASS", "offline": True}
            result["health"] = {"status": "PASS", "bind": "127.0.0.1", "static": "PASS"}
            result["negative_health"] = expect_failure(
                lambda: server_b.health("/__delivery_injected_bad_health__"), {"HEALTH_REJECTED"}
            )
        finally:
            server_b.stop()
        result["graceful_shutdown"] = {
            "status": "PASS", "seconds": server_b.stop_seconds,
            "exit_code": server_b.process.returncode, "forced_stop": False,
        }
        # A second real process demonstrates startup failure independently of
        # HTTP failure. Neither injection changes the immutable package bytes.
        failed_server = Server(workspace, version_b, fault="startup")
        try:
            result["negative_startup"] = expect_failure(failed_server.health, {"STARTUP_FAILED"})
        finally:
            failed_server.stop()
        result["rollback_events"] = [
            "A_HEALTHY",
            "BACKUP_VERIFIED",
            "B_SELECTED_AND_HEALTHY",
            "B_HEALTH_FAILURE_OBSERVED",
            "B_STARTUP_FAILURE_OBSERVED",
        ]
        recovery_started = time.monotonic()
        rollback_compatibility(workspace, database, version_a["contract"], version_b["contract"])
        select_version(workspace, "A", previous)
        verify(a, previous["source_commit"], previous["package_sha256"])
        recovered = Server(workspace, version_a)
        try:
            recovered.health()
            recovered.static()
            verify_selection(workspace, "A", a, previous)
            database_check(workspace, database, record["schema_head"], record["state_signature"])
            recovery_seconds = round(time.monotonic() - recovery_started, 6)
        finally:
            recovered.stop()
        result["rollback_events"] += ["A_RESELECTED", "A_DIGEST_VERIFIED", "A_RESTARTED_HEALTHY"]
        result["rollback"] = {
            "status": "PASS",
            "application_digest": previous["package_sha256"],
            "schema_compatibility": "EXACT_MIGRATION_IDENTITY",
            "state_signature": record["state_signature"],
            "downgrade": "NOT_RUN",
            "recovery_seconds": recovery_seconds,
            "measurement_boundary": (
                "ROLLBACK_DECISION_TO_APP_HEALTH_STATIC_AND_SEMANTIC_VALIDATION"
            ),
            "host_rpo_rto_certified": False,
        }
        with closing(sqlite3.connect(database)) as synthetic:
            synthetic.execute("UPDATE alembic_version SET version_num='synthetic-future-schema'")
            synthetic.commit()
        result["incompatible_schema"] = expect_failure(
            lambda: rollback_compatibility(
                workspace, database, version_a["contract"], version_b["contract"]
            ),
            {"SCHEMA_INCOMPATIBLE"},
        )
        result["incompatible_schema"].update(
            status="BLOCKED",
            safe_block_verified=True,
            downgrade="NOT_RUN",
            required_action="SEPARATE_VALIDATED_RESTORE_PLAN",
        )
        # This is a separately validated restore plan for the synthetic test DB,
        # not an automatic destructive downgrade or a production recovery claim.
        result["synthetic_restore_after_block"] = restore_database(
            workspace, backup, database, record
        )
        require(
            sha(a.read_bytes()) == previous["package_sha256"]
            and sha(b.read_bytes()) == candidate["package_sha256"],
            "PROMOTION_BYTES_CHANGED",
        )
        result["immutable_promotion"] = {
            "status": "PASS",
            "candidate_sha256": sha(b.read_bytes()),
            "staging_sha256": sha(b.read_bytes()),
            "rebuild": "NOT_RUN",
        }
    finally:
        try:
            workspace.cleanup()
        except Exception:
            result["cleanup"] = {"status": "FAIL", "reason": "CLEANUP_FAILED"}
            raise
        result["cleanup"] = {
            "status": "PASS",
            "processes_stopped": True,
            "ports_released": True,
            "temporary_root_removed": True,
        }
