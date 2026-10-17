"""Contracts shared by the auditable B3 import pipeline.

These values deliberately describe the imported source rows, independently from
the financial events eventually created from them.  That separation lets a
preview remain reviewable and makes repeated/overlapping reports idempotent.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Iterable, Protocol
from uuid import UUID, uuid4

from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.infrastructure.b3_report_parser import B3ParsedRow, B3RowStatus


class B3ImportReportType(StrEnum):
    NEGOTIATION = "NEGOTIATION"
    MOVEMENT = "MOVEMENT"


class B3ImportBatchStatus(StrEnum):
    PREVIEWED = "PREVIEWED"
    APPLYING = "APPLYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class B3ImportedRecordStatus(StrEnum):
    NEW = "NEW"
    DUPLICATE = "DUPLICATE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID = "INVALID"
    APPLIED = "APPLIED"


@dataclass(frozen=True, slots=True)
class B3ImportBatch:
    id: UUID
    file_name: str
    file_hash: str
    report_type: B3ImportReportType
    total_rows: int
    new_rows: int
    duplicate_rows: int
    review_rows: int
    unsupported_rows: int
    invalid_rows: int
    status: B3ImportBatchStatus
    created_at: datetime
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class B3ImportedRecord:
    id: UUID
    batch_id: UUID
    fingerprint: str
    occurrence_index: int
    source_row: int
    status: B3ImportedRecordStatus
    event_date: date | None
    event_type: str | None
    income_type: str | None
    source_symbol: str | None
    normalized_symbol: str | None
    institution: str | None
    market: str | None
    quantity: Decimal | None
    unit_price: Decimal | None
    total_value: Decimal | None
    raw_payload: str | None
    detail: str | None
    asset_id: UUID | None = None
    financial_event_id: UUID | None = None
    created_at: datetime | None = None
    applied_at: datetime | None = None
    quantity_status: str | None = None
    financial_status: str | None = None


class B3ImportRepository(Protocol):
    def create_batch(self, batch: B3ImportBatch) -> None: ...
    def get_batch(self, batch_id: UUID) -> B3ImportBatch | None: ...
    def list_records(self, batch_id: UUID) -> tuple[B3ImportedRecord, ...]: ...
    def get_record_by_identity(
        self, fingerprint: str, occurrence_index: int
    ) -> B3ImportedRecord | None: ...
    def save_record(self, record: B3ImportedRecord) -> None: ...


class B3ImportService:
    """Build an auditable preview; application is deliberately a separate step."""

    def __init__(
        self,
        repository: B3ImportRepository,
        assets: dict[str, object],
        existing_events: Iterable[object] = (),
    ) -> None:
        self._repository = repository
        self._assets = assets
        self._existing_events = tuple(existing_events)

    def preview(
        self,
        *,
        workbook: bytes,
        file_name: str,
        report_type: B3ImportReportType,
        rows: Iterable[B3ParsedRow],
        persist: bool = True,
    ) -> tuple[B3ImportBatch, tuple[B3ImportedRecord, ...]]:
        now = datetime.now().astimezone()
        parsed = tuple(rows)
        provisional: list[B3ImportedRecord] = []
        occurrences: dict[str, int] = {}
        for row in parsed:
            fingerprint = self._fingerprint(row)
            occurrence = occurrences.get(fingerprint, 0) + 1
            occurrences[fingerprint] = occurrence
            status, detail, asset_id = self._resolve(row, fingerprint, occurrence)
            provisional.append(
                B3ImportedRecord(
                    id=uuid4(),
                    batch_id=UUID(int=0),
                    fingerprint=fingerprint,
                    occurrence_index=occurrence,
                    source_row=row.source_row,
                    status=status,
                    event_date=row.event_date,
                    event_type=row.event_type,
                    income_type=row.income_type,
                    source_symbol=row.source_symbol,
                    normalized_symbol=row.normalized_symbol,
                    institution=row.institution,
                    market=row.market,
                    quantity=row.quantity,
                    unit_price=row.unit_price,
                    total_value=row.total_value,
                    raw_payload=self._income_payload(row),
                    detail=detail,
                    asset_id=asset_id,
                    created_at=now,
                    quantity_status=(
                        "OBSERVED" if row.financial_status == "DATA_GAP" else row.quantity_status
                    ),
                    financial_status=row.financial_status,
                )
            )
        counts = self._counts(provisional)
        batch = B3ImportBatch(
            id=uuid4(),
            file_name=file_name,
            file_hash=hashlib.sha256(workbook).hexdigest(),
            report_type=report_type,
            status=B3ImportBatchStatus.PREVIEWED,
            created_at=now,
            total_rows=len(provisional),
            **counts,
        )
        records = tuple(
            replace(
                record,
                # A previously unresolved source row is explicitly allowed to
                # be re-reviewed after the asset registry has been enriched.
                id=(
                    previous.id
                    if previous and previous.status is not B3ImportedRecordStatus.APPLIED
                    else record.id
                ),
                batch_id=batch.id,
            )
            for record in provisional
            for previous in [
                self._repository.get_record_by_identity(record.fingerprint, record.occurrence_index)
            ]
        )
        if persist:
            self._repository.create_batch(batch)
        for record in records:
            # The source identity is globally unique.  A duplicate remains in
            # the returned/persisted batch counters, while its canonical audit
            # record stays attached to the first batch instead of violating
            # that identity constraint.
            if persist and record.status is not B3ImportedRecordStatus.DUPLICATE:
                self._repository.save_record(record)
        return batch, records

    def _resolve(
        self,
        row: B3ParsedRow,
        fingerprint: str,
        occurrence: int,
    ) -> tuple[B3ImportedRecordStatus, str | None, UUID | None]:
        previous = self._repository.get_record_by_identity(fingerprint, occurrence)
        if previous is not None and previous.status is B3ImportedRecordStatus.APPLIED:
            return B3ImportedRecordStatus.DUPLICATE, "DUPLICATE_SOURCE_RECORD", None
        if row.financial_status == "DATA_GAP":
            return (
                B3ImportedRecordStatus.REVIEW_REQUIRED,
                "SETTLEMENT_FINANCIAL_DATA_GAP",
                None,
            )
        mapped = {
            B3RowStatus.NEW: B3ImportedRecordStatus.NEW,
            B3RowStatus.REVIEW_REQUIRED: B3ImportedRecordStatus.REVIEW_REQUIRED,
            B3RowStatus.UNSUPPORTED: B3ImportedRecordStatus.UNSUPPORTED,
            B3RowStatus.INVALID: B3ImportedRecordStatus.INVALID,
        }[row.status]
        if mapped is not B3ImportedRecordStatus.NEW:
            return mapped, row.detail, None
        asset = self._assets.get(row.normalized_symbol or "")
        if asset is None:
            return B3ImportedRecordStatus.REVIEW_REQUIRED, "ASSET_RESOLUTION_REQUIRED", None
        if (
            row.income_type == "INCOME"
            and getattr(asset, "asset_class", None) is not AssetClass.FII
        ):
            return B3ImportedRecordStatus.REVIEW_REQUIRED, "INCOME_TYPE_REQUIRES_FII", None
        if row.source_date_type == "SETTLEMENT_DATE" and self._matches_existing_trade(row):
            return B3ImportedRecordStatus.DUPLICATE, "EXISTING_TRADE_FROM_OTHER_B3_REPORT", None
        return B3ImportedRecordStatus.NEW, None, getattr(asset, "id")

    def _matches_existing_trade(self, row: B3ParsedRow) -> bool:
        for event in self._existing_events:
            asset = getattr(event, "asset", None)
            quantity = getattr(event, "quantity", None)
            unit_price = getattr(event, "unit_price", None)
            if (
                getattr(event, "effective_date", None) == row.event_date
                and getattr(getattr(event, "event_type", None), "value", None) == row.event_type
                and str(getattr(asset, "ticker", "")) == row.normalized_symbol
                and getattr(quantity, "value", None) == row.quantity
                and getattr(unit_price, "amount", None) == row.unit_price
                and str(
                    getattr(getattr(event, "metadata", {}), "get", lambda *_: None)("source") or ""
                ).startswith("B3")
            ):
                return True
        return False

    @staticmethod
    def _fingerprint(row: B3ParsedRow) -> str:
        values = (
            "B3",
            row.report_type,
            row.event_date,
            row.event_type,
            row.income_type,
            row.original_movement,
            row.direction,
            row.normalized_symbol,
            B3ImportService._normalize_institution(row.institution),
            row.market,
            row.quantity,
            row.unit_price,
            row.total_value,
        )
        return hashlib.sha256(
            "|".join("" if value is None else str(value) for value in values).encode()
        ).hexdigest()

    @staticmethod
    def _normalize_institution(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = unicodedata.normalize("NFD", value.upper())
        return "".join(character for character in normalized if character.isalnum()) or None

    @staticmethod
    def _income_payload(row: B3ParsedRow) -> str:
        return json.dumps(
            {
                "source": "B3_MOVEMENT_STATEMENT"
                if row.report_type == "MOVEMENT"
                else "B3_NEGOTIATION_REPORT",
                "source_date": row.event_date.isoformat() if row.event_date else None,
                "source_date_type": row.source_date_type,
                "original_movement": row.original_movement,
                "direction": row.direction,
                "quantity_status": row.quantity_status,
                "financial_status": row.financial_status,
                "gross_amount": str(row.gross_amount) if row.gross_amount is not None else None,
                "withheld_tax": str(row.withheld_tax) if row.withheld_tax is not None else None,
            }
        )

    @staticmethod
    def _counts(records: Iterable[B3ImportedRecord]) -> dict[str, int]:
        records = tuple(records)
        return {
            "new_rows": sum(row.status is B3ImportedRecordStatus.NEW for row in records),
            "duplicate_rows": sum(
                row.status is B3ImportedRecordStatus.DUPLICATE for row in records
            ),
            "review_rows": sum(
                row.status is B3ImportedRecordStatus.REVIEW_REQUIRED for row in records
            ),
            "unsupported_rows": sum(
                row.status is B3ImportedRecordStatus.UNSUPPORTED for row in records
            ),
            "invalid_rows": sum(row.status is B3ImportedRecordStatus.INVALID for row in records),
        }
