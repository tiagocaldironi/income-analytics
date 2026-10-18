"""Global test isolation: test runs must never use the local portfolio database."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

_test_database = Path(gettempdir()) / f"income-analytics-pytest-{uuid4().hex}.db"
os.environ["INCOME_ANALYTICS_TESTING"] = "1"
os.environ["INCOME_ANALYTICS_DATABASE"] = str(_test_database)
