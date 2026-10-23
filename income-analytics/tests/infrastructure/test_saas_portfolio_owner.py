"""Ownership survives existing local lifecycle operations; HTTP auth is separate."""

from uuid import uuid4

from income_analytics.api.routers.portfolios import (
    PortfolioUpdate,
    archive_portfolio,
    rename_portfolio,
    restore_portfolio,
)
from income_analytics.domain.entities.portfolio import Portfolio
from income_analytics.infrastructure.database import SessionFactory, initialize_database
from income_analytics.infrastructure.models import UserRecord
from income_analytics.infrastructure.sqlite_repositories import SqlitePortfolioRepository


def test_owner_roundtrip_and_existing_lifecycle_preserve_binding():
    initialize_database()
    user_id, wallet_id = uuid4(), uuid4()
    with SessionFactory.begin() as session:
        session.add(UserRecord(id=str(user_id), status="ACTIVE"))
    repo = SqlitePortfolioRepository()
    repo.save(Portfolio(id=wallet_id, name=f"Owner {wallet_id}", owner_user_id=user_id))
    assert repo.get(wallet_id).owner_user_id == user_id
    assert next(p for p in repo.list() if p.id == wallet_id).owner_user_id == user_id
    rename_portfolio(wallet_id, PortfolioUpdate(name=f"Renamed {wallet_id}"))
    assert repo.get(wallet_id).owner_user_id == user_id
    archive_portfolio(wallet_id)
    assert repo.get(wallet_id).owner_user_id == user_id
    restore_portfolio(wallet_id)
    assert repo.get(wallet_id).owner_user_id == user_id
