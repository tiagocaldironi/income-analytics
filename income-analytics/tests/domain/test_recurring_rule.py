from datetime import date
from decimal import Decimal

from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.recurring_rule import RecurrenceFrequency, RecurringRule


def test_monthly_rule_advances_on_short_months_without_duplicate_date() -> None:
    rule = RecurringRule(
        event_type=FinancialEventType.DEPOSIT, amount=Decimal("100"),
        frequency=RecurrenceFrequency.MONTHLY, next_execution_date=date(2026, 1, 31),
    )

    assert rule.advance().next_execution_date == date(2026, 2, 28)


def test_rule_becomes_inactive_after_its_last_allowed_execution() -> None:
    rule = RecurringRule(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("100"),
        frequency=RecurrenceFrequency.MONTHLY,
        next_execution_date=date(2026, 1, 31),
        end_execution_date=date(2026, 2, 28),
    )

    assert rule.advance().active is True
    assert rule.advance().advance().active is False
