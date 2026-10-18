from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from income_analytics.api.routers.dashboard import _effective_analysis_end_date


def test_effective_analysis_end_date_caps_future_periods_at_today() -> None:
    today = date.today()

    result = _effective_analysis_end_date(today - timedelta(days=1), today + timedelta(days=30))

    assert result == today


def test_effective_analysis_end_date_rejects_an_entirely_future_period() -> None:
    tomorrow = date.today() + timedelta(days=1)

    with pytest.raises(HTTPException, match="não possui dias realizados"):
        _effective_analysis_end_date(tomorrow, tomorrow)
