"""Artifact-bound production execution state machine; Windows host I/O is injected."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
import urllib.parse
import zipfile
import argparse
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from production_authorization import evaluate, require_publish_confirmation
from artifact import verify
from delivery import production_request


class ProductionExecutionError(RuntimeError):
    def __init__(self, code: str, evidence: dict | None = None):
        super().__init__(code)
        self.code = code
        self.evidence = evidence or {}


class WindowsHost:
    """Local Windows implementation; only the existing launcher and release slots change."""

    def __init__(self, *, release_root: Path, database: Path, launcher: Path, health_url: str,
                 test_mode: bool = False, port: int = 8002):
        if os.name != "nt":
            raise ProductionExecutionError("WINDOWS_HOST_REQUIRED")
        self.release_root = release_root.resolve()
        self.database = database.resolve()
        self.launcher = launcher.resolve()
        self.health_url = health_url
        self.test_mode = test_mode
        self.port = port
        if not 1 <= port <= 65535 or (test_mode and port == 8002):
            raise ProductionExecutionError("TEST_PORT_MUST_BE_DISPOSABLE")
        parsed_health = urllib.parse.urlparse(health_url)
        production_health = parsed_health.scheme == "https" and parsed_health.hostname and \
            parsed_health.hostname.endswith(".ts.net")
        disposable_health = test_mode and parsed_health.scheme == "http" and \
            parsed_health.hostname in {"127.0.0.1", "localhost"}
        if not (production_health or disposable_health) or parsed_health.path.rstrip("/") != "/health":
            raise ProductionExecutionError("TAILSCALE_HTTPS_HEALTH_URL_REQUIRED")
        self.package_root: Path | None = None
        self.launcher_bytes: bytes | None = None
        self.previous_candidate: dict = {}
        self.stopped = False
        self.activated = False

    def verify_package(self, package: Path, candidate: dict):
        verify(package, candidate["source_commit"], candidate["package_sha256"])

    def create_and_verify_online_backup(self) -> dict:
        if not self.database.is_file():
            raise ProductionExecutionError("PRODUCTION_DATABASE_MISSING")
        backup_dir = self.release_root.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") +
                               "-" + uuid.uuid4().hex + ".sqlite3")
        with closing(sqlite3.connect(
            f"file:{self.database.as_posix()}?mode=ro", uri=True, timeout=5
        )) as source:
            with closing(sqlite3.connect(backup)) as target:
                source.backup(target, pages=256, sleep=0.1)
        digest = hashlib.sha256(backup.read_bytes()).hexdigest()
        with closing(sqlite3.connect(f"file:{backup.as_posix()}?mode=ro", uri=True)) as db:
            if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ProductionExecutionError("PRODUCTION_BACKUP_INTEGRITY_FAILED")
            rows = db.execute("SELECT version_num FROM alembic_version").fetchall()
            if len(rows) != 1 or not isinstance(rows[0][0], str):
                raise ProductionExecutionError("PRODUCTION_BACKUP_SCHEMA_UNKNOWN")
            head = rows[0][0]
        # Prove the backup can be opened and copied without touching the live DB.
        with tempfile.TemporaryDirectory(prefix="income-backup-check-") as directory:
            rehearsal = Path(directory) / "rehearsal.sqlite3"
            with closing(sqlite3.connect(f"file:{backup.as_posix()}?mode=ro", uri=True)) as source:
                with closing(sqlite3.connect(rehearsal)) as target:
                    source.backup(target)
            with closing(sqlite3.connect(f"file:{rehearsal.as_posix()}?mode=ro", uri=True)) as db:
                if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise ProductionExecutionError("PRODUCTION_BACKUP_RESTORE_REHEARSAL_FAILED")
        if hashlib.sha256(backup.read_bytes()).hexdigest() != digest:
            raise ProductionExecutionError("PRODUCTION_BACKUP_CHANGED_DURING_REHEARSAL")
        return {"status": "PASS", "path": str(backup), "sha256": digest, "schema_head": head}

    def preserve_previous_release(self) -> dict:
        if not self.launcher.is_file():
            raise ProductionExecutionError("PRODUCTION_LAUNCHER_MISSING")
        self.launcher_bytes = self.launcher.read_bytes()
        content = self.launcher_bytes.decode("utf-8-sig")
        locations = re.findall(r"(?m)^\s*Set-Location\s+-LiteralPath\s+'([^']+)'\s*$", content)
        if len(locations) != 1:
            raise ProductionExecutionError("LAUNCHER_LOCATION_NOT_UNIQUE")
        old_root = Path(locations[0]).resolve()
        result = subprocess.run(
            ["git", "-C", str(old_root), "rev-parse", "HEAD"], capture_output=True,
            text=True, check=False,
        )
        old_commit = result.stdout.strip()
        if result.returncode or not re.fullmatch(r"[0-9a-f]{40}", old_commit):
            raise ProductionExecutionError("PREVIOUS_VERSION_IDENTITY_UNKNOWN")
        dirty = subprocess.run(
            ["git", "-C", str(old_root), "status", "--porcelain", "--untracked-files=normal"],
            capture_output=True, text=True, check=False,
        )
        if dirty.returncode or dirty.stdout.strip():
            raise ProductionExecutionError("PREVIOUS_VERSION_DIRTY_OR_UNKNOWN")
        live_health = self.health_check({})
        live_commit = live_health.get("release_commit")
        if live_commit and live_commit != old_commit:
            raise ProductionExecutionError("RUNNING_VERSION_DOES_NOT_MATCH_LAUNCHER")
        self.previous_candidate = {
            "source_commit": old_commit,
            "legacy_health_without_commit": not bool(live_commit),
        }
        rollback_file = self.launcher.with_name(
            self.launcher.name + ".rollback-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-" + uuid.uuid4().hex[:8]
        )
        rollback_file.write_bytes(self.launcher_bytes)
        return {"launcher_bytes": self.launcher_bytes, "previous_candidate": self.previous_candidate,
                "previous_root": str(old_root), "launcher_backup": str(rollback_file),
                "launcher_sha256": hashlib.sha256(self.launcher_bytes).hexdigest()}

    def stage_candidate(self, package: Path, candidate: dict):
        target = self.release_root / candidate["source_commit"]
        if target.exists():
            raise ProductionExecutionError("RELEASE_SLOT_ALREADY_EXISTS")
        target.mkdir(parents=True)
        with zipfile.ZipFile(package) as archive:
            archive.extractall(target)
        self.package_root = target
        env = os.environ.copy()
        venv_args = ["py", "-3.14", "-m", "venv"]
        if self.test_mode:
            venv_args.append("--system-site-packages")
        run([*venv_args, str(target / ".venv")], cwd=target, env=env)
        python = target / ".venv" / "Scripts" / "python.exe"
        if self.test_mode:
            # Test bundles are synthetic and may use only host-installed test dependencies.
            run([str(python), "-c", "import uvicorn; assert uvicorn.__version__"],
                cwd=target, env=env)
        else:
            run([str(python), "-m", "pip", "--isolated", "install", "--no-index", "--find-links",
                 str(target / "wheelhouse"), "--require-hashes", "--only-binary=:all:",
                 "-r", "requirements.lock"], cwd=target, env=env)
        run([str(python), "-m", "pip", "check"], cwd=target, env=env)

    def require_schema_compatible(self, candidate: dict, current_head: str):
        if self.package_root is None:
            raise ProductionExecutionError("RELEASE_SLOT_NOT_STAGED")
        import ast
        revisions, parents = set(), set()
        for migration in (self.package_root / "alembic" / "versions").glob("*.py"):
            tree = ast.parse(migration.read_bytes(), filename=str(migration))
            values = {}
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                            values[target.id] = ast.literal_eval(node.value)
            if not isinstance(values.get("revision"), str):
                raise ProductionExecutionError("CANDIDATE_SCHEMA_UNKNOWN")
            revisions.add(values["revision"])
            parent = values.get("down_revision")
            parents.update((parent,) if isinstance(parent, str) else (parent or []))
        heads = revisions - parents
        if len(heads) != 1 or heads != {current_head}:
            raise ProductionExecutionError("SCHEMA_CHANGE_REQUIRES_SEPARATE_APPROVAL")

    def discard_candidate(self):
        if self.package_root is None:
            return
        target = self.package_root.resolve()
        if target.parent != self.release_root or target.is_symlink():
            raise ProductionExecutionError("CANDIDATE_CLEANUP_PATH_INVALID")
        shutil.rmtree(target)
        self.package_root = None

    def _stop_application(self, allow_absent: bool):
        absent = f"$x=@(Get-NetTCPConnection -LocalPort {self.port} -State Listen -ErrorAction SilentlyContinue); if($x.Count -eq 0){{exit 0}}; " if allow_absent else ""
        # Only the new wrapper owns this named event. Legacy Uvicorn has no safe
        # shutdown API; fail closed rather than guessing or terminating it.
        script = absent + f"$x=@(Get-NetTCPConnection -LocalPort {self.port} -State Listen -ErrorAction SilentlyContinue); if($x.Count -ne 1){{exit 21}}; $id=$x[0].OwningProcess; $p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$id); if($p.CommandLine -notmatch 'income_analytics.windows_server'){{exit 22}}; Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class IAEvent {{ [DllImport(\"kernel32.dll\", SetLastError=true, CharSet=CharSet.Unicode)] public static extern IntPtr OpenEvent(uint access, bool inherit, string name); [DllImport(\"kernel32.dll\", SetLastError=true)] public static extern bool SetEvent(IntPtr handle); [DllImport(\"kernel32.dll\")] public static extern bool CloseHandle(IntPtr handle); }}'; $h=[IAEvent]::OpenEvent(0x0002, $false, 'Local\\IncomeAnalytics-Uvicorn-{self.port}'); if($h -eq [IntPtr]::Zero){{exit 24}}; try{{if(-not [IAEvent]::SetEvent($h)){{exit 24}}}}finally{{[IAEvent]::CloseHandle($h)|Out-Null}}; if(-not (Wait-Process -Id $id -Timeout 25 -ErrorAction SilentlyContinue)){{}}; $p=Get-Process -Id $id -ErrorAction SilentlyContinue; if($p){{exit 23}}; if(@(Get-NetTCPConnection -LocalPort {self.port} -State Listen -ErrorAction SilentlyContinue).Count -ne 0){{exit 25}}"
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, timeout=35, check=False,
        )
        if completed.returncode:
            if completed.returncode == 22:
                raise ProductionExecutionError("LEGACY_GRACEFUL_STOP_UNAVAILABLE")
            raise ProductionExecutionError(
                "GRACEFUL_STOP_FAILED", {"powershell_exit_code": completed.returncode}
            )
        self.stopped = True

    def stop_application(self):
        self._stop_application(allow_absent=False)

    def stop_candidate_application(self):
        self._stop_application(allow_absent=True)

    def activate_candidate(self, candidate: dict):
        if self.package_root is None or self.launcher_bytes is None:
            raise ProductionExecutionError("RELEASE_OR_LAUNCHER_SNAPSHOT_MISSING")
        content = self.launcher_bytes.decode("utf-8-sig")
        target = str(self.package_root).replace("'", "''")
        content, count = re.subn(
            r"(?m)^(\s*Set-Location\s+-LiteralPath\s+)'[^']+'\s*$",
            lambda match: match.group(1) + "'" + target + "'", content,
        )
        if count != 1:
            raise ProductionExecutionError("LAUNCHER_LOCATION_UPDATE_FAILED")
        python = str(self.package_root / ".venv" / "Scripts" / "python.exe").replace("'", "''")
        content, count = re.subn(
            r"(?m)^\s*py\s+-3\.14\s+-X\s+utf8\s+-m\s+(?:uvicorn|income_analytics\.windows_server)\b",
            lambda _: "& '" + python + "' -X utf8 -m income_analytics.windows_server", content,
        )
        if count != 1:
            raise ProductionExecutionError("LAUNCHER_RUNTIME_UPDATE_FAILED")
        src = str(self.package_root / "src").replace("'", "''")
        line = "$env:INCOME_ANALYTICS_RELEASE_COMMIT = '" + candidate["source_commit"] + "'\r\n"
        line += "$env:PYTHONPATH = '" + src + "'\r\n"
        content, count = re.subn(r"(?m)^(\s*&?\s*'.*python\.exe'.*income_analytics\.windows_server.*)$",
                                  lambda match: line + match.group(1), content, count=1)
        if count != 1:
            raise ProductionExecutionError("LAUNCHER_ENVIRONMENT_UPDATE_FAILED")
        temporary = self.launcher.with_suffix(self.launcher.suffix + ".pending")
        temporary.write_bytes(content.encode("utf-8"))
        os.replace(temporary, self.launcher)
        self.activated = True

    def start_application(self):
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-File", str(self.launcher)],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def health_check(self, candidate: dict) -> dict:
        last_error = None
        attempts = 30 if self.test_mode else 24
        interval = 0.25 if self.test_mode else 5
        for _ in range(attempts):
            try:
                request = urllib.request.Request(self.health_url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(request, timeout=1 if self.test_mode else 5) as response:
                    data = json.loads(response.read())
                if data.get("status") == "ok":
                    return data
            except Exception as error:  # transport details are not written to evidence
                last_error = type(error).__name__
            time.sleep(interval)
        raise ProductionExecutionError("HTTPS_HEALTH_FAILED_" + str(last_error or "TIMEOUT"))

    def restore_previous_release(self, snapshot: dict):
        if self.activated:
            if hashlib.sha256(snapshot["launcher_bytes"]).hexdigest() != snapshot["launcher_sha256"]:
                raise ProductionExecutionError("LAUNCHER_ROLLBACK_BACKUP_MISMATCH")
            temporary = self.launcher.with_suffix(self.launcher.suffix + ".rollback")
            temporary.write_bytes(snapshot["launcher_bytes"])
            os.replace(temporary, self.launcher)
        self.activated = False


def run(args, cwd, env):
    completed = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=1800)
    if completed.returncode:
        raise ProductionExecutionError("OFFLINE_INSTALL_OR_PROCESS_FAILED")
    return completed


def execute(adapter, *, candidate: dict, staging: dict, scope: dict, authorization: dict,
            package: Path, confirmation: str) -> dict:
    """Execute a deployment while retaining an independently testable rollback path.

    `adapter` owns host operations. The SQLite database is backed up and verified
    before stopping the app; rollback restores code/config only and never restores DB.
    """
    decision = evaluate(candidate, staging, scope, authorization)
    if decision["decision"] != "ELIGIBLE":
        raise ProductionExecutionError("PRODUCTION_EVIDENCE_BLOCKED")
    try:
        require_publish_confirmation(
            candidate["source_commit"], candidate["package_sha256"], confirmation
        )
        production_request("production", decision, confirmation)
    except Exception as error:
        raise ProductionExecutionError("EXPLICIT_ARTIFACT_CONFIRMATION_MISMATCH") from error
    actual = hashlib.sha256(package.read_bytes()).hexdigest()
    if actual != candidate["package_sha256"]:
        raise ProductionExecutionError("PACKAGE_DIGEST_MISMATCH")
    adapter.verify_package(package, candidate)
    backup = adapter.create_and_verify_online_backup()
    if backup.get("status") != "PASS" or not backup.get("schema_head"):
        raise ProductionExecutionError("ONLINE_BACKUP_NOT_VERIFIED")
    snapshot = adapter.preserve_previous_release()
    try:
        adapter.stage_candidate(package, candidate)
        adapter.require_schema_compatible(candidate, backup["schema_head"])
        adapter.stop_application()
    except Exception:
        adapter.discard_candidate()
        raise
    activated = False
    try:
        adapter.activate_candidate(candidate)
        activated = True
        adapter.start_application()
        observed = adapter.health_check(candidate)
        if observed.get("status") != "ok" or observed.get("release_commit") != candidate["source_commit"]:
            raise ProductionExecutionError("PUBLISHED_VERSION_HEALTH_MISMATCH")
        return {
            "status": "PUBLISHED",
            "deployment_authorized": True,
            "source_commit": candidate["source_commit"],
            "package_sha256": candidate["package_sha256"],
            "artifact_id": candidate["artifact_id"],
            "policy_sha256": decision["policy_sha256"],
            "staging_run_id": decision["staging_run_id"],
            "production_approval_comment_id": authorization["approval"]["comment_id"],
            "backup": backup,
            "health": observed,
            "rollback": "NOT_REQUIRED",
            "database_restored": False,
        }
    except Exception as error:
        try:
            if activated:
                adapter.stop_candidate_application()
            if activated:
                adapter.restore_previous_release(snapshot)
            adapter.start_application()
            restored = adapter.health_check(snapshot["previous_candidate"])
            previous = snapshot["previous_candidate"]
            if restored.get("release_commit") != previous.get("source_commit") and not (
                previous.get("legacy_health_without_commit") and restored.get("status") == "ok"
            ):
                raise ProductionExecutionError("ROLLBACK_HEALTH_MISMATCH")
        except Exception as rollback_error:
            raise ProductionExecutionError(
                "DEPLOYMENT_AND_ROLLBACK_FAILED",
                {"backup": backup, "rollback": "FAIL", "database_restored": False},
            ) from rollback_error
        raise ProductionExecutionError(
            "DEPLOYMENT_FAILED_ROLLED_BACK",
            {"backup": backup, "rollback": "PASS", "database_restored": False},
        ) from error


def github_comment(comment_id: int) -> dict:
    if not isinstance(comment_id, int) or comment_id < 1:
        raise ProductionExecutionError("APPROVAL_COMMENT_ID_INVALID")
    response = subprocess.run(
        ["gh", "api", f"repos/tiagocaldironi/income-analytics/issues/comments/{comment_id}"],
        capture_output=True, text=True, check=False, timeout=30,
    )
    if response.returncode:
        raise ProductionExecutionError("APPROVAL_COMMENT_FETCH_FAILED")
    try:
        return json.loads(response.stdout)
    except json.JSONDecodeError as error:
        raise ProductionExecutionError("APPROVAL_COMMENT_RESPONSE_INVALID") from error


class GitHubEvidence:
    """Fetch and compare exact run/artifact evidence using the operator's `gh` login."""

    repository = "tiagocaldironi/income-analytics"

    def json(self, endpoint: str) -> dict:
        response = subprocess.run(
            ["gh", "api", "repos/" + self.repository + "/" + endpoint],
            capture_output=True, text=True, check=False, timeout=60,
        )
        if response.returncode:
            raise ProductionExecutionError("GITHUB_PROVENANCE_FETCH_FAILED")
        try:
            return json.loads(response.stdout)
        except json.JSONDecodeError as error:
            raise ProductionExecutionError("GITHUB_PROVENANCE_RESPONSE_INVALID") from error

    def artifact(self, run_id: int, name: str) -> dict:
        result = self.json(f"actions/runs/{run_id}/artifacts?per_page=100")
        matches = [item for item in result.get("artifacts", []) if item.get("name") == name]
        if len(matches) != 1:
            raise ProductionExecutionError("GITHUB_EVIDENCE_ARTIFACT_NOT_UNIQUE")
        artifact = matches[0]
        if artifact.get("expired") is not False or artifact.get("workflow_run", {}).get("id") != run_id:
            raise ProductionExecutionError("GITHUB_EVIDENCE_ARTIFACT_INVALID")
        return artifact

    def files(self, artifact: dict) -> dict[str, bytes]:
        with tempfile.TemporaryDirectory(prefix="income-github-evidence-") as directory:
            archive_path = Path(directory) / "artifact.zip"
            with archive_path.open("wb") as output:
                response = subprocess.run(
                    ["gh", "api", f"repos/{self.repository}/actions/artifacts/{artifact['id']}/zip"],
                    stdout=output, stderr=subprocess.PIPE, check=False, timeout=180,
                )
            if response.returncode:
                raise ProductionExecutionError("GITHUB_EVIDENCE_DOWNLOAD_FAILED")
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)) or sum(item.file_size for item in archive.infolist()) > 512 * 1024 * 1024:
                    raise ProductionExecutionError("GITHUB_EVIDENCE_ARCHIVE_INVALID")
                files = {}
                for name in names:
                    flat_name = Path(name).name
                    if flat_name in files:
                        raise ProductionExecutionError("GITHUB_EVIDENCE_DUPLICATE_BASENAME")
                    files[flat_name] = archive.read(name)
                return files

    def verify_run(self, run_id: int, commit: str, path: str, events: set[str]) -> dict:
        run = self.json(f"actions/runs/{run_id}")
        if (
            run.get("repository", {}).get("full_name") != self.repository
            or run.get("head_repository", {}).get("full_name") != self.repository
            or run.get("path") != path
            or run.get("head_sha") != commit
            or run.get("event") not in events
            or run.get("status") != "completed"
        ):
            raise ProductionExecutionError("GITHUB_EVIDENCE_RUN_IDENTITY_MISMATCH")
        return run

    def verify_candidate(self, candidate: dict, package: Path, staging: dict, scope: dict):
        commit = candidate["source_commit"]
        build_run_id = int(candidate["build_run_id"])
        build_attempt = int(candidate["build_run_attempt"])
        build = self.verify_run(build_run_id, commit, ".github/workflows/ci-offline.yml", {"push"})
        if build.get("head_branch") != "develop" or build.get("run_attempt") != build_attempt:
            raise ProductionExecutionError("SOURCE_RUN_NOT_PRODUCTION_BRANCH")
        metadata = self.json(f"actions/artifacts/{int(candidate['artifact_id'])}")
        if (
            metadata.get("name") != f"application-{commit}-windows-x64"
            or metadata.get("digest") != candidate.get("artifact_digest")
            or metadata.get("workflow_run", {}).get("id") != build_run_id
            or metadata.get("created_at", "") < build.get("run_started_at", "")
            or metadata.get("expired") is not False
        ):
            raise ProductionExecutionError("SOURCE_ARTIFACT_METADATA_MISMATCH")
        jobs = self.json(f"actions/runs/{build_run_id}/attempts/{build_attempt}/jobs?per_page=100").get("jobs", [])
        conclusions = {job.get("name"): job.get("conclusion") for job in jobs}
        for required in ("CI / Engineering", "CI / Reproducible build", "CI / Security baseline"):
            if conclusions.get(required) != "success":
                raise ProductionExecutionError("SOURCE_REQUIRED_JOB_NOT_SUCCESS")
        source_files = self.files(metadata)
        package_name = f"income-analytics-{commit}-windows-x64.zip"
        if hashlib.sha256(package.read_bytes()).hexdigest() != candidate["package_sha256"]:
            raise ProductionExecutionError("LOCAL_PACKAGE_HASH_MISMATCH")
        if source_files.get(package_name) != package.read_bytes():
            raise ProductionExecutionError("LOCAL_PACKAGE_NOT_FROM_SOURCE_ARTIFACT")
        sidecar_name = package_name.removesuffix(".zip") + ".sha256"
        if sidecar_name not in source_files or source_files[sidecar_name].decode().split()[0] != candidate["package_sha256"]:
            raise ProductionExecutionError("SOURCE_PACKAGE_SIDECAR_MISMATCH")
        with zipfile.ZipFile(package) as bundle:
            if source_files.get("manifest.json") != bundle.read("manifest.json"):
                raise ProductionExecutionError("SOURCE_MANIFEST_MISMATCH")

        stage_run_id = int(staging.get("workflow_identity", {}).get("delivery_run_id", 0))
        stage = self.verify_run(stage_run_id, commit, ".github/workflows/delivery-validation.yml", {"push"})
        stage_attempt = int(stage.get("run_attempt", 0))
        if stage.get("head_branch") != "develop" or stage_attempt < 1 or stage.get("conclusion") != "success":
            raise ProductionExecutionError("STAGING_RUN_NOT_PRODUCTION_BRANCH")
        stage_artifact = self.artifact(stage_run_id, f"staging-validated-{stage_run_id}-{stage_attempt}")
        if stage_artifact.get("created_at", "") < stage.get("run_started_at", ""):
            raise ProductionExecutionError("STAGING_ARTIFACT_FROM_OLD_ATTEMPT")
        stage_files = self.files(stage_artifact)
        try:
            if (
                json.loads(stage_files["validation.json"]) != staging
                or json.loads(stage_files["candidate.json"]) != candidate
            ):
                raise ProductionExecutionError("STAGING_REPORT_NOT_FROM_GITHUB_ARTIFACT")
        except (KeyError, json.JSONDecodeError) as error:
            raise ProductionExecutionError("STAGING_REPORT_NOT_FROM_GITHUB_ARTIFACT") from error

        scope_run_id = int(scope.get("run_id", 0))
        scope_run = self.verify_run(scope_run_id, commit, ".github/workflows/ci-offline.yml", {"pull_request"})
        if scope_run.get("workflow_id") != 399392307:
            raise ProductionExecutionError("SCOPE_WORKFLOW_ID_MISMATCH")
        scope_artifact = self.artifact(scope_run_id, f"scoped-promotion-{commit}")
        if scope_artifact.get("created_at", "") < scope_run.get("run_started_at", ""):
            raise ProductionExecutionError("SCOPE_ARTIFACT_FROM_OLD_ATTEMPT")
        scope_files = self.files(scope_artifact)
        try:
            if json.loads(scope_files["promotion-report.json"]) != scope:
                raise ProductionExecutionError("SCOPE_REPORT_NOT_FROM_GITHUB_ARTIFACT")
        except (KeyError, json.JSONDecodeError) as error:
            raise ProductionExecutionError("SCOPE_REPORT_NOT_FROM_GITHUB_ARTIFACT") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--scope-report", type=Path, required=True)
    parser.add_argument("--production-approval", type=Path, required=True)
    parser.add_argument("--policy-approval", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=Path(__file__).with_name("release-applicability-policy.json"))
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--launcher", type=Path, required=True)
    parser.add_argument("--health-url", required=True)
    parser.add_argument("--evidence-out", type=Path, required=True)
    parser.add_argument("--confirm", action="store_true", help="prompt for exact artifact confirmation")
    args = parser.parse_args()
    try:
        from production_authorization import valid_production_comment
        from release_applicability import valid_policy_approval

        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        staging = json.loads(args.staging.read_text(encoding="utf-8"))
        scope = json.loads(args.scope_report.read_text(encoding="utf-8"))
        authorization = json.loads(args.production_approval.read_text(encoding="utf-8"))
        record = json.loads(args.policy_approval.read_text(encoding="utf-8"))
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        policy_approval = record.get("approval", {})
        if not valid_policy_approval(
            args.policy, record, github_comment(int(policy_approval.get("comment_id", 0)))
        ):
            raise ProductionExecutionError("EXACT_POLICY_HASH_APPROVAL_INVALID")
        approval = authorization.get("approval", {})
        if not valid_production_comment(
            approval, github_comment(int(approval.get("comment_id", 0))),
            policy["approval_authority"],
        ):
            raise ProductionExecutionError("EXACT_ARTIFACT_APPROVAL_INVALID")
        GitHubEvidence().verify_candidate(candidate, args.package, staging, scope)
        if scope.get("control_applicability", {}).get("policy_sha256") != policy_approval.get("policy_sha256"):
            raise ProductionExecutionError("SCOPE_POLICY_HASH_MISMATCH")
        if not args.confirm:
            raise ProductionExecutionError("EXPLICIT_CONFIRMATION_REQUIRED")
        phrase = input("Digite a confirmação exata para publicar: ")
        host = WindowsHost(
            release_root=args.release_root, database=args.database,
            launcher=args.launcher, health_url=args.health_url,
        )
        report = execute(
            host, candidate=candidate, staging=staging, scope=scope,
            authorization=authorization, package=args.package, confirmation=phrase,
        )
        report["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: report[key] for key in
                          ("status", "source_commit", "package_sha256", "health")}))
        return 0
    except Exception as error:
        failure = str(error) if isinstance(error, ProductionExecutionError) else type(error).__name__
        report = {"status": "BLOCKED", "failure_category": failure, "deployment_authorized": False}
        if isinstance(error, ProductionExecutionError):
            report.update(error.evidence)
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
