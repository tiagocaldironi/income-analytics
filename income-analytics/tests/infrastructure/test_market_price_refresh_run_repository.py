from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.infrastructure.sqlite_repositories import (
    SqliteMarketPriceRefreshRunRepository,
)


def test_refresh_run_history_keeps_structured_errors_queryable() -> None:
    repository = SqliteMarketPriceRefreshRunRepository(MAIN_PORTFOLIO_ID)
    started = datetime.now(UTC)
    providers = [
        {
            "provider": "b3",
            "status": "PARTIAL",
            "requested_assets": ["AAA3", "BBB3"],
            "resolved_assets": 1,
            "failed_assets": ["AAA3"],
            "errors": [
                {
                    "asset": "AAA3",
                    "stage": "single_quote",
                    "error_type": "MarketDataUnavailable",
                    "message": "Sem cotação para o ticker.",
                }
            ],
            "warnings": [],
            "effective_date": date(2026, 10, 28),
            "observed_at": started,
            "rate": Decimal("5.1234567890123456789"),
        }
    ]
    repository.save(
        {
            "id": "refresh-run-test",
            "started_at": started,
            "finished_at": started + timedelta(seconds=2),
            "status": "PARTIAL",
            "providers": providers,
        }
    )

    runs = repository.list_recent(1)

    assert len(runs) == 1
    assert runs[0]["id"] == "refresh-run-test"
    assert runs[0]["status"] == "PARTIAL"
    assert runs[0]["providers"][0]["errors"][0]["asset"] == "AAA3"
    assert runs[0]["providers"][0]["errors"][0]["message"] == "Sem cotação para o ticker."
    assert runs[0]["providers"][0]["effective_date"] == "2026-10-28"
    assert runs[0]["providers"][0]["observed_at"] == started.isoformat()
    assert runs[0]["providers"][0]["rate"] == "5.1234567890123456789"
