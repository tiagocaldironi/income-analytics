"""Observe executed application dependencies during scoped tests, not import statements.

No arguments, values, local paths, credentials or financial records are collected.
This supports an applicability review; absence in a trace is not a universal proof.
"""

import json
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALLS = set()
DEFINITIONS = set()
PREVIOUS = None
PREVIOUS_THREAD = None


def observe(frame, event, arg):
    if event != "call" or frame.f_code.co_name == "<module>":
        return
    module = frame.f_globals.get("__name__", "")
    if module.startswith("income_analytics."):
        identity = module + ":" + frame.f_code.co_qualname
        # Class bodies have no CO_NEWLOCALS; Python 3.14 annotation thunks and
        # dataclasses' generated builders are definitions, not ranking calls.
        # Retain them separately so the review can see the import dependency.
        definition = (
            not frame.f_code.co_flags & 2
            or frame.f_code.co_name == "__annotate__"
            or frame.f_code.co_name == "__create_fn__"
        )
        (DEFINITIONS if definition else CALLS).add(identity)


def pytest_sessionstart(session):
    global PREVIOUS, PREVIOUS_THREAD
    CALLS.clear()
    DEFINITIONS.clear()
    PREVIOUS = sys.getprofile()
    PREVIOUS_THREAD = threading.getprofile()
    sys.setprofile(observe)
    threading.setprofile(observe)


def pytest_sessionfinish(session, exitstatus):
    sys.setprofile(PREVIOUS)
    threading.setprofile(PREVIOUS_THREAD)
    destination = os.environ.get("CI_SCOPED_FINANCIAL_TRACE")
    if destination:
        Path(destination).write_text(
            json.dumps({"schema": 1, "calls": sorted(CALLS),
                        "definitions": sorted(DEFINITIONS)}, indent=2) + "\n",
            encoding="utf-8",
        )
