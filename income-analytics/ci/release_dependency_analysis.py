"""Fail-closed static dependency closure for release applicability."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path

ANALYZER_VERSION = 1
INTERNAL_ROOTS = ("income_analytics", "tests")
VISUAL_SUFFIXES = {".css"}


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
                if _internal(alias.name):
                    if alias.name in modules:
                        dependencies.add(alias.name)
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
            if _internal(target):
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
                complete = False
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(
                    node.args[0].value, str
                ):
                    dynamic_name = node.args[0].value
                    if _internal(dynamic_name):
                        dependencies.add(dynamic_name)
    return dependencies, complete


def analyze_changed_dependencies(root: Path, paths: list[str]) -> dict:
    """Resolve changed Python modules through their transitive static imports.

    CSS changes are a known non-executable visual scope. Every other changed
    path must map to a parseable Python module or the analysis remains blocked.
    """
    app_root = root.resolve()
    module_files: dict[str, Path] = {}
    for base_name in ("src", "tests"):
        base = app_root / base_name
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            module = _module_for(path, app_root)
            if module:
                module_files[module] = path

    changed_modules: set[str] = set()
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

    return {
        "analyzer_version": ANALYZER_VERSION,
        "complete": complete,
        "changed_modules": sorted(changed_modules),
        "modules": sorted(reachable),
        "source_sha256": scanned,
        "unclassified_paths": sorted(set(unclassified)),
    }
