"""CI policy only; never loaded by the application or normal pytest invocation."""

from pathlib import Path

import pytest

EXTERNAL_SUITES = {"test_firebase_emulator.py", "test_firebase_live.py"}


def pytest_collection_modifyitems(items):
    for item in items:
        if Path(item.path).name in EXTERNAL_SUITES:
            item.add_marker(pytest.mark.skip(reason="CI offline: emulator/cloud run separately"))


def pytest_report_header():
    return "CI offline: temporary SQLite, no credentials, network denied; CERT_48 not waived"
