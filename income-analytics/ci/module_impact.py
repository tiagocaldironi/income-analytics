"""Conservative path ownership for independent core and Magic Formula CI."""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "ci/module_ownership.json"


def classify_path(path: str, policy: dict | None = None) -> str:
    normalized = path.replace("\\", "/").removeprefix("income-analytics/")
    rules = policy or json.loads(POLICY.read_text(encoding="utf-8"))
    shared = any(fnmatch.fnmatchcase(normalized, rule) for rule in rules["shared"])
    magic = any(fnmatch.fnmatchcase(normalized, rule) for rule in rules["magic_formula"])
    if shared:
        return "shared"
    if magic:
        return "magic_formula"
    if normalized.startswith(("src/", "tests/", "alembic/", "scripts/")):
        return "core"
    return "shared"


def classify_changes(paths: list[str]) -> set[str]:
    scopes = {classify_path(path) for path in paths}
    if not scopes:
        return {"shared"}
    return scopes


def should_run_magic_formula(scopes: set[str]) -> bool:
    return bool(scopes & {"magic_formula", "shared"})


def should_run_core(scopes: set[str]) -> bool:
    return bool(scopes & {"core", "shared"})


def engineering_decision(
    scopes: set[str],
    *,
    core_pass: bool,
    magic_formula_pass: bool,
    shared_pass: bool,
    security_pass: bool,
    build_pass: bool,
) -> bool:
    """Shared controls are mandatory; domain gates follow changed ownership."""
    if not (shared_pass and security_pass and build_pass):
        return False
    if "shared" in scopes and not (core_pass and magic_formula_pass):
        return False
    if "core" in scopes and not core_pass:
        return False
    if "magic_formula" in scopes and not magic_formula_pass:
        return False
    return True
