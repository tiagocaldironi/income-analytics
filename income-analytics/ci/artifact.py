"""Deterministic Windows application bundle and stdlib-only integrity verifier.

Also shipped as artifact.py, so validation requires neither Git nor installed packages.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

REPOSITORY = "tiagocaldironi/income-analytics"
PYTHON = "3.14.7"
FORMAT = 1
PREFIXES = ("src/", "alembic/")
SUPPORT = {
    "ci/runtime-windows-py314.lock": "requirements.lock",
    "ci/artifact.py": "artifact.py",
    "ci/smoke_artifact.py": "smoke_artifact.py",
    "ci/build_installation.md": "INSTALL.md",
    "ci/build_policy.json": "build-policy.json",
    "alembic.ini": "alembic.ini",
    "pyproject.toml": "pyproject.toml",
}
REQUIRED = {
    *SUPPORT.values(),
    "src/income_analytics/main.py",
    "src/income_analytics/api/static/index.html",
    "alembic/env.py",
}
FORBIDDEN = {"data", ".git", ".venv", "__pycache__", "node_modules", "tmp", "backups"}
SECRET = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    rb"\"type\"\s*:\s*\"service_account\"|"
    rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AIza[\w-]{35})"
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode()


def safe_name(name):
    path = PurePosixPath(name)
    if (
        not name or path.is_absolute() or "\\" in name or ":" in name
        or any(p in {"", ".", ".."} for p in name.split("/"))
        or any(p.lower() in FORBIDDEN for p in path.parts)
        or path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".log", ".tmp", ".pyc", ".pem"}
        or any(p.startswith(".env") or "service-account" in p.lower() for p in path.parts)
    ):
        raise ValueError("UNSAFE_ARTIFACT_PATH")


def check_content(name, data):
    safe_name(name)
    if not name.startswith("wheelhouse/") and SECRET.search(data):
        raise ValueError("SECRET_PATTERN_IN_ARTIFACT")


def lock_entries(data):
    entries = {}
    for line in data.decode("utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([\w.-]+)==([\w.+-]+) --hash=sha256:([a-f0-9]{64})", line)
        if not match:
            raise ValueError("UNLOCKED_DEPENDENCY")
        name = re.sub(r"[-_.]+", "-", match[1]).lower()
        if name in entries:
            raise ValueError("DUPLICATE_DEPENDENCY")
        entries[name] = (match[2], match[3])
    if not entries or "alembic" not in entries:
        raise ValueError("INCOMPLETE_RUNTIME_LOCK")
    return entries


def validate_payload(files):
    if not REQUIRED.issubset(files) or not any(
        p.startswith("alembic/versions/") and p.endswith(".py") for p in files
    ):
        raise ValueError("INCOMPLETE_APPLICATION")
    for name, data in files.items():
        check_content(name, data)
        if not (
            name in SUPPORT.values() or name.startswith(PREFIXES)
            or (name.startswith("wheelhouse/") and name.endswith(".whl"))
        ):
            raise ValueError("UNEXPECTED_APPLICATION_FILE")
    expected = lock_entries(files["requirements.lock"])
    actual = {}
    for name, data in files.items():
        if name.startswith("wheelhouse/"):
            parts = PurePosixPath(name).name.split("-")
            key = re.sub(r"[-_.]+", "-", parts[0]).lower()
            if key in actual:
                raise ValueError("DUPLICATE_WHEEL")
            actual[key] = (parts[1], sha(data))
    if actual != expected:
        raise ValueError("WHEELHOUSE_LOCK_MISMATCH")


def verify(archive, expected_commit, expected_digest=None):
    if not re.fullmatch(r"[a-f0-9]{40}", expected_commit):
        raise ValueError("INVALID_EXPECTED_COMMIT")
    digest = sha(archive.read_bytes())
    if expected_digest and digest != expected_digest:
        raise ValueError("ARTIFACT_DIGEST_MISMATCH")
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or names != sorted(names):
            raise ValueError("INVALID_ARCHIVE_STRUCTURE")
        for entry in bundle.infolist():
            safe_name(entry.filename)
            if entry.date_time != (1980, 1, 1, 0, 0, 0) or entry.external_attr >> 16 != 0o100644:
                raise ValueError("NONDETERMINISTIC_ARCHIVE_METADATA")
        if "manifest.json" not in names:
            raise ValueError("MISSING_MANIFEST")
        manifest_bytes = bundle.read("manifest.json")
        manifest = json.loads(manifest_bytes)
        if canonical(manifest) != manifest_bytes:
            raise ValueError("NONCANONICAL_MANIFEST")
        if (
            manifest["commit_sha"] != expected_commit or manifest["repository"] != REPOSITORY
            or manifest["format_version"] != FORMAT or manifest["python_version"] != PYTHON
        ):
            raise ValueError("PROVENANCE_MISMATCH")
        files = {name: bundle.read(name) for name in names if name != "manifest.json"}
    records = {name: {"sha256": sha(data), "size": len(data)} for name, data in files.items()}
    if records != manifest["files"]:
        raise ValueError("MANIFEST_CONTENT_MISMATCH")
    validate_payload(files)
    policy = json.loads(files["build-policy.json"])
    policy_inputs = {p: sha(files[p]) for p in policy["policy_inputs"]}
    if sha(canonical(policy_inputs)) != manifest["build_policy_sha256"]:
        raise ValueError("BUILD_POLICY_MISMATCH")
    source = {p: sha(b) for p, b in files.items() if not p.startswith("wheelhouse/")}
    if sha(canonical(source)) != manifest["source_fingerprint"]:
        raise ValueError("SOURCE_FINGERPRINT_MISMATCH")
    if policy["required_files"] != manifest["required_files"]:
        raise ValueError("REQUIRED_FILES_MISMATCH")
    if not set(manifest["required_files"]).issubset(files):
        raise ValueError("REQUIRED_FILE_MISSING")
    return {"sha256": digest, "commit_sha": expected_commit, "files": len(files), "status": "PASS"}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def build(root, wheels, output, source_ref):
    if sys.version.split()[0] != PYTHON or sys.platform != "win32":
        raise ValueError("BUILD_REQUIRES_WINDOWS_X64_PYTHON_3_14_7")
    if git(root, "status", "--porcelain", "--untracked-files=normal").strip():
        raise ValueError("BUILD_REQUIRES_CLEAN_CHECKOUT")
    commit = git(root, "rev-parse", "HEAD").decode().strip()
    names = git(
        root, "ls-tree", "-r", "--name-only", "HEAD", "--", "income-analytics"
    ).decode().splitlines()
    files = {}
    for full in names:
        name = full.removeprefix("income-analytics/")
        target = SUPPORT.get(name, name if name.startswith(PREFIXES) else None)
        if target:
            files[target] = git(root, "show", f"HEAD:{full}")
    for wheel in sorted(wheels.glob("*.whl")):
        files["wheelhouse/" + wheel.name] = wheel.read_bytes()
    validate_payload(files)
    policy = json.loads(files["build-policy.json"])
    required = policy["required_files"]
    if not set(required).issubset(files):
        raise ValueError("MISSING_POLICY_REQUIRED_FILE")
    manifest = {
        "format_version": FORMAT, "repository": REPOSITORY, "commit_sha": commit,
        "source_ref": source_ref or commit, "python_version": PYTHON,
        "node_version": "NOT_REQUIRED_STATIC_FRONTEND",
        "target": "windows-x64-cpython314", "required_files": required,
        "build_policy_sha256": sha(canonical({p: sha(files[p]) for p in policy["policy_inputs"]})),
        "source_fingerprint": sha(canonical({
            p: sha(b) for p, b in files.items() if not p.startswith("wheelhouse/")
        })),
        "files": {p: {"sha256": sha(b), "size": len(b)} for p, b in sorted(files.items())},
    }
    files["manifest.json"] = canonical(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as bundle:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_STORED
            bundle.writestr(entry, data)
    result = verify(output, commit)
    output.with_suffix(".sha256").write_text(result["sha256"] + "  " + output.name + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    create = subs.add_parser("build")
    create.add_argument("--root", type=Path, required=True)
    create.add_argument("--wheels", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--source-ref", default="")
    check = subs.add_parser("verify")
    check.add_argument("archive", type=Path)
    check.add_argument("--commit", required=True)
    check.add_argument("--sha256")
    args = parser.parse_args()
    if args.command == "build":
        result = build(args.root, args.wheels, args.output, args.source_ref)
    else:
        result = verify(args.archive, args.commit, args.sha256)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
