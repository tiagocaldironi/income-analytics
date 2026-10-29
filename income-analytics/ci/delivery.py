"""Delivery decisions and SQLite recovery. No production target is implemented."""

import ast
import hashlib
import json
import os
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path

from artifact import canonical, sha, verify

REPOSITORY = "tiagocaldironi/income-analytics"
WORKFLOW_ID = 399392307
WORKFLOW_PATH = ".github/workflows/ci-offline.yml"
BASELINE_RUN = 40856571402
BASELINE_COMMIT = "cc71b0be65d6fe34b97cd3305dfc7956c9a4a065"


class DeliveryError(ValueError):
    """Stable, payload-free error code suitable for audit reports."""


def require(condition, code):
    if not condition:
        raise DeliveryError(code)


class Workspace:
    """Capability: filesystem writes and SQLite access only below a fresh owned root."""

    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="income-delivery-")
        self.root = Path(self.temporary.name).resolve()
        self.processes = []
        self.ports = []

    def safe(self, path):
        value = Path(path)
        require(value.absolute().is_relative_to(self.root), "PATH_NOT_OWNED")
        resolved = value.resolve()
        require(resolved.is_relative_to(self.root) and resolved != self.root, "PATH_NOT_OWNED")
        for parent in (value, *value.parents):
            require(not parent.is_symlink() and not parent.is_junction(), "LINK_NOT_ALLOWED")
            if parent == self.root:
                break
        return resolved

    def file(self, name):
        return self.safe(self.root / name)

    def cleanup(self):
        import socket

        failed = False
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except Exception:
                    process.kill()
                    process.wait(timeout=10)
            failed |= process.poll() is None
        for port in self.ports:
            with socket.socket() as probe:
                probe.settimeout(1)
                if os.getenv("INCOME_CI_OFFLINE") == "1":
                    try:
                        probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                        probe.bind(("127.0.0.1", port))
                    except OSError:
                        failed = True
                else:
                    failed |= probe.connect_ex(("127.0.0.1", port)) == 0
        require(not failed, "PROCESS_OR_PORT_LEAK")
        try:
            self.temporary.cleanup()
        except OSError:
            raise DeliveryError("CLEANUP_FAILED") from None
        require(not self.root.exists(), "CLEANUP_FAILED")


