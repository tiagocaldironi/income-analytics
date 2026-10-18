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
