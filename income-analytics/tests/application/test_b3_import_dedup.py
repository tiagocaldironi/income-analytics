from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import uuid4

from income_analytics.application.b3_import import (
    B3ImportBatch,
    B3ImportedRecord,
    B3ImportedRecordStatus,
    B3ImportReportType,
    B3ImportService,
)
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.infrastructure.b3_report_parser import B3ParsedRow, B3RowStatus


class _Asset:
    def __init__(self) -> None:
        self.id = uuid4()
        self.asset_class = AssetClass.BRAZILIAN_STOCK


class _Repository:
    def __init__(self) -> None:
        self.records: dict[tuple[str, int], B3ImportedRecord] = {}

    def create_batch(self, _: B3ImportBatch) -> None:
        pass

    def get_batch(self, _: object) -> None:
        return None

    def list_records(self, _: object) -> tuple[B3ImportedRecord, ...]:
        return ()

    def get_record_by_identity(self, fingerprint: str, occurrence: int) -> B3ImportedRecord | None:
        return self.records.get((fingerprint, occurrence))

    def save_record(self, record: B3ImportedRecord) -> None:
        self.records[(record.fingerprint, record.occurrence_index)] = record


def _row(
    *,
    direction: str = "CREDITO",
    movement: str = "Transferência - Liquidação",
    institution: str = "XP CCTVM S/A",
) -> B3ParsedRow:
    return B3ParsedRow(
        "MOVEMENT",
        2,
        B3RowStatus.NEW,
        "ITSA4",
        "ITSA4",
        date(2026, 6, 1),
        "BUY",
        None,
        institution,
        None,
        Decimal("2"),
        Decimal("10"),
        Decimal("20"),
        original_movement=movement,
        direction=direction,
        source_date_type="SETTLEMENT_DATE",
    )


def test_stable_identity_ignores_line_position_and_normalizes_institution() -> None:
    first = _row(institution="XP Investimentos CCTVM S/A.")
    moved = _row(institution="XP Investimentos CCTVM S/A")
    assert B3ImportService._fingerprint(first) == B3ImportService._fingerprint(moved)


def test_line_position_changed_keeps_canonical_identity() -> None:
    first = _row()
    moved = B3ParsedRow(
        report_type=first.report_type,
        source_row=99,
        status=first.status,
        source_symbol=first.source_symbol,
        normalized_symbol=first.normalized_symbol,
        event_date=first.event_date,
        event_type=first.event_type,
        institution=first.institution,
        quantity=first.quantity,
        unit_price=first.unit_price,
        total_value=first.total_value,
        original_movement=first.original_movement,
        direction=first.direction,
        source_date_type=first.source_date_type,
    )
    assert B3ImportService._fingerprint(first) == B3ImportService._fingerprint(moved)


def test_direction_and_movement_do_not_collide() -> None:
    assert B3ImportService._fingerprint(_row()) != B3ImportService._fingerprint(
        _row(direction="DEBITO")
    )
    assert B3ImportService._fingerprint(_row()) != B3ImportService._fingerprint(
        _row(movement="Dividendo")
    )


def test_identical_group_uses_deterministic_multiplicity_and_reimport_is_duplicate() -> None:
    repository = _Repository()
    service = B3ImportService(repository, {"ITSA4": _Asset()})
    _, first = service.preview(
        workbook=b"a",
        file_name="a.xlsx",
        report_type=B3ImportReportType.MOVEMENT,
        rows=(_row(), _row()),
    )
    assert [item.occurrence_index for item in first] == [1, 2]
    for item in first:
        repository.save_record(replace(item, status=B3ImportedRecordStatus.APPLIED))
    _, second = service.preview(
        workbook=b"b",
        file_name="overlap.xlsx",
        report_type=B3ImportReportType.MOVEMENT,
        rows=(_row(), _row()),
    )
    assert [item.status for item in second] == [
        B3ImportedRecordStatus.DUPLICATE,
        B3ImportedRecordStatus.DUPLICATE,
    ]


def test_null_financial_settlement_is_idempotent_and_preserves_multiplicity() -> None:
    repository = _Repository()
    service = B3ImportService(repository, {"ITSA4": _Asset()})
    row = B3ParsedRow(
        "MOVEMENT",
        2,
        B3RowStatus.NEW,
        "ITSA4",
        "ITSA4",
        date(2026, 6, 1),
        "SELL",
        None,
        "XP",
        None,
        Decimal("31"),
        None,
        None,
        original_movement="Transferência - Liquidação",
        direction="DEBITO",
        source_date_type="SETTLEMENT_DATE",
        quantity_status="COMPLETE",
        financial_status="DATA_GAP",
    )
    _, first = service.preview(
        workbook=b"a",
        file_name="a.xlsx",
        report_type=B3ImportReportType.MOVEMENT,
        rows=(row, row),
    )
    assert [item.occurrence_index for item in first] == [1, 2]
    assert all(item.financial_status == "DATA_GAP" for item in first)
    for item in first:
        repository.save_record(replace(item, status=B3ImportedRecordStatus.APPLIED))
    _, second = service.preview(
        workbook=b"b",
        file_name="b.xlsx",
        report_type=B3ImportReportType.MOVEMENT,
        rows=(row, row),
    )
    assert [item.status for item in second] == [B3ImportedRecordStatus.DUPLICATE] * 2
