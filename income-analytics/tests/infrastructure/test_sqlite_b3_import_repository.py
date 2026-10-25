from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from income_analytics.application.b3_import import (
    B3ImportBatch,
    B3ImportBatchStatus,
    B3ImportedRecord,
    B3ImportedRecordStatus,
    B3ImportReportType,
)
from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.infrastructure.sqlite_repositories import SqliteB3ImportRepository


def _batch() -> B3ImportBatch:
    return B3ImportBatch(
        id=uuid4(),
        file_name="movimentacao.xlsx",
        file_hash="a" * 64,
        report_type=B3ImportReportType.MOVEMENT,
        total_rows=2,
        new_rows=2,
        duplicate_rows=0,
        review_rows=0,
        unsupported_rows=0,
        invalid_rows=0,
        status=B3ImportBatchStatus.PREVIEWED,
        created_at=datetime.now(UTC),
    )


def _record(batch: B3ImportBatch, occurrence_index: int = 1) -> B3ImportedRecord:
    return B3ImportedRecord(
        id=uuid4(),
        batch_id=batch.id,
        fingerprint=f"{batch.id.hex:0<64}"[:64],
        occurrence_index=occurrence_index,
        source_row=7,
        status=B3ImportedRecordStatus.NEW,
        event_date=date(2026, 1, 2),
        event_type="DIVIDEND",
        income_type="DIVIDEND",
        source_symbol="PETR4",
        normalized_symbol="PETR4",
        institution="Corretora",
        market="A vista",
        quantity=Decimal("10"),
        unit_price=Decimal("1.23"),
        total_value=Decimal("12.30"),
        raw_payload='{"ticker":"PETR4"}',
        detail=None,
    )


def test_persists_batch_and_decimal_source_record() -> None:
    repository = SqliteB3ImportRepository(MAIN_PORTFOLIO_ID)
    batch = _batch()
    record = _record(batch)

    repository.create_batch(batch)
    repository.save_record(record)

    loaded_batch = repository.get_batch(batch.id)
    loaded_record = repository.get_record_by_identity(record.fingerprint, 1)

    assert loaded_batch is not None
    assert loaded_batch.file_hash == batch.file_hash
    assert loaded_batch.report_type is B3ImportReportType.MOVEMENT
    assert loaded_record is not None
    assert loaded_record.institution == "Corretora"
    assert loaded_record.total_value == Decimal("12.30")


def test_occurrence_index_preserves_legitimate_duplicate_rows() -> None:
    repository = SqliteB3ImportRepository(MAIN_PORTFOLIO_ID)
    batch = _batch()
    repository.create_batch(batch)
    first = _record(batch, 1)
    second = _record(batch, 2)

    repository.save_record(first)
    repository.save_record(second)

    assert len(repository.list_records(batch.id)) == 2
    assert repository.get_record_by_identity(first.fingerprint, 1) is not None
    assert repository.get_record_by_identity(first.fingerprint, 2) is not None


def test_apply_batch_rolls_back_audit_write_when_operation_fails() -> None:
    repository = SqliteB3ImportRepository(MAIN_PORTFOLIO_ID)
    batch = _batch()
    record = _record(batch)
    repository.create_batch(batch)

    def fail_after_record(session: object, _: SqliteB3ImportRepository) -> None:
        repository.save_record_in_session(session, record)  # type: ignore[arg-type]
        raise RuntimeError("simulated failure")

    with pytest.raises(RuntimeError, match="simulated failure"):
        repository.apply_batch(batch.id, fail_after_record)

    assert repository.get_record_by_identity(record.fingerprint, 1) is None
    persisted_batch = repository.get_batch(batch.id)
    assert persisted_batch is not None
    assert persisted_batch.status is B3ImportBatchStatus.PREVIEWED


def _applied_trade():
    from dataclasses import replace

    from income_analytics.application.portfolio_session import PortfolioSession
    from income_analytics.domain.enums.financial_event_type import FinancialEventType

    session = PortfolioSession(portfolio_id=MAIN_PORTFOLIO_ID, persistent=True)
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="T" + uuid4().hex[:8].upper(),
        quantity=Decimal("2"),
        unit_price=Decimal("10"),
        effective_date=date(2026, 1, 2),
    )
    trade = session.history()[-1]
    repository = SqliteB3ImportRepository(MAIN_PORTFOLIO_ID)
    batch = _batch()
    repository.create_batch(batch)
    record = replace(
        _record(batch),
        status=B3ImportedRecordStatus.APPLIED,
        event_type="BUY",
        asset_id=trade.asset.id,
        financial_event_id=trade.id,
    )
    repository.save_record(record)
    return trade, record, repository


