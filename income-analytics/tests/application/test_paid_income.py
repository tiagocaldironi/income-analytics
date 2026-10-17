from datetime import date
from decimal import Decimal

from income_analytics.application.paid_income import (
    IncomeType,
    PaidIncomeIntegrationStatus,
    PaidIncomeSettings,
    PaidIncomeSyncService,
)
from income_analytics.infrastructure.brapi_paid_income import normalize_event


def test_brapi_payload_is_normalized_with_decimal_and_dates() -> None:
    event = normalize_event(
        "TASA4",
        {
            "rate": "0.15",
            "lastDatePrior": "2026-06-10",
            "paymentDate": "2026-06-25",
            "approvedOn": "2026-06-01",
            "label": "JCP",
        },
    )
    assert event is not None
    assert event.amount_per_unit == Decimal("0.15")
    assert event.record_date == date(2026, 6, 10)
    assert event.payment_date == date(2026, 6, 25)
    assert event.approval_date == date(2026, 6, 1)
    assert event.income_type is IncomeType.JCP


def test_disabled_sync_never_calls_provider() -> None:
    class Settings:
        def get(self):
            return PaidIncomeSettings(enabled=False)

        def save(self, value):
            raise AssertionError("must not save")

    class Imports:
        pass

    class Provider:
        def get_paid_income(self, *args):
            raise AssertionError("must not call provider")

    result = PaidIncomeSyncService(Settings(), Imports()).sync(object(), Provider())
    assert result["status"] is PaidIncomeIntegrationStatus.DISABLED


def test_missing_payment_date_is_not_normalized() -> None:
    assert normalize_event("GGRC11", {"rate": "0.10", "label": "RENDIMENTO"}) is None