def trusted_source(run, artifact, jobs, build, gate, expected, mode, current_run=None):
    """Authenticate metadata before executing or extracting any package content."""
    require(run.get("repository", {}).get("full_name") == REPOSITORY, "WRONG_REPOSITORY")
    require(run.get("head_repository", {}).get("full_name") == REPOSITORY, "FORK_NOT_TRUSTED")
    require(
        run.get("workflow_id") == WORKFLOW_ID and run.get("path") == WORKFLOW_PATH,
        "UNTRUSTED_WORKFLOW",
    )
    if mode == "delivery":
        require(
            run.get("event") == "push" and run.get("head_branch") == "develop",
            "UNMERGED_PR_NOT_PROMOTABLE",
        )
        require(run.get("status") == "completed", "SOURCE_NOT_COMPLETE")
        require(run.get("head_sha") == expected, "SOURCE_COMMIT_MISMATCH")
        require(build.get("pr_head_sha") == "", "PR_PROVENANCE_NOT_PROMOTABLE")
    else:
        require(
            mode == "premerge"
            and run.get("event") == "pull_request"
            and run.get("id") == current_run,
            "INVALID_PREMERGE_CONTEXT",
        )
        require(build.get("pr_head_sha") == run.get("head_sha"), "PR_HEAD_MISMATCH")
    require(
        build.get("checkout_sha") == expected == build.get("event_sha"), "SOURCE_COMMIT_MISMATCH"
    )
    require(
        build.get("worktree_dirty") is False and build.get("schema") == 3, "DIRTY_OR_UNKNOWN_BUILD"
    )
    require(
        build.get("status") == "PASS"
        and build.get("exit_code") == 0
        and build.get("independent_builds") == 2
        and build.get("reproducibility") == build.get("manifest") == "PASS",
        "BUILD_GATE_FAILED",
    )
    require(
        gate.get("engineering_ci") == "PASS"
        and gate.get("reproducible_build") == "PASS"
        and gate.get("consistent_identity") is True,
        "ENGINEERING_FAILED",
    )
    require(
        gate.get("financial_certification") == "BLOCKED"
        and gate.get("release_readiness") == "BLOCKED"
        and gate.get("deployment_authorized") is False,
        "FALSE_RELEASE_AUTHORIZATION",
    )
    states = {j["name"]: j.get("conclusion") for j in jobs}
    require(
        states.get("CI / Engineering") == states.get("CI / Reproducible build") == "success",
        "REQUIRED_JOB_FAILED",
    )
    require(artifact is not None and artifact.get("expired") is False, "ARTIFACT_UNAVAILABLE")
    require(artifact.get("workflow_run", {}).get("id") == run["id"], "WRONG_ARTIFACT_RUN")
    require(artifact.get("name") == f"application-{expected}-windows-x64", "WRONG_ARTIFACT")
    require(
        artifact.get("created_at", "") >= run.get("run_started_at", ""), "ARTIFACT_FROM_OLD_ATTEMPT"
    )
    return {
        "repository": REPOSITORY,
        "source_commit": expected,
        "build_run_id": run["id"],
        "build_run_attempt": run["run_attempt"],
        "artifact_id": artifact["id"],
        "artifact_digest": artifact["digest"],
        "package_sha256": build["artifact_sha256"],
        "build_policy_identity": build["build_policy_sha256"],
        "governance_policy_identity": build["governance_policy_sha256"],
        "source_fingerprint": build["source_fingerprint"],
        "environment_target": "DISPOSABLE_WINDOWS_STAGING",
        "mode": mode,
        "promotion_status": "CANDIDATE_CREATED" if mode == "delivery" else "PROMOTION_BLOCKED",
        "promotion_blockers": [] if mode == "delivery" else ["PR_UNMERGED_PREMERGE_TEST_ONLY"],
        "financial_release": "BLOCKED",
        "production_status": "PRODUCTION_NOT_AUTHORIZED",
        "validation_evidence_references": [],
    }


def production_request(target, authorization=None):
    # This implementation deliberately has no productive execution path, even
    # when a caller supplies a purported approval token.
    require(target == "staging" and authorization is None, "PRODUCTION_NOT_AUTHORIZED")


def schema_contract(archive):
    with zipfile.ZipFile(archive) as package:
        manifest = json.loads(package.read("manifest.json"))
        names = sorted(p for p in manifest["files"] if p.startswith("alembic/versions/"))
        revisions, parents = set(), set()
        for name in names:
            tree = ast.parse(package.read(name))
            values = {}
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id in {
                            "revision",
                            "down_revision",
                        }:
                            values[target.id] = ast.literal_eval(node.value)
            require(isinstance(values.get("revision"), str), "UNKNOWN_MIGRATION_CONTRACT")
            revisions.add(values["revision"])
            parent = values.get("down_revision")
            if parent:
                parents.update((parent,) if isinstance(parent, str) else parent)
        heads = revisions - parents
        require(len(heads) == 1 and parents.issubset(revisions), "INVALID_MIGRATION_GRAPH")
        return {
            "head": heads.pop(),
            "migrations_sha256": sha(canonical({p: manifest["files"][p]["sha256"] for p in names})),
        }