def test_delete_imported_trade_retains_source_tombstone_and_audit():
    from sqlalchemy import text

    from income_analytics.infrastructure.database import SessionFactory
    from income_analytics.infrastructure.models import SecurityAuditRecord
    from income_analytics.infrastructure.sqlite_repositories import SqliteFinancialEventRepository

    trade, source, imports = _applied_trade()
    repo = SqliteFinancialEventRepository(MAIN_PORTFOLIO_ID)
    assert repo.delete(str(trade.id))
    assert all(item.id != trade.id for item in repo.list())
    retained = imports.get_record_by_identity(source.fingerprint, 1)
    assert retained.financial_event_id is None
    assert retained.status is B3ImportedRecordStatus.APPLIED
    assert str(trade.id) in retained.detail
    assert retained.raw_payload == source.raw_payload
    with SessionFactory() as db:
        assert db.query(SecurityAuditRecord).filter_by(evidence_ref=str(trade.id)).count() == 1
        assert db.execute(text("PRAGMA foreign_key_check")).all() == []
    assert not repo.delete(str(trade.id))


def test_delete_cannot_detach_another_portfolios_import():
    from income_analytics.infrastructure.sqlite_repositories import SqliteFinancialEventRepository

    trade, source, imports = _applied_trade()
    assert not SqliteFinancialEventRepository(uuid4()).delete(str(trade.id))
    assert imports.get_record_by_identity(source.fingerprint, 1).financial_event_id == trade.id


def test_delete_failure_rolls_back_import_detachment_and_audit():
    from sqlalchemy import event

    from income_analytics.infrastructure.database import SessionFactory, engine
    from income_analytics.infrastructure.models import SecurityAuditRecord
    from income_analytics.infrastructure.sqlite_repositories import SqliteFinancialEventRepository

    trade, source, imports = _applied_trade()

    def fail_delete(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("DELETE FROM financial_events"):
            raise RuntimeError("simulated delete failure")

    event.listen(engine, "before_cursor_execute", fail_delete)
    try:
        with pytest.raises(RuntimeError, match="simulated delete failure"):
            SqliteFinancialEventRepository(MAIN_PORTFOLIO_ID).delete(str(trade.id))
    finally:
        event.remove(engine, "before_cursor_execute", fail_delete)
    assert imports.get_record_by_identity(source.fingerprint, 1).financial_event_id == trade.id
    assert any(
        item.id == trade.id for item in SqliteFinancialEventRepository(MAIN_PORTFOLIO_ID).list()
    )
    with SessionFactory() as db:
        assert db.query(SecurityAuditRecord).filter_by(evidence_ref=str(trade.id)).count() == 0


def test_delete_preserves_paid_income_fingerprint_and_import_status():
    from income_analytics.infrastructure.database import SessionFactory
    from income_analytics.infrastructure.models import ImportedPaidIncomeRecord
    from income_analytics.infrastructure.sqlite_repositories import SqliteFinancialEventRepository

    trade, _, _ = _applied_trade()
    ref_id = str(uuid4())
    now = datetime.now(UTC)
    with SessionFactory.begin() as db:
        db.add(
            ImportedPaidIncomeRecord(
                id=ref_id,
                portfolio_id=str(MAIN_PORTFOLIO_ID),
                provider="fixture",
                raw_fingerprint=uuid4().hex,
                asset_id=str(trade.asset.id),
                income_type="DIVIDEND",
                amount_per_unit="1",
                financial_event_id=str(trade.id),
                import_status="IMPORTED",
                detail="original evidence",
                created_at=now,
                updated_at=now,
            )
        )
    assert SqliteFinancialEventRepository(MAIN_PORTFOLIO_ID).delete(str(trade.id))
    with SessionFactory() as db:
        retained = db.get(ImportedPaidIncomeRecord, ref_id)
        assert retained.financial_event_id is None
        assert retained.import_status == "IMPORTED"
        assert retained.raw_fingerprint
        assert "original evidence" in retained.detail and str(trade.id) in retained.detail
