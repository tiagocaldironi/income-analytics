"""Audit collection and deselect only explicit gate scopes; never add skip/xfail."""

import json
import os
from pathlib import Path

from gate_policy import GROUPS, ROOT, test_scope

INVENTORY = []


def pytest_addoption(parser):
    parser.addoption("--ci-gate", choices=("full", "engineering", "financial"), default="full")


def pytest_collection_modifyitems(config, items):
    gate = config.getoption("--ci-gate")
    selected, excluded = [], []
    for item in items:
        try:
            file = item.path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            file = "temporary-tests/" + item.path.name
        suffix = item.nodeid.split("::", 1)[1]
        entry = test_scope(file + "::" + suffix)
        entry["line"] = item.location[1] + 1
        entry["selected"] = gate == "full" or entry[gate]
        entry["result"] = "NOT_RUN" if entry["selected"] else "DESELECTED_TO_EXPLICIT_OTHER_GATE"
        INVENTORY.append(entry)
        (selected if entry["selected"] else excluded).append(item)
    if gate != "full":
        config.hook.pytest_deselected(items=excluded)
        items[:] = selected
    # Missing known cases is a collection error, not a silent certification improvement.
    if gate in {"full", "financial"}:
        required = set(GROUPS["historical_reference_tests"] + GROUPS["frozen_integrity_tests"])
        collected = {entry["nodeid"] for entry in INVENTORY}
        if not required.issubset(collected):
            raise ValueError("CERTIFICATION_CASES_MISSING_FROM_COLLECTION")


def pytest_sessionfinish(session, exitstatus):
    destination = os.environ.get("CI_TEST_INVENTORY")
    if destination:
        Path(destination).write_text(json.dumps(INVENTORY, indent=2) + "\n", encoding="utf-8")