def state_signature(connection):
    tables = connection.execute(
        "SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    state = []
    for name, sql in tables:
        quoted = '"' + name.replace('"', '""') + '"'
        rows = connection.execute("SELECT * FROM " + quoted).fetchall()
        converted = [
            [{"blob": v.hex()} if isinstance(v, bytes) else v for v in row] for row in rows
        ]
        state.append(
            [name, sql, sorted(converted, key=lambda row: json.dumps(row, sort_keys=True))]
        )
    return sha(canonical(state))


def database_check(workspace, path, expected_head, signature=None):
    path = workspace.safe(path)
    require(path.is_file(), "DATABASE_MISSING")
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
            require(
                db.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
                "SQLITE_INTEGRITY_FAILED",
            )
            heads = db.execute("SELECT version_num FROM alembic_version").fetchall()
            require(heads == [(expected_head,)], "SCHEMA_INCOMPATIBLE")
            actual = state_signature(db)
            require(signature is None or signature == actual, "RESTORE_STATE_MISMATCH")
            return actual
    except sqlite3.Error:
        raise DeliveryError("SQLITE_INVALID_OR_UNREADABLE") from None


def backup_database(workspace, source, destination, head):
    source, destination = workspace.safe(source), workspace.safe(destination)
    signature = database_check(workspace, source, head)
    require(not destination.exists(), "BACKUP_ALREADY_EXISTS")
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as origin:
        with closing(sqlite3.connect(destination)) as backup:
            origin.backup(backup)
    database_check(workspace, destination, head, signature)
    return {
        "status": "PASS",
        "method": "SQLITE_ONLINE_BACKUP_API",
        "sha256": sha(destination.read_bytes()),
        "state_signature": signature,
        "schema_head": head,
    }


def restore_database(workspace, backup_path, destination, record):
    backup_path, destination = workspace.safe(backup_path), workspace.safe(destination)
    require(backup_path.is_file(), "BACKUP_MISSING")
    require(sha(backup_path.read_bytes()) == record["sha256"], "BACKUP_DIGEST_MISMATCH")
    database_check(workspace, backup_path, record["schema_head"], record["state_signature"])
    require(all(p.poll() is not None for p in workspace.processes), "RESTORE_REQUIRES_STOPPED_APP")
    with closing(sqlite3.connect(backup_path.as_uri() + "?mode=ro", uri=True)) as source:
        with closing(sqlite3.connect(destination)) as target:
            source.backup(target)
    database_check(workspace, destination, record["schema_head"], record["state_signature"])
    return {"status": "PASS", "integrity_check": "PASS", "schema": "PASS", "semantic_state": "PASS"}


def rollback_compatibility(workspace, database, previous_contract, candidate_contract):
    require(
        previous_contract == candidate_contract, "ROLLBACK_BLOCKED_SCHEMA_RESTORE_PLAN_REQUIRED"
    )
    database_check(workspace, database, previous_contract["head"])
    return "PASS_EXACT_MIGRATION_IDENTITY"


def immutable_copy(workspace, archive, destination, candidate):
    destination = workspace.safe(destination)
    require(not destination.exists(), "LOGICAL_ARTIFACT_ALREADY_EXISTS")
    verify(archive, candidate["source_commit"], candidate["package_sha256"])
    destination.write_bytes(archive.read_bytes())
    require(sha(destination.read_bytes()) == candidate["package_sha256"], "PROMOTION_BYTES_CHANGED")
    with zipfile.ZipFile(destination) as package:
        candidate["manifest_sha256"] = hashlib.sha256(package.read("manifest.json")).hexdigest()
    return destination


def select_version(workspace, name, candidate):
    require(name in {"A", "B"}, "INVALID_VERSION_SLOT")
    pointer = workspace.file("current.json")
    staging = workspace.file("current.pending.json")
    staging.write_bytes(
        canonical(
            {
                "slot": name,
                "commit": candidate["source_commit"],
                "package_sha256": candidate["package_sha256"],
            }
        )
    )
    os.replace(staging, pointer)


def verify_selection(workspace, slot, archive, candidate):
    pointer = json.loads(workspace.file("current.json").read_text())
    require(
        pointer
        == {
            "slot": slot,
            "commit": candidate["source_commit"],
            "package_sha256": candidate["package_sha256"],
        },
        "PARTIAL_ROLLBACK",
    )
    require(
        sha(workspace.safe(archive).read_bytes()) == candidate["package_sha256"], "PARTIAL_ROLLBACK"
    )


def security_delivery_gate(gate, jobs, run_id, commit, rollback=False):
    """Legacy A is a pinned rollback fixture, never a new approved candidate."""
    if rollback and run_id == BASELINE_RUN and commit == BASELINE_COMMIT:
        return "LEGACY_PINNED_ROLLBACK_ONLY"
    states = {job["name"]: job.get("conclusion") for job in jobs}
    require(gate.get("security_baseline") == "PASS", "SECURITY_GATE_NOT_APPROVED")
    require(states.get("CI / Security baseline") == "success", "SECURITY_JOB_NOT_APPROVED")
    return "PASS"
