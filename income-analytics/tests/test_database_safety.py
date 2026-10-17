from __future__ import annotations

import os
from pathlib import Path

from income_analytics.infrastructure.database import database_url


def test_pytest_uses_an_isolated_temporary_database() -> None:
    assert os.environ["INCOME_ANALYTICS_TESTING"] == "1"
    configured = Path(os.environ["INCOME_ANALYTICS_DATABASE"]).resolve()
    production = Path("income_analytics.db").resolve()
    assert configured != production
    assert configured.parent == Path(os.environ["TEMP"]).resolve()
    assert configured.as_posix() in database_url()
