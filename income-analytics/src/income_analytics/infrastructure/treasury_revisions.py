"""Owner-scoped, compare-and-swap persistence for audited treasury amendments."""

import json
from uuid import UUID

from sqlalchemy import select, update

from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.infrastructure.database import SessionFactory
from income_analytics.infrastructure.models import FinancialEventRecord


def save_revision(event: FinancialEvent, portfolio_id: UUID, expected_revision: int) -> None:
    with SessionFactory.begin() as db:
        row = db.scalar(
            select(FinancialEventRecord).where(
                FinancialEventRecord.id == str(event.id),
                FinancialEventRecord.portfolio_id == str(portfolio_id),
            )
        )
        if row is None:
            raise ValueError("Lançamento não encontrado nesta carteira.")
        raw = row.metadata_json
        metadata = json.loads(raw) if raw else {}
        revisions = metadata.get("treasury_revisions", [])
        if not isinstance(revisions, list) or len(revisions) != expected_revision:
            raise ValueError("O lançamento foi alterado; recarregue antes de editar.")
        statement = (
            update(FinancialEventRecord)
            .where(
                FinancialEventRecord.id == str(event.id),
                FinancialEventRecord.portfolio_id == str(portfolio_id),
                FinancialEventRecord.metadata_json == raw,
            )
            .values(
                quantity=str(event.quantity.value) if event.quantity else None,
                unit_price=str(event.unit_price.amount) if event.unit_price else None,
                effective_date=event.effective_date,
                metadata_json=json.dumps(dict(event.metadata)),
            )
        )
        updated_id = db.execute(statement.returning(FinancialEventRecord.id)).scalar_one_or_none()
        if updated_id != str(event.id):
            raise ValueError("O lançamento foi alterado; recarregue antes de editar.")
    # The existing write repository owns this derived cache.
    from income_analytics.infrastructure.sqlite_repositories import _cached_financial_events

    _cached_financial_events.cache_clear()
