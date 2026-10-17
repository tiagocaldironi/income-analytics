from datetime import date
from decimal import Decimal

from income_analytics.application.fx_data import FxRateObservation
from income_analytics.infrastructure.sqlite_repositories import SqliteFxRateRepository


def test_fx_rate_bulk_upsert_keeps_latest_value_for_each_date() -> None:
    repository = SqliteFxRateRepository()
    day = date(2026, 1, 2)
    repository.save_many(
        (
            FxRateObservation(
                base_currency="USD",
                quote_currency="BRL",
                rate=Decimal("5.1"),
                effective_date=day,
                source="fixture",
            ),
            FxRateObservation(
                base_currency="USD",
                quote_currency="BRL",
                rate=Decimal("5.2"),
                effective_date=day,
                source="corrected",
            ),
            FxRateObservation(
                base_currency="USD",
                quote_currency="BRL",
                rate=Decimal("5.3"),
                effective_date=date(2026, 1, 3),
                source="fixture",
            ),
        )
    )

    saved = repository.list("USD", "BRL")
    assert [(item.effective_date, item.rate, item.source) for item in saved] == [
        (day, Decimal("5.2"), "corrected"),
        (date(2026, 1, 3), Decimal("5.3"), "fixture"),
    ]
