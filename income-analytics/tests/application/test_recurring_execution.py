from datetime import date
from decimal import Decimal

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.recurring_rule import RecurrenceFrequency, RecurringRule


def test_due_recurring_flow_executes_once_and_advances_cursor() -> None:
    session = PortfolioSession()
    rule = RecurringRule(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("100"),
        frequency=RecurrenceFrequency.MONTHLY,
        next_execution_date=date(2026, 1, 1),
    )
    session.schedule_recurring_rule(rule)

    first = session.execute_recurring_rules(through=date(2026, 1, 1))
    second = session.execute_recurring_rules(through=date(2026, 1, 1))

    assert first == (rule.id,)
    assert second == ()
    assert len(session.history()) == 1
    assert session._recurring_rules[rule.id].next_execution_date == date(2026, 2, 1)


def test_past_rule_executes_only_until_its_end_date_and_never_creates_future_events() -> None:
    session = PortfolioSession()
    rule = RecurringRule(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("100"),
        frequency=RecurrenceFrequency.MONTHLY,
        next_execution_date=date(2026, 1, 15),
        end_execution_date=date(2026, 3, 15),
    )
    session.schedule_recurring_rule(rule)

    executed = session.execute_recurring_rules(through=date(2026, 8, 1))

    assert executed == (rule.id, rule.id, rule.id)
    assert [event.effective_date for event in session.history()] == [
        date(2026, 1, 15),
        date(2026, 2, 15),
        date(2026, 3, 15),
    ]
    assert session._recurring_rules[rule.id].active is False
    assert session._recurring_rules[rule.id].next_execution_date == date(2026, 4, 15)


def test_deleting_rule_preserves_financial_events_already_created() -> None:
    session = PortfolioSession()
    rule = RecurringRule(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("100"),
        frequency=RecurrenceFrequency.MONTHLY,
        next_execution_date=date(2026, 1, 1),
    )
    session.schedule_recurring_rule(rule)
    session.execute_recurring_rules(through=date(2026, 1, 1))

    session.delete_recurring_rule(rule.id)

    assert session.history()[0].effective_date == date(2026, 1, 1)
    assert session.recurring_rules() == ()
