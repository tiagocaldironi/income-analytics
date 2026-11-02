from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import event

from income_analytics.api.routers.dashboard import _serialize_asset_transaction
from income_analytics.application.auth_context import Principal, principal_context
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.entities.portfolio import Portfolio
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.infrastructure.database import SessionFactory, engine, initialize_database
from income_analytics.infrastructure.models import PortfolioAssetMetadataRecord, UserRecord
from income_analytics.infrastructure.sqlite_repositories import (
    SqliteAssetRepository,
    SqlitePortfolioRepository,
)


def test_history_queries_are_bounded_and_preserve_scoped_metadata(monkeypatch):
    initialize_database()
    owner, wallet, other = uuid4(), uuid4(), uuid4()
    with SessionFactory.begin() as db:
        db.add(UserRecord(id=str(owner), status="ACTIVE"))
    for identifier in (wallet, other):
        SqlitePortfolioRepository().save(Portfolio(
            id=identifier, owner_user_id=owner, name=f"History {identifier}",
        ))
    full = PortfolioSession(portfolio_id=wallet, persistent=True)
    for index in range(20):
        full.register_trade(
            ticker=f"Q{uuid4().hex[:6]}{index}", event_type=FinancialEventType.BUY,
            quantity=Decimal("2"), unit_price=Decimal("10"),
            effective_date=date(2026, 10, 1),
        )
    asset = next(iter(full._assets.values()))
    SqliteAssetRepository(other).link(asset.id)
    with SessionFactory.begin() as db:
        for identifier, label, classification in (
            (wallet, "My scoped asset", "BRAZILIAN_ETF"),
            (other, "Other scoped asset", "FII"),
        ):
            db.add(PortfolioAssetMetadataRecord(
                portfolio_id=str(identifier), asset_id=str(asset.id),
                payload='{"name":"' + label + '","asset_class":"' + classification + '"}',
            ))
    monkeypatch.setenv("INCOME_AUTH_MODE", "firebase")
    token = principal_context.set(Principal(owner, "test-history"))
    queries = []

    def record_query(conn, cursor, statement, *args):
        queries.append(statement)

    try:
        event.listen(engine, "before_cursor_execute", record_query)
        try:
            history = PortfolioSession(portfolio_id=wallet, persistent=True, history_only=True)
        finally:
            event.remove(engine, "before_cursor_execute", record_query)
        assert len(queries) == 5
        assert len(history.history()) == 20
        assert history._assets[str(asset.ticker)].name == "My scoped asset"
        assert history._assets[str(asset.ticker)].asset_class == AssetClass.BRAZILIAN_ETF
        other_assets = SqliteAssetRepository(other).list()
        assert len(other_assets) == 1
        assert other_assets[0].name == "Other scoped asset"
        assert other_assets[0].asset_class == AssetClass.FII
        complete = PortfolioSession(portfolio_id=wallet, persistent=True)
        assert [_serialize_asset_transaction(item) for item in history.history()] == [
            _serialize_asset_transaction(item) for item in complete.history()
        ]
        assert history._fixed_income_details == complete._fixed_income_details
    finally:
        principal_context.reset(token)
