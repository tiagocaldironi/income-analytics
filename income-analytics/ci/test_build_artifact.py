"""Build contract: negative cases mutate only temporary synthetic application copies."""

import json
import subprocess
import zipfile
from pathlib import Path

import artifact
import pytest
import smoke_artifact
from build_pipeline import compare_builds
from gate_policy import summarize_reports
from test_governance import engineering_reports


def test_runtime_policy_requires_only_real_versioned_files_and_all_migrations():
    root = Path(__file__).resolve().parents[1]
    policy = json.loads((root / "ci/build_policy.json").read_text())
    reverse = {target: source for source, target in artifact.SUPPORT.items()}
    for name in artifact.REQUIRED | set(policy["required_files"]):
        assert (root / reverse.get(name, name)).is_file()
    migrations = {p.relative_to(root).as_posix() for p in (root / "alembic/versions").glob("*.py")}
    assert migrations.issubset(policy["required_files"])


@pytest.fixture
def built(tmp_path):
    root = tmp_path / "repo"
    app = root / "income-analytics"
    app.mkdir(parents=True)
    here = Path(__file__).parent
    for source in artifact.SUPPORT:
        path = app / source
        path.parent.mkdir(parents=True, exist_ok=True)
        original = here.parent / source
        path.write_bytes(original.read_bytes())
    for name in artifact.REQUIRED:
        if name not in artifact.SUPPORT.values():
            path = app / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# synthetic application input\n")
    migration = app / "alembic/versions/0001_synthetic.py"
    migration.parent.mkdir(parents=True, exist_ok=True)
    migration.write_text("# synthetic migration\n")
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    wheel = wheels / "alembic-1.19.2-py3-none-any.whl"
    wheel.write_bytes(b"synthetic wheel bytes; never installed")
    (app / "ci/runtime-windows-py314.lock").write_text(
        "alembic==1.19.2 --hash=sha256:" + artifact.sha(wheel.read_bytes()) + "\n"
    )
    policy_file = app / "ci/build_policy.json"
    policy = json.loads(policy_file.read_text())
    policy["required_files"] = sorted(artifact.REQUIRED | {"alembic/versions/0001_synthetic.py"})
    policy_file.write_bytes(artifact.canonical(policy))
    for args in (
        ["init"], ["config", "core.autocrlf", "false"], ["add", "."],
        ["-c", "user.name=Build Test", "-c", "user.email=build@example.invalid",
         "commit", "-m", "synthetic build test"],
    ):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    commit = artifact.git(root, "rev-parse", "HEAD").decode().strip()
    archive = tmp_path / "first.zip"
    artifact.build(root, wheels, archive, commit)
    return root, wheels, archive, commit


def rewrite(archive, changes, remove=()):
    with zipfile.ZipFile(archive) as bundle:
        files = {name: bundle.read(name) for name in bundle.namelist() if name not in remove}
    files.update(changes)
    with zipfile.ZipFile(archive, "w") as bundle:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            bundle.writestr(entry, data)


def test_two_builds_ignore_filesystem_times_and_use_git_bytes(built, tmp_path):
    root, wheels, first, commit = built
    second = tmp_path / "second.zip"
    artifact.build(root, wheels, second, commit)
    compare_builds(first, second)
    assert artifact.verify(first, commit)["sha256"] == artifact.sha(second.read_bytes())
    with zipfile.ZipFile(first) as bundle:
        assert bundle.namelist() == sorted(bundle.namelist())
        assert all(i.compress_type == zipfile.ZIP_STORED for i in bundle.infolist())


@pytest.mark.parametrize("change,remove", [
    ({"src/income_analytics/main.py": b"altered"}, ()),
    ({}, ("src/income_analytics/main.py",)),
    ({}, ("alembic/versions/0001_synthetic.py",)),
    ({}, ("wheelhouse/alembic-1.19.2-py3-none-any.whl",)),
    ({"unexpected.txt": b"extra"}, ()),
    ({"manifest.json": b"{}"}, ()),
    ({"/absolute.txt": b"extra"}, ()),
    ({"../escape": b"extra"}, ()),
    ({"C:/personal/file": b"extra"}, ()),
    ({"debug.tmp": b"temporary"}, ()),
])
def test_tampered_incomplete_or_invalid_structure_rejected(built, change, remove):
    _, _, archive, commit = built
    rewrite(archive, change, remove)
    with pytest.raises((ValueError, KeyError)):
        artifact.verify(archive, commit)


