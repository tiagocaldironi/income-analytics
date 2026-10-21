from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from income_analytics.application.income_starter import (
    IncomeStarterError,
    ReserveJourneyRepository,
)
from income_analytics.infrastructure.database import Base
from income_analytics.infrastructure.models import (
    FinancialEventRecord,
    IncomeStarterJourneyProgressRecord,
    PortfolioRecord,
)

PORTFOLIO_A = UUID("7a54eeb7-542a-5832-8544-8be7dcb0237e")
PORTFOLIO_B = UUID("11111111-1111-4111-8111-111111111111")


@pytest.fixture
def repository(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'reserve.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    now = datetime.now(UTC)
    with sessions.begin() as session:
        for portfolio_id in (PORTFOLIO_A, PORTFOLIO_B):
            session.add(
                PortfolioRecord(
                    id=str(portfolio_id),
                    name=str(portfolio_id),
                    base_currency="BRL",
                    status="ACTIVE",
                    created_at=now,
                    updated_at=now,
                )
            )
    yield ReserveJourneyRepository(sessions, initialize=lambda: None), sessions
    engine.dispose()


def save(repository, portfolio, *, expenses="5000", months=6, reserved="12000", step=3):
    return repository.save(
        portfolio,
        essential_monthly_expenses=Decimal(expenses) if expenses is not None else None,
        coverage_months=months,
        declared_reserved_amount=Decimal(reserved),
        current_step=step,
    )


def test_reserve_goal_progress_and_coverage_are_calculated(repository):
    repo, _ = repository
    result = save(repo, PORTFOLIO_A)

    assert result["reserve_goal"] == "30000"
    assert result["progress_percent"] == "40.0"
    assert result["remaining_amount"] == "18000"
    assert result["months_covered"] == "2.4"
    assert result["goal_reached"] is False
    assert result["value_source"] == "SELF_DECLARED"


def test_progress_is_upserted_per_portfolio_and_zero_goal_is_safe(repository):
    repo, sessions = repository
    first = save(repo, PORTFOLIO_A)
    updated = save(repo, PORTFOLIO_A, expenses="0", months=6, reserved="25", step=4)
    other = repo.get(PORTFOLIO_B)

    assert first["updated_at"] != updated["updated_at"]
    assert updated["progress_percent"] == "100"
    assert updated["goal_reached"] is True
    assert updated["months_covered"] is None
    assert other["reserve_goal"] is None
    with sessions() as session:
        count = session.scalar(select(func.count()).select_from(IncomeStarterJourneyProgressRecord))
        financial_events = session.scalar(select(func.count()).select_from(FinancialEventRecord))
    assert count == 1
    assert financial_events == 0


@pytest.mark.parametrize(
    ("expenses", "reserved", "months", "step"),
    [("-1", "0", 6, 1), ("100", "-1", 6, 1), ("100", "0", 0, 1), ("100", "0", 6, 5)],
)
def test_invalid_values_are_rejected(repository, expenses, reserved, months, step):
    repo, _ = repository
    with pytest.raises(IncomeStarterError):
        save(repo, PORTFOLIO_A, expenses=expenses, reserved=reserved, months=months, step=step)
