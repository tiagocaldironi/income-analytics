"""Fail-closed static dependency closure for release applicability."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ANALYZER_VERSION = 1
INTERNAL_ROOTS = ("income_analytics", "tests", "ci")
VISUAL_SUFFIXES = {".css"}
LOCK_FILES = {"ci/runtime-windows-py314.lock", "ci/requirements-windows-py314.lock"}
KNOWN_NONEXECUTABLE_FILES = {"ci/release-applicability-policy.json"}
LOCK_LINE = re.compile(r"([\w.-]+)==([\w.+-]+) --hash=sha256:([a-f0-9]{64})")


def _pypi_release(name: str, version: str) -> dict:
    url = "https://pypi.org/pypi/" + urllib.parse.quote(name, safe="") + "/" + \
        urllib.parse.quote(version, safe="") + "/json"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if int(response.headers.get("Content-Length", "0")) > 4 * 1024 * 1024:
                raise ValueError("PYPI_METADATA_TOO_LARGE")
            payload = response.read(4 * 1024 * 1024 + 1)
        if len(payload) > 4 * 1024 * 1024:
            raise ValueError("PYPI_METADATA_TOO_LARGE")
        return json.loads(payload)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise ValueError("PYPI_METADATA_UNAVAILABLE") from error


def _module_for(path: Path, root: Path) -> str | None:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[0] == "src":
        parts.pop(0)
    if parts[-1] == "__init__":
        parts.pop()
    if not parts or parts[0] not in INTERNAL_ROOTS:
        return None
    return ".".join(parts)


def _internal(name: str) -> bool:
    return any(name == prefix or name.startswith(prefix + ".") for prefix in INTERNAL_ROOTS)


def _imports(tree: ast.AST, module: str, modules: dict[str, Path]) -> tuple[set[str], bool]:
    dependencies: set[str] = set()
    complete = True
    dynamic_names = {"__import__", "import_module"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in {"importlib", "builtins"}:
            for alias in node.names:
                if alias.name in dynamic_names:
                    dynamic_names.add(alias.asname or alias.name)
    source_path = modules[module]
    package = module if source_path.name == "__init__.py" else module.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                internal_name = alias.name if _internal(alias.name) else (
                    "ci." + alias.name if "ci." + alias.name in modules else None
                )
                if internal_name:
                    if internal_name in modules:
                        dependencies.add(internal_name)
                    else:
                        complete = False
        elif isinstance(node, ast.ImportFrom):
            target = node.module or ""
            if node.level:
                try:
                    target = importlib.util.resolve_name("." * node.level + target, package)
                except (ImportError, ValueError):
                    complete = False
                    continue
            internal_target = target if _internal(target) else (
                "ci." + target if "ci." + target in modules else None
            )
            if internal_target:
                target = internal_target
                if target not in modules:
                    complete = False
                    continue
                dependencies.add(target)
                for alias in node.names:
                    if alias.name == "*":
                        complete = False
                        continue
                    imported = target + "." + alias.name
                    if imported in modules:
                        dependencies.add(imported)
        elif isinstance(node, ast.Call):
            func = node.func
            is_dynamic = (isinstance(func, ast.Name) and func.id in dynamic_names) or (
                isinstance(func, ast.Attribute) and func.attr in {"import_module", "__import__"}
            )
            if is_dynamic:
                literal_name = (
                    node.args[0].value
                    if node.args and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                    else None
                )
                if literal_name is None:
                    complete = False
                    continue
                if _internal(literal_name):
                    dependencies.add(literal_name)
                    if literal_name in modules:
                        continue
                    else:
                        complete = False
    return dependencies, complete


def analyze_changed_dependencies(root: Path, paths: list[str]) -> dict:
    """Resolve changed Python modules through their transitive static imports.

    CSS changes are a known non-executable visual scope. Every other changed
    path must map to a parseable Python module or the analysis remains blocked.
    """
    app_root = root.resolve()
    module_files: dict[str, Path] = {}
    for base_name in ("src", "tests", "ci"):
        base = app_root / base_name
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            module = _module_for(path, app_root)
            if module:
                module_files[module] = path

    changed_modules: set[str] = set()
    runtime_paths: list[str] = []
    complete = bool(paths)
    unclassified: list[str] = []
    for raw in paths:
        normalized = raw.replace("\\", "/").removeprefix("income-analytics/")
        path = (app_root / normalized).resolve()
        try:
            path.relative_to(app_root)
        except ValueError:
            complete = False
            unclassified.append(normalized)
            continue
        if path.suffix.lower() in VISUAL_SUFFIXES and "/static/css/" in normalized:
            continue
        if normalized in LOCK_FILES or normalized == "pyproject.toml":
            runtime_paths.append(normalized)
            continue
        if normalized in KNOWN_NONEXECUTABLE_FILES:
            continue
        module = _module_for(path, app_root) if path.suffix == ".py" and path.is_file() else None
        if module is None:
            complete = False
            unclassified.append(normalized)
            continue
        changed_modules.add(module)

    reachable: set[str] = set()
    scanned: dict[str, str] = {}
    pending = list(sorted(changed_modules))
    while pending:
        module = pending.pop()
        if module in reachable:
            continue
        reachable.add(module)
        source = module_files.get(module)
        if source is None:
            complete = False
            unclassified.append(module)
            continue
        try:
            content = source.read_bytes()
            tree = ast.parse(content, filename=str(source))
        except (OSError, SyntaxError, UnicodeError):
            complete = False
            continue
        scanned[module] = hashlib.sha256(content).hexdigest()
        dependencies, imports_complete = _imports(tree, module, module_files)
        complete = complete and imports_complete
        pending.extend(sorted(dependencies - reachable))

    runtime = {"status": "NOT_APPLICABLE", "complete": True, "changes": [], "evidence": []}
    if runtime_paths:
        runtime = {"status": "BLOCKED", "complete": False, "changes": [],
                   "evidence": ["RUNTIME_BASE_COMPARISON_REQUIRED"]}
    return {
        "analyzer_version": ANALYZER_VERSION,
        "complete": complete,
        "changed_modules": sorted(changed_modules),
        "modules": sorted(reachable),
        "source_sha256": scanned,
        "unclassified_paths": sorted(set(unclassified)),
        "runtime_dependency": runtime,
    }


def _lock_entries(content: bytes) -> dict[str, tuple[str, str]]:
    result = {}
    for line in content.decode("utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match = LOCK_LINE.fullmatch(line)
        if not match:
            raise ValueError("UNLOCKED_RUNTIME_DEPENDENCY")
        name = re.sub(r"[-_.]+", "-", match[1]).lower()
        if name in result:
            raise ValueError("DUPLICATE_RUNTIME_DEPENDENCY")
        result[name] = (match[2], match[3])
    if not result:
        raise ValueError("EMPTY_RUNTIME_LOCK")
    return result


def analyze_runtime_dependency(root: Path, paths: list[str], base_sha: str) -> dict:
    """Compare shared runtime locks against the PR base and inspect installed metadata.

    A package version/hash change is recorded as shared runtime impact. Missing base
    bytes or consumer metadata keeps the release blocked; no historical control is
    waived by this analysis.
    """
    normalized = sorted({p.replace("\\", "/").removeprefix("income-analytics/") for p in paths})
    changed = sorted(set(normalized).intersection(LOCK_FILES))
    if "pyproject.toml" in normalized:
        return {"status": "BLOCKED", "complete": False, "changes": [],
                "evidence": ["PYPROJECT_RUNTIME_CHANGE_REQUIRES_LOCK_REVIEW"]}
    if not changed:
        return {"status": "NOT_APPLICABLE", "complete": True, "changes": [], "evidence": []}
    if not re.fullmatch(r"[0-9a-f]{40}", base_sha):
        return {"status": "BLOCKED", "complete": False, "changes": [],
                "evidence": ["RUNTIME_BASE_SHA_MISSING"]}
    package_changes = []
    try:
        for path in changed:
            prior = subprocess.run(
                ["git", "show", f"{base_sha}:income-analytics/{path}"],
                cwd=root, capture_output=True, check=True,
            ).stdout
            old = _lock_entries(prior)
            new = _lock_entries((root / path).read_bytes())
            for name in sorted(set(old) | set(new)):
                if old.get(name) != new.get(name):
                    package_changes.append({"path": path, "name": name,
                                            "before": old.get(name), "after": new.get(name)})
        if not package_changes:
            return {"status": "PASS", "complete": True, "changes": [],
                    "evidence": ["LOCK_BYTES_REVIEWED_NO_RUNTIME_DELTA"]}
        consumers = []
        metadata_complete = True
        changed_names = {item["name"] for item in package_changes}
        runtime_lock = _lock_entries((root / "ci/runtime-windows-py314.lock").read_bytes())
        pypi = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                name: pool.submit(_pypi_release, name, version)
                for name, (version, _digest) in runtime_lock.items()
            }
            for name, future in futures.items():
                try:
                    payload = future.result(timeout=30)
                    info = payload.get("info", {})
                    expected_version, expected_hash = runtime_lock[name]
                    wheel_hashes = {
                        item.get("digests", {}).get("sha256")
                        for item in payload.get("urls", [])
                        if item.get("packagetype") == "bdist_wheel"
                    }
                    if info.get("version") != expected_version or expected_hash not in wheel_hashes:
                        metadata_complete = False
                    pypi[name] = info
                except Exception:
                    metadata_complete = False
        try:
            from packaging.requirements import Requirement
            from packaging.markers import default_environment
            from packaging.version import Version
        except ImportError:
            Requirement = None
            metadata_complete = False
        if Requirement is not None:
            for consumer, info in pypi.items():
                for raw_requirement in info.get("requires_dist") or []:
                    try:
                        requirement = Requirement(raw_requirement)
                    except Exception:
                        metadata_complete = False
                        continue
                    required_name = re.sub(r"[-_.]+", "-", requirement.name).lower()
                    if required_name not in changed_names:
                        continue
                    environment = default_environment()
                    environment.update({"python_version": "3.14", "python_full_version": "3.14.7",
                                        "sys_platform": "win32", "platform_system": "Windows",
                                        "platform_machine": "AMD64", "implementation_name": "cpython",
                                        "extra": ""})
                    if requirement.marker is not None and not requirement.marker.evaluate(environment):
                        continue
                    consumers.append({"consumer": consumer, "requirement": raw_requirement})
                    changed_version = next(item["after"][0] for item in package_changes
                                           if item["name"] == required_name)
                    if Version(changed_version) not in requirement.specifier:
                        metadata_complete = False
            changed_package_dependencies = []
            for changed_name in changed_names:
                info = pypi.get(changed_name)
                if not info:
                    metadata_complete = False
                    continue
                for raw_requirement in info.get("requires_dist") or []:
                    try:
                        requirement = Requirement(raw_requirement)
                        environment = default_environment()
                        environment.update({"python_version": "3.14", "python_full_version": "3.14.7",
                                            "sys_platform": "win32", "platform_system": "Windows",
                                            "platform_machine": "AMD64", "implementation_name": "cpython",
                                            "extra": ""})
                        if requirement.marker is not None and not requirement.marker.evaluate(environment):
                            continue
                        dependency_name = re.sub(r"[-_.]+", "-", requirement.name).lower()
                        dependency = runtime_lock.get(dependency_name)
                        if dependency is None or Version(dependency[0]) not in requirement.specifier:
                            metadata_complete = False
                        changed_package_dependencies.append({"package": changed_name,
                                                             "requirement": raw_requirement,
                                                             "locked_version": dependency[0] if dependency else None})
                    except Exception:
                        metadata_complete = False
        else:
            changed_package_dependencies = []
        evidence = ["LOCKS_MATCHED_BASE_AND_CANDIDATE", "DEPENDENCY_METADATA_SCANNED"]
        if "opentelemetry-api" in changed_names:
            consumer = next((item for item in consumers if item["consumer"] == "google-api-core"), None)
            if consumer is None:
                metadata_complete = False
            if "opentelemetry-api" not in pypi:
                metadata_complete = False
            source_refs = []
            for source in (root / "src").rglob("*.py"):
                try:
                    tree = ast.parse(source.read_bytes(), filename=str(source))
                except (OSError, SyntaxError, UnicodeError):
                    metadata_complete = False
                    continue
                if any(
                    isinstance(node, ast.Import) and any(alias.name == "opentelemetry" or
                        alias.name.startswith("opentelemetry.") for alias in node.names)
                    or isinstance(node, ast.ImportFrom) and (node.module == "opentelemetry" or
                        (node.module or "").startswith("opentelemetry."))
                    for node in ast.walk(tree)
                ):
                    source_refs.append(source.relative_to(root).as_posix())
            evidence.append("OPENTELEMETRY_TRANSITIVE_CONSUMERS_INSPECTED")
            evidence.append("APPLICATION_OPENTELEMETRY_IMPORT_SCAN_COMPLETE")
        return {
            "status": "PASS" if metadata_complete else "BLOCKED",
            "complete": metadata_complete,
            "changes": package_changes,
            "consumers": sorted(consumers, key=lambda item: (item["consumer"], item["requirement"])),
            "changed_package_dependencies": changed_package_dependencies,
            "application_direct_references": source_refs if "opentelemetry-api" in changed_names else [],
            "evidence": evidence if metadata_complete else [*evidence, "DEPENDENCY_METADATA_INCOMPLETE"],
        }
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError):
        return {"status": "BLOCKED", "complete": False, "changes": [],
                "evidence": ["RUNTIME_LOCK_ANALYSIS_INCOMPLETE"]}