def test_incorrect_commit_and_external_digest_rejected(built):
    _, _, archive, commit = built
    with pytest.raises(ValueError, match="PROVENANCE"):
        artifact.verify(archive, "a" * 40)
    with pytest.raises(ValueError, match="DIGEST"):
        artifact.verify(archive, commit, "0" * 64)


def test_divergent_build_cannot_be_reported_reproducible(built, tmp_path):
    other = tmp_path / "other.zip"
    other.write_bytes(b"different build")
    with pytest.raises(ValueError, match="DIVERGENCE"):
        compare_builds(built[2], other)


def test_accidental_secret_is_rejected_before_packaging(built):
    root, wheels, archive, _ = built
    target = root / "income-analytics/src/income_analytics/accidental.py"
    target.write_text('secret = "-----BEGIN PRIVATE KEY-----"\n')
    artifact.git(root, "add", ".")
    artifact.git(root, "-c", "user.name=Test", "-c", "user.email=t@example.invalid",
                 "commit", "-m", "synthetic secret")
    with pytest.raises(ValueError, match="SECRET"):
        artifact.build(root, wheels, archive, "test")


def test_unlocked_dependency_is_rejected():
    with pytest.raises(ValueError, match="UNLOCKED"):
        artifact.lock_entries(b"alembic>=1\n")


def test_dirty_checkout_is_rejected(built):
    root, wheels, archive, _ = built
    (root / "untracked.txt").write_text("unexpected local content")
    with pytest.raises(ValueError, match="CLEAN_CHECKOUT"):
        artifact.build(root, wheels, archive, "test")


@pytest.mark.parametrize("status", ["missing", "failed"])
def test_build_failure_or_absence_blocks_stable_engineering_gate(status):
    reports = engineering_reports()
    if status == "missing":
        del reports["build"]
    else:
        reports["build"]["exit_code"] = 1
    assert summarize_reports(reports)["engineering_ci"] == "FAIL"


@pytest.mark.parametrize("field", [
    "reproducibility", "manifest", "independent_builds", "artifact_sha256", "installation",
])
def test_zero_exit_without_complete_build_evidence_cannot_approve(field):
    reports = engineering_reports()
    del reports["build"][field]
    assert summarize_reports(reports)["engineering_ci"] == "FAIL"


def test_migration_failure_is_not_reported_as_clean_install(built, monkeypatch):
    labels = []

    def fail_migration(args, cwd, env, label):
        labels.append(label)
        assert env["INCOME_AUTH_MODE"] == "local"
        assert env["INCOME_ENV"] == "development"
        assert "BRAPI_TOKEN" not in env
        assert Path(env["INCOME_ANALYTICS_DATABASE"]).is_relative_to(cwd.parent)
        if label == "MIGRATIONS":
            raise RuntimeError("SMOKE_FAILED_MIGRATIONS")

    monkeypatch.setenv("BRAPI_TOKEN", "synthetic-inherited-secret")
    monkeypatch.setattr(smoke_artifact, "command", fail_migration)
    with pytest.raises(RuntimeError, match="MIGRATIONS"):
        smoke_artifact.smoke(built[2], built[3], artifact.sha(built[2].read_bytes()))
    assert labels == ["VENV", "INSTALL", "DEPENDENCIES", "MIGRATIONS"]


def test_initialization_failure_is_not_reported_as_success(built, monkeypatch):
    class FailedServer:
        def __init__(self, *args, **kwargs):
            self.terminated = False

        def poll(self):
            return 1

        def terminate(self):
            self.terminated = True

        def wait(self, timeout):
            assert self.terminated

    monkeypatch.setattr(smoke_artifact, "command", lambda *args: None)
    monkeypatch.setattr(smoke_artifact.subprocess, "Popen", FailedServer)
    with pytest.raises(RuntimeError, match="STARTUP"):
        smoke_artifact.smoke(built[2], built[3], artifact.sha(built[2].read_bytes()))
