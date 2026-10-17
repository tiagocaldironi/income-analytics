"""Immutable snapshot and validation persistence for Magic Formula inputs."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import text

from income_analytics.application.magic_formula_validation import CompanyNormalizationValidation
from income_analytics.infrastructure.database import SessionFactory, initialize_database
from income_analytics.infrastructure.models import (
    CompanyNormalizationValidationRecord,
    MagicFormulaFundamentalsSnapshotRecord,
)


class SqliteMagicFormulaSnapshotRepository:
    def __init__(self, *, session_factory=None, initialize=None):
        self._session_factory = session_factory
        self._initialize = initialize

    def save_if_absent(
        self,
        *,
        issuer_id: str,
        financial_reference_date: date,
        market_reference_date: date,
        statement_type: str,
        statement_scope: str,
        adapter_version: str,
        normalization_status: str,
        validation_status: str,
        metrics: dict[str, object],
        lineage: list[dict[str, object]],
    ) -> str:
        if validation_status != "NOT_VALIDATED":
            raise ValueError("VALIDATION_REQUIRES_SNAPSHOT_BOUND_FORMAL_QA")
        try:
            UUID(issuer_id)
        except ValueError as error:
            raise ValueError("CANONICAL_ISSUER_REQUIRED") from error
        if metrics.get("issuer_id", issuer_id) != issuer_id:
            raise ValueError("SNAPSHOT_ISSUER_MISMATCH")
        # The structured column is the only writable validation decision.
        metrics = {key: value for key, value in metrics.items() if key != "validation_status"}
        (self._initialize or initialize_database)()
        with (self._session_factory or SessionFactory).begin() as session:
            if (
                session.execute(
                    text("SELECT 1 FROM magic_formula_issuers WHERE issuer_id=:issuer_id"),
                    {"issuer_id": issuer_id},
                ).first()
                is None
            ):
                raise ValueError("CANONICAL_ISSUER_REQUIRED")
            existing = (
                session.query(MagicFormulaFundamentalsSnapshotRecord)
                .filter_by(
                    issuer_id=issuer_id,
                    financial_reference_date=financial_reference_date,
                    market_reference_date=market_reference_date,
                    adapter_version=adapter_version,
                )
                .one_or_none()
            )
            if existing:
                return existing.id
            snapshot_id = str(uuid4())
            session.add(
                MagicFormulaFundamentalsSnapshotRecord(
                    id=snapshot_id,
                    issuer_id=issuer_id,
                    financial_reference_date=financial_reference_date,
                    market_reference_date=market_reference_date,
                    statement_type=statement_type,
                    statement_scope=statement_scope,
                    adapter_version=adapter_version,
                    normalization_status=normalization_status,
                    validation_status=validation_status,
                    metrics_json=json.dumps(metrics, default=str),
                    lineage_json=json.dumps(lineage, default=str),
                    created_at=datetime.now(UTC),
                )
            )
            return snapshot_id

    def save_validation(self, validation: CompanyNormalizationValidation) -> str:
        initialize_database()
        validation_id = str(uuid4())
        with SessionFactory.begin() as session:
            session.add(
                CompanyNormalizationValidationRecord(
                    id=validation_id,
                    issuer_id=validation.issuer_id,
                    reference_date=date.fromisoformat(validation.reference_date),
                    adapter_version=validation.adapter_version,
                    metric=validation.metric,
                    expected_value=str(validation.expected_value),
                    actual_value=str(validation.actual_value),
                    difference=str(validation.difference),
                    status=validation.status.value,
                    notes=validation.notes,
                    validated_at=validation.validated_at,
                )
            )
        return validation_id
