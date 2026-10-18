from datetime import date
from decimal import Decimal

from spikes.paid_income.models import IncomeType
from spikes.paid_income.provider import normalize_event, parse_date, parse_decimal


def test_normalizes_paid_jcp_with_decimal_and_dates() -> None:
    event = normalize_event(
        "TASA4",
        {
            "label": "JCP",
            "rate": "0.1234",
            "lastDatePrior": "2026-01-03T03:00:00Z",
            "paymentDate": "2026-01-20T03:00:00Z",
        },
    )
    assert event is not None
    assert event.income_type is IncomeType.JCP
    assert event.amount_per_unit == Decimal("0.1234")
    assert event.record_date == date(2026, 1, 3)


def test_missing_payment_date_is_not_paid_income() -> None:
    assert normalize_event("GGRC11", {"label": "RENDIMENTO", "rate": "0.10"}) is None


def test_parsers_do_not_invent_missing_values() -> None:
    assert parse_date(None) is None
    assert parse_decimal(None) is None
