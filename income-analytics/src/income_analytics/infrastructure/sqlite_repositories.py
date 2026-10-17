"""SQLite adapters; mapping between persistence records and domain entities."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from income_analytics.application.b3_import import (
    B3ImportBatch,
    B3ImportBatchStatus,
    B3ImportedRecord,
    B3ImportedRecordStatus,
    B3ImportReportType,
)
from income_analytics.application.benchmark_data import BenchmarkNature, BenchmarkObservation
from income_analytics.application.fx_data import FxRateObservation
from income_analytics.application.provider_health import ProviderHealth
from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.asset_allocation_policy import AssetAllocationPolicy
from income_analytics.domain.benchmark_rate import BenchmarkRate
from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.entities.currency import Currency
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.entities.institution import Institution
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)
from income_analytics.domain.enums.valuation_method import ValuationMethod
from income_analytics.domain.fixed_income_details import FixedIncomeDetails
from income_analytics.domain.market_price import MarketPrice
from income_analytics.domain.pension_market_data import PensionFundQuota, PensionInvestmentVehicle
from income_analytics.domain.recurring_rule import RecurrenceFrequency, RecurringRule
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from income_analytics.domain.value_objects.ticker import Ticker
from income_analytics.domain.wealth_details import PensionPlanDetails, RealEstateDetails
from income_analytics.infrastructure.database import SessionFactory, initialize_database
from income_analytics.infrastructure.models import (
    AllocationTargetRecord,
    AssetRecord,
    AssetTargetRecord,
    B3ImportBatchRecord,
    BenchmarkObservationRecord,
    BenchmarkRateRecord,
    FinancialEventRecord,
    FixedIncomeDetailsRecord,
    FxRateRecord,
    ImportedPaidIncomeRecord,
    MarketPriceRecord,
    MarketPriceRefreshRunRecord,
    PaidIncomeProviderSettingsRecord,
    PensionFundQuotaRecord,
    PensionInvestmentVehicleRecord,
    PensionPlanDetailsRecord,
    PortfolioConfigurationRecord,
    PortfolioDashboardSnapshotRecord,
    ProviderHealthRecord,
    RealEstateDetailsRecord,
    RecurringRuleRecord,
)
from income_analytics.infrastructure.models import (
    B3ImportedRecord as B3ImportedRecordRow,
)


class SqliteB3ImportRepository:
    """Audit store for B3 source rows and their cross-file identities.

    A row identity is globally unique, rather than unique per batch, so an
    overlapping export naturally resolves to the original imported row.  The
    ``apply_batch`` callback exposes the same SQLAlchemy transaction used to
    persist audit metadata, allowing the import use case to save a financial
    event and its B3 record atomically.
    """

    def create_batch(self, batch: B3ImportBatch) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.add(self._batch_record(batch))

    def get_batch(self, batch_id: UUID) -> B3ImportBatch | None:
        initialize_database()
        with SessionFactory() as session:
            record = session.get(B3ImportBatchRecord, str(batch_id))
            return self._to_batch(record) if record else None

    def list_batches(
        self, *, offset: int = 0, limit: int = 20
    ) -> tuple[tuple[B3ImportBatch, ...], int]:
        initialize_database()
        with SessionFactory() as session:
            query = session.query(B3ImportBatchRecord)
            total = query.count()
            records = (
                query.order_by(B3ImportBatchRecord.created_at.desc(), B3ImportBatchRecord.id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return tuple(self._to_batch(record) for record in records), total

    def list_records(self, batch_id: UUID) -> tuple[B3ImportedRecord, ...]:
        initialize_database()
        with SessionFactory() as session:
            records = (
                session.query(B3ImportedRecordRow)
                .filter_by(batch_id=str(batch_id))
                .order_by(B3ImportedRecordRow.source_row, B3ImportedRecordRow.id)
                .all()
            )
            return tuple(self._to_imported_record(record) for record in records)

    def get_record_by_identity(
        self, fingerprint: str, occurrence_index: int
    ) -> B3ImportedRecord | None:
        initialize_database()
        with SessionFactory() as session:
            record = (
                session.query(B3ImportedRecordRow)
                .filter_by(source="B3", fingerprint=fingerprint, occurrence_index=occurrence_index)
                .one_or_none()
            )
            return self._to_imported_record(record) if record else None

    def save_record(self, record: B3ImportedRecord) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(self._imported_record(record))

    def apply_batch(
        self,
        batch_id: UUID,
        operation: Callable[[Session, "SqliteB3ImportRepository"], None],
    ) -> B3ImportBatch:
        """Run ``operation`` and mark its batch completed in one transaction.

        The operation receives the open SQLAlchemy session.  It may call
        :meth:`save_record_in_session` after adding the corresponding
        ``FinancialEventRecord`` to that same session.  Any exception rolls
        both writes back, avoiding orphan B3 metadata or financial events.
        """
        initialize_database()
        now = datetime.now(UTC)
        with SessionFactory.begin() as session:
            batch = session.get(B3ImportBatchRecord, str(batch_id))
            if batch is None:
                raise ValueError(f"B3 import batch not found: {batch_id}")
            if batch.status == B3ImportBatchStatus.COMPLETED.value:
                return self._to_batch(batch)
            batch.status = B3ImportBatchStatus.APPLYING.value
            operation(session, self)
            batch.status = B3ImportBatchStatus.COMPLETED.value
            batch.completed_at = now
            session.flush()
            result = self._to_batch(batch)
        return result

    def save_record_in_session(self, session: Session, record: B3ImportedRecord) -> None:
        """Persist a source row inside an import application's transaction."""
        # SQLAlchemy's Session protocol is intentionally not exposed to the
        # domain.  This adapter method is only for the infrastructure use case.
        session.merge(self._imported_record(record))

    @staticmethod
    def _batch_record(batch: B3ImportBatch) -> B3ImportBatchRecord:
        return B3ImportBatchRecord(
            id=str(batch.id),
            source="B3",
            file_name=batch.file_name,
            file_hash=batch.file_hash,
            report_type=batch.report_type.value,
            total_rows=batch.total_rows,
            new_rows=batch.new_rows,
            duplicate_rows=batch.duplicate_rows,
            review_rows=batch.review_rows,
            unsupported_rows=batch.unsupported_rows,
            invalid_rows=batch.invalid_rows,
            status=batch.status.value,
            created_at=batch.created_at,
            completed_at=batch.completed_at,
        )

    @staticmethod
    def _imported_record(record: B3ImportedRecord) -> B3ImportedRecordRow:
        return B3ImportedRecordRow(
            id=str(record.id),
            batch_id=str(record.batch_id),
            source="B3",
            fingerprint=record.fingerprint,
            occurrence_index=record.occurrence_index,
            source_row=record.source_row,
            status=record.status.value,
            event_date=record.event_date,
            event_type=record.event_type,
            income_type=record.income_type,
            source_symbol=record.source_symbol,
            normalized_symbol=record.normalized_symbol,
            institution=record.institution,
            market=record.market,
            quantity=str(record.quantity) if record.quantity is not None else None,
            unit_price=str(record.unit_price) if record.unit_price is not None else None,
            total_value=str(record.total_value) if record.total_value is not None else None,
            raw_payload=record.raw_payload,
            detail=record.detail,
            asset_id=str(record.asset_id) if record.asset_id else None,
            financial_event_id=str(record.financial_event_id)
            if record.financial_event_id
            else None,
            created_at=record.created_at or datetime.now(UTC),
            applied_at=record.applied_at,
        )

    @staticmethod
    def _to_batch(record: B3ImportBatchRecord) -> B3ImportBatch:
        return B3ImportBatch(
            id=UUID(record.id),
            file_name=record.file_name,
            file_hash=record.file_hash,
            report_type=B3ImportReportType(record.report_type),
            total_rows=record.total_rows,
            new_rows=record.new_rows,
            duplicate_rows=record.duplicate_rows,
            review_rows=record.review_rows,
            unsupported_rows=record.unsupported_rows,
            invalid_rows=record.invalid_rows,
            status=B3ImportBatchStatus(record.status),
            created_at=record.created_at,
            completed_at=record.completed_at,
        )

    @staticmethod
    def _to_imported_record(record: B3ImportedRecordRow) -> B3ImportedRecord:
        return B3ImportedRecord(
            id=UUID(record.id),
            batch_id=UUID(record.batch_id),
            fingerprint=record.fingerprint,
            occurrence_index=record.occurrence_index,
            source_row=record.source_row,
            status=B3ImportedRecordStatus(record.status),
            event_date=record.event_date,
            event_type=record.event_type,
            income_type=record.income_type,
            source_symbol=record.source_symbol,
            normalized_symbol=record.normalized_symbol,
            institution=record.institution,
            market=record.market,
            quantity=Decimal(record.quantity) if record.quantity is not None else None,
            unit_price=Decimal(record.unit_price) if record.unit_price is not None else None,
            total_value=Decimal(record.total_value) if record.total_value is not None else None,
            raw_payload=record.raw_payload,
            detail=record.detail,
            asset_id=UUID(record.asset_id) if record.asset_id else None,
            financial_event_id=UUID(record.financial_event_id)
            if record.financial_event_id
            else None,
            created_at=record.created_at,
            applied_at=record.applied_at,
        )


class SqlitePortfolioDashboardSnapshotRepository:
    """Persistent JSON read model; source transactions stay in their own tables."""

    def get(self) -> dict[str, object] | None:
        initialize_database()
        with SessionFactory() as session:
            record = session.get(PortfolioDashboardSnapshotRecord, 1)
        if record is None:
            return None
        payload = json.loads(record.payload)
        payload.update(
            {
                "status": record.status,
                "version": record.version,
                "calculated_at": record.calculated_at.isoformat(),
            }
        )
        return payload

    def save(self, payload: dict[str, object]) -> dict[str, object]:
        """Replace the complete view in one database transaction."""
        initialize_database()
        now = datetime.now(UTC)
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
        with SessionFactory.begin() as session:
            current = session.get(PortfolioDashboardSnapshotRecord, 1)
            version = (current.version if current else 0) + 1
            session.merge(
                PortfolioDashboardSnapshotRecord(
                    id=1,
                    status="VALID",
                    version=version,
                    calculated_at=now,
                    payload=encoded,
                )
            )
        return {
            **payload,
            "status": "VALID",
            "version": version,
            "calculated_at": now.isoformat(),
        }


class SqliteAssetRepository:
    def save(self, asset: Asset) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                AssetRecord(
                    id=str(asset.id),
                    ticker=str(asset.ticker),
                    name=asset.name,
                    asset_class=asset.asset_class.value,
                    asset_type=asset.asset_type.value,
                    valuation_method=asset.valuation_method.value,
                    currency_code=asset.currency.code,
                    country=asset.country,
                    sector=asset.sector,
                    created_at=asset.created_at,
                )
            )

    def get_by_ticker(self, ticker: str) -> Asset | None:
        with SessionFactory() as session:
            record = (
                session.query(AssetRecord).filter_by(ticker=ticker.strip().upper()).one_or_none()
            )
            return self._to_domain(record) if record else None

    def list(self) -> tuple[Asset, ...]:
        with SessionFactory() as session:
            return tuple(self._to_domain(record) for record in session.query(AssetRecord).all())

    @staticmethod
    def _to_domain(record: AssetRecord) -> Asset:
        created_at = SqliteAssetRepository._utc(record.created_at)
        return Asset(
            id=UUID(record.id),
            ticker=Ticker(record.ticker),
            name=record.name,
            asset_type=AssetType(record.asset_type),
            valuation_method=ValuationMethod(
                getattr(record, "valuation_method", None) or "MARKET_PRICE"
            ),
            asset_class=AssetClass(record.asset_class),
            currency=Currency(
                code=record.currency_code,
                name=record.currency_code,
                symbol=record.currency_code,
                decimal_places=2,
            ),
            institution=Institution(name="Cadastro local"),
            country=record.country,
            sector=record.sector,
            created_at=created_at,
            updated_at=created_at,
        )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class SqliteFixedIncomeDetailsRepository:
    """Persistence adapter for the fixed-income aggregate extension."""

    def save(self, details: FixedIncomeDetails) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                FixedIncomeDetailsRecord(
                    asset_id=str(details.asset_id),
                    instrument_type=details.instrument_type.value,
                    issuer=details.issuer,
                    indexer_type=details.indexer_type.value,
                    contracted_rate=str(details.contracted_rate)
                    if details.contracted_rate is not None
                    else None,
                    percentage_of_indexer=str(details.percentage_of_indexer)
                    if details.percentage_of_indexer is not None
                    else None,
                    spread=str(details.spread) if details.spread is not None else None,
                    application_date=details.application_date,
                    maturity_date=details.maturity_date,
                    principal_amount=str(details.principal_amount),
                    liquidity_type=details.liquidity_type,
                    tax_exempt=details.tax_exempt,
                    created_at=details.created_at,
                )
            )

    def list(self) -> tuple[FixedIncomeDetails, ...]:
        initialize_database()
        with SessionFactory() as session:
            rows = session.query(FixedIncomeDetailsRecord).all()
        return tuple(
            FixedIncomeDetails(
                asset_id=UUID(row.asset_id),
                instrument_type=FixedIncomeInstrumentType(row.instrument_type),
                issuer=row.issuer,
                indexer_type=FixedIncomeIndexerType(row.indexer_type),
                contracted_rate=Decimal(row.contracted_rate) if row.contracted_rate else None,
                percentage_of_indexer=Decimal(row.percentage_of_indexer)
                if row.percentage_of_indexer
                else None,
                spread=Decimal(row.spread) if row.spread else None,
                application_date=row.application_date,
                maturity_date=row.maturity_date,
                principal_amount=Decimal(row.principal_amount),
                liquidity_type=row.liquidity_type,
                tax_exempt=row.tax_exempt,
                created_at=SqliteAssetRepository._utc(row.created_at),
            )
            for row in rows
        )


class SqliteRecurringRuleRepository:
    def save(self, rule: RecurringRule) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                RecurringRuleRecord(
                    id=str(rule.id),
                    event_type=rule.event_type.value,
                    amount=str(rule.amount),
                    asset_id=str(rule.asset_id) if rule.asset_id else None,
                    frequency=rule.frequency.value,
                    next_execution_date=rule.next_execution_date,
                    end_execution_date=rule.end_execution_date,
                    active=rule.active,
                )
            )

    def list(self) -> tuple[RecurringRule, ...]:
        initialize_database()
        with SessionFactory() as session:
            rows = session.query(RecurringRuleRecord).all()
        return tuple(
            RecurringRule(
                id=UUID(row.id),
                event_type=FinancialEventType(row.event_type),
                amount=Decimal(row.amount),
                asset_id=UUID(row.asset_id) if row.asset_id else None,
                frequency=RecurrenceFrequency(row.frequency),
                next_execution_date=row.next_execution_date,
                end_execution_date=row.end_execution_date,
                active=row.active,
            )
            for row in rows
        )

    def delete(self, rule_id: UUID) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.query(RecurringRuleRecord).filter_by(id=str(rule_id)).delete()


class SqlitePensionPlanDetailsRepository:
    def save(self, details: PensionPlanDetails) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                PensionPlanDetailsRecord(
                    asset_id=str(details.asset_id),
                    pension_type=details.pension_type,
                    institution=details.institution,
                    institution_cnpj=details.institution_cnpj,
                    plan_name=details.plan_name,
                    tax_regime=details.tax_regime,
                    start_date=details.start_date,
                    reported_balance=str(details.reported_balance),
                    reported_balance_date=details.reported_balance_date,
                    ownership_origin=details.ownership_origin,
                    pension_system_type=details.pension_system_type,
                    product_type=details.product_type,
                    closed_plan_modality=details.closed_plan_modality,
                    sponsor_name=details.sponsor_name,
                    sponsor_cnpj=details.sponsor_cnpj,
                    susep_process_number=details.susep_process_number,
                    cnpb=details.cnpb,
                    participant_balance=str(details.participant_balance)
                    if details.participant_balance is not None
                    else None,
                    sponsor_balance=str(details.sponsor_balance)
                    if details.sponsor_balance is not None
                    else None,
                    employer_match_enabled=details.employer_match_enabled,
                    employer_match_rate=str(details.employer_match_rate)
                    if details.employer_match_rate is not None
                    else None,
                    match_limit=str(details.match_limit)
                    if details.match_limit is not None
                    else None,
                    match_rule_notes=details.match_rule_notes,
                    vesting_enabled=details.vesting_enabled,
                    current_vested_percentage=str(details.current_vested_percentage)
                    if details.current_vested_percentage is not None
                    else None,
                    vesting_rule_notes=details.vesting_rule_notes,
                    status=details.status,
                )
            )

    def list(self) -> tuple[PensionPlanDetails, ...]:
        initialize_database()
        with SessionFactory() as session:
            rows = session.query(PensionPlanDetailsRecord).all()
        return tuple(
            PensionPlanDetails(
                asset_id=UUID(row.asset_id),
                pension_type=row.pension_type,
                institution=row.institution,
                institution_cnpj=getattr(row, "institution_cnpj", None),
                plan_name=row.plan_name,
                tax_regime=row.tax_regime,
                start_date=row.start_date,
                reported_balance=Decimal(row.reported_balance),
                reported_balance_date=row.reported_balance_date,
                ownership_origin=getattr(row, "ownership_origin", None) or "PARTICULAR",
                pension_system_type=getattr(row, "pension_system_type", None) or "OPEN",
                product_type=getattr(row, "product_type", None),
                closed_plan_modality=getattr(row, "closed_plan_modality", None),
                sponsor_name=getattr(row, "sponsor_name", None),
                sponsor_cnpj=getattr(row, "sponsor_cnpj", None),
                susep_process_number=getattr(row, "susep_process_number", None),
                cnpb=getattr(row, "cnpb", None),
                participant_balance=Decimal(row.participant_balance)
                if getattr(row, "participant_balance", None) is not None
                else None,
                sponsor_balance=Decimal(row.sponsor_balance)
                if getattr(row, "sponsor_balance", None) is not None
                else None,
                employer_match_enabled=getattr(row, "employer_match_enabled", None),
                employer_match_rate=Decimal(row.employer_match_rate)
                if getattr(row, "employer_match_rate", None) is not None
                else None,
                match_limit=Decimal(row.match_limit)
                if getattr(row, "match_limit", None) is not None
                else None,
                match_rule_notes=getattr(row, "match_rule_notes", None),
                vesting_enabled=getattr(row, "vesting_enabled", None),
                current_vested_percentage=Decimal(row.current_vested_percentage)
                if getattr(row, "current_vested_percentage", None) is not None
                else None,
                vesting_rule_notes=getattr(row, "vesting_rule_notes", None),
                status=getattr(row, "status", None) or "ACTIVE",
            )
            for row in rows
        )


class SqlitePensionInvestmentVehicleRepository:
    def save(self, vehicle: PensionInvestmentVehicle) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                PensionInvestmentVehicleRecord(
                    id=str(vehicle.id),
                    pension_asset_id=str(vehicle.pension_asset_id),
                    vehicle_name=vehicle.vehicle_name,
                    vehicle_cnpj=vehicle.vehicle_cnpj,
                    vehicle_type=vehicle.vehicle_type,
                    source=vehicle.source,
                    valid_from=vehicle.valid_from,
                    valid_to=vehicle.valid_to,
                )
            )

    def list_for(self, asset_id: UUID) -> tuple[PensionInvestmentVehicle, ...]:
        initialize_database()
        with SessionFactory() as session:
            rows = (
                session.query(PensionInvestmentVehicleRecord)
                .filter_by(pension_asset_id=str(asset_id))
                .all()
            )
        return tuple(
            PensionInvestmentVehicle(
                id=UUID(row.id),
                pension_asset_id=UUID(row.pension_asset_id),
                vehicle_name=row.vehicle_name,
                vehicle_cnpj=row.vehicle_cnpj,
                vehicle_type=row.vehicle_type,
                source=row.source,
                valid_from=row.valid_from,
                valid_to=row.valid_to,
            )
            for row in rows
        )


class SqlitePensionFundQuotaRepository:
    def save_all(self, quotas: tuple[PensionFundQuota, ...]) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            for quota in quotas:
                session.merge(
                    PensionFundQuotaRecord(
                        vehicle_id=str(quota.vehicle_id),
                        reference_date=quota.reference_date,
                        quota=str(quota.quota),
                        source=quota.source,
                        retrieved_at=quota.retrieved_at,
                    )
                )

    def list_for(self, vehicle_id: UUID) -> tuple[PensionFundQuota, ...]:
        initialize_database()
        with SessionFactory() as session:
            rows = (
                session.query(PensionFundQuotaRecord)
                .filter_by(vehicle_id=str(vehicle_id))
                .order_by(PensionFundQuotaRecord.reference_date)
                .all()
            )
        return tuple(
            PensionFundQuota(
                vehicle_id=UUID(row.vehicle_id),
                reference_date=row.reference_date,
                quota=Decimal(row.quota),
                source=row.source,
                retrieved_at=SqliteAssetRepository._utc(row.retrieved_at),
            )
            for row in rows
        )


class SqliteRealEstateDetailsRepository:
    def save(self, details: RealEstateDetails) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                RealEstateDetailsRecord(
                    asset_id=str(details.asset_id),
                    property_type=details.property_type,
                    country=details.country,
                    description=details.description,
                    cep=details.cep,
                    city=details.city,
                    state=details.state,
                    neighborhood=details.neighborhood,
                    usable_area_m2=str(details.usable_area_m2)
                    if details.usable_area_m2 is not None
                    else None,
                    bedrooms=details.bedrooms,
                    parking_spaces=details.parking_spaces,
                    acquisition_date=details.acquisition_date,
                    acquisition_value=str(details.acquisition_value)
                    if details.acquisition_value is not None
                    else None,
                    ownership_percentage=str(details.ownership_percentage),
                    current_manual_value=str(details.current_manual_value),
                    valuation_date=details.valuation_date,
                )
            )

    def list(self) -> tuple[RealEstateDetails, ...]:
        initialize_database()
        with SessionFactory() as session:
            rows = session.query(RealEstateDetailsRecord).all()
        return tuple(
            RealEstateDetails(
                asset_id=UUID(row.asset_id),
                property_type=row.property_type,
                country=getattr(row, "country", None) or "BR",
                description=row.description,
                cep=row.cep,
                city=row.city,
                state=row.state,
                neighborhood=row.neighborhood,
                usable_area_m2=Decimal(row.usable_area_m2) if row.usable_area_m2 else None,
                bedrooms=row.bedrooms,
                parking_spaces=row.parking_spaces,
                acquisition_date=row.acquisition_date,
                acquisition_value=Decimal(row.acquisition_value) if row.acquisition_value else None,
                ownership_percentage=Decimal(getattr(row, "ownership_percentage", None) or "100"),
                current_manual_value=Decimal(row.current_manual_value),
                valuation_date=row.valuation_date,
            )
            for row in rows
        )


class SqliteFinancialEventRepository:
    def save(self, event: FinancialEvent) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                FinancialEventRecord(
                    id=str(event.id),
                    account_id=str(event.account_id),
                    event_type=event.event_type.value,
                    asset_id=str(event.asset.id) if event.asset else None,
                    quantity=str(event.quantity.value) if event.quantity else None,
                    unit_price=str(event.unit_price.amount) if event.unit_price else None,
                    amount=str(event.amount.amount) if event.amount else None,
                    effective_date=event.effective_date,
                    occurred_at=event.occurred_at,
                    registered_at=event.registered_at,
                    description=event.description,
                    metadata_json=json.dumps(dict(event.metadata)),
                )
            )

    def delete(self, event_id: str) -> bool:
        initialize_database()
        with SessionFactory.begin() as session:
            return session.query(FinancialEventRecord).filter_by(id=event_id).delete() == 1

    def list(self) -> tuple[FinancialEvent, ...]:
        assets = {str(asset.id): asset for asset in SqliteAssetRepository().list()}
        with SessionFactory() as session:
            rows = (
                session.query(FinancialEventRecord)
                .order_by(
                    FinancialEventRecord.effective_date,
                    FinancialEventRecord.registered_at,
                    FinancialEventRecord.id,
                )
                .all()
            )
        # SQLite databases created before foreign-key enforcement may contain
        # references to assets that were later removed.  Such records cannot be
        # reconstructed as domain events, so they must not prevent the whole
        # portfolio from loading.
        rows = [row for row in rows if row.asset_id is None or row.asset_id in assets]
        return tuple(
            FinancialEvent(
                id=UUID(row.id),
                account_id=UUID(row.account_id),
                event_type=FinancialEventType(row.event_type),
                asset=assets.get(row.asset_id) if row.asset_id else None,
                quantity=Quantity(Decimal(row.quantity)) if row.quantity else None,
                unit_price=Money(Decimal(row.unit_price)) if row.unit_price else None,
                amount=Money(Decimal(row.amount)) if row.amount else None,
                effective_date=row.effective_date,
                occurred_at=SqliteAssetRepository._utc(row.occurred_at),
                registered_at=SqliteAssetRepository._utc(row.registered_at),
                description=row.description,
                metadata=json.loads(row.metadata_json) if row.metadata_json else {},
            )
            for row in rows
        )


class SqliteMarketPriceRepository:
    def save_many(self, prices: tuple[MarketPrice, ...]) -> None:
        """Persist a historical quote batch in one transaction."""
        if not prices:
            return
        initialize_database()
        from sqlalchemy import insert

        with SessionFactory.begin() as session:
            session.execute(
                insert(MarketPriceRecord),
                [
                    {
                        "id": str(price.id),
                        "asset_id": str(price.asset.id),
                        "price": str(price.price.amount),
                        "effective_date": price.effective_date,
                        "registered_at": price.registered_at,
                        "provider": price.provider,
                        "price_timestamp": price.price_timestamp,
                    }
                    for price in prices
                ],
            )

    def save(self, price: MarketPrice) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                MarketPriceRecord(
                    id=str(price.id),
                    asset_id=str(price.asset.id),
                    price=str(price.price.amount),
                    effective_date=price.effective_date,
                    registered_at=price.registered_at,
                    provider=price.provider,
                    price_timestamp=price.price_timestamp,
                )
            )

    def list(self) -> tuple[MarketPrice, ...]:
        assets = {str(asset.id): asset for asset in SqliteAssetRepository().list()}
        with SessionFactory() as session:
            rows = (
                session.query(MarketPriceRecord)
                .order_by(
                    MarketPriceRecord.effective_date,
                    MarketPriceRecord.registered_at,
                    MarketPriceRecord.id,
                )
                .all()
            )
        rows = [row for row in rows if row.asset_id in assets]
        return tuple(
            MarketPrice(
                id=UUID(row.id),
                asset=assets[row.asset_id],
                price=Money(Decimal(row.price)),
                effective_date=row.effective_date,
                registered_at=SqliteAssetRepository._utc(row.registered_at),
                provider=row.provider,
                price_timestamp=(
                    SqliteAssetRepository._utc(row.price_timestamp) if row.price_timestamp else None
                ),
            )
            for row in rows
        )


class SqliteMarketPriceRefreshRunRepository:
    def save(self, run: dict[str, object]) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.add(
                MarketPriceRefreshRunRecord(
                    id=str(run["id"]),
                    started_at=cast(datetime, run["started_at"]),
                    finished_at=cast(datetime, run["finished_at"]),
                    status=str(run["status"]),
                    outcomes_json=json.dumps(run["providers"], ensure_ascii=False),
                )
            )

    def list_recent(self, limit: int = 20) -> tuple[dict[str, object], ...]:
        initialize_database()
        bounded_limit = max(1, min(limit, 100))
        with SessionFactory() as session:
            rows = (
                session.query(MarketPriceRefreshRunRecord)
                .order_by(MarketPriceRefreshRunRecord.started_at.desc())
                .limit(bounded_limit)
                .all()
            )
        return tuple(
            {
                "id": row.id,
                "started_at": row.started_at.isoformat(),
                "finished_at": row.finished_at.isoformat(),
                "status": row.status,
                "providers": json.loads(row.outcomes_json),
            }
            for row in rows
        )


class SqliteBenchmarkRateRepository:
    def save(self, rate: BenchmarkRate) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                BenchmarkRateRecord(
                    name=rate.name,
                    effective_date=rate.effective_date,
                    return_percentage=str(rate.return_percentage),
                )
            )

    def list(self) -> tuple[BenchmarkRate, ...]:
        with SessionFactory() as session:
            rows = (
                session.query(BenchmarkRateRecord)
                .order_by(BenchmarkRateRecord.name, BenchmarkRateRecord.effective_date)
                .all()
            )
        return tuple(
            BenchmarkRate(
                name=row.name,
                effective_date=row.effective_date,
                return_percentage=Decimal(row.return_percentage),
            )
            for row in rows
        )


class SqliteBenchmarkObservationRepository:
    def save(self, observation: BenchmarkObservation) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                BenchmarkObservationRecord(
                    benchmark=observation.benchmark,
                    effective_date=observation.effective_date,
                    nature=observation.nature,
                    value=str(observation.value),
                    source=observation.source,
                )
            )

    def list(self, benchmark: str) -> tuple[BenchmarkObservation, ...]:
        initialize_database()
        with SessionFactory() as session:
            rows = (
                session.query(BenchmarkObservationRecord)
                .filter(BenchmarkObservationRecord.benchmark == benchmark.upper())
                .order_by(BenchmarkObservationRecord.effective_date)
                .all()
            )
        return tuple(
            BenchmarkObservation(
                benchmark=row.benchmark,
                effective_date=row.effective_date,
                value=Decimal(row.value),
                nature=cast("BenchmarkNature", row.nature),
                source=row.source,
            )
            for row in rows
        )


class SqliteFxRateRepository:
    def list(self, base_currency: str, quote_currency: str) -> tuple[FxRateObservation, ...]:
        initialize_database()
        with SessionFactory() as session:
            rows = (
                session.query(FxRateRecord)
                .filter(
                    FxRateRecord.base_currency == base_currency.upper(),
                    FxRateRecord.quote_currency == quote_currency.upper(),
                )
                .order_by(FxRateRecord.effective_date)
                .all()
            )
        return tuple(
            FxRateObservation(
                base_currency=row.base_currency,
                quote_currency=row.quote_currency,
                rate=Decimal(row.rate),
                effective_date=row.effective_date,
                source=row.source,
            )
            for row in rows
        )

    def save(self, observation: FxRateObservation) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                FxRateRecord(
                    base_currency=observation.base_currency.upper(),
                    quote_currency=observation.quote_currency.upper(),
                    effective_date=observation.effective_date,
                    rate=str(observation.rate),
                    source=observation.source,
                )
            )

    def save_many(self, observations: tuple[FxRateObservation, ...]) -> None:
        """Upsert a dated FX series in one transaction instead of one commit per row."""
        if not observations:
            return
        initialize_database()
        rows = [
            {
                "base_currency": item.base_currency.upper(),
                "quote_currency": item.quote_currency.upper(),
                "effective_date": item.effective_date,
                "rate": str(item.rate),
                "source": item.source,
            }
            for item in observations
        ]
        statement = sqlite_insert(FxRateRecord).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=[
                FxRateRecord.base_currency,
                FxRateRecord.quote_currency,
                FxRateRecord.effective_date,
            ],
            set_={"rate": statement.excluded.rate, "source": statement.excluded.source},
        )
        with SessionFactory.begin() as session:
            session.execute(statement)

    def latest_on_or_before(
        self, base_currency: str, quote_currency: str, effective_date: date
    ) -> FxRateObservation | None:
        initialize_database()
        with SessionFactory() as session:
            row = (
                session.query(FxRateRecord)
                .filter(
                    FxRateRecord.base_currency == base_currency.upper(),
                    FxRateRecord.quote_currency == quote_currency.upper(),
                    FxRateRecord.effective_date <= effective_date,
                )
                .order_by(FxRateRecord.effective_date.desc())
                .first()
            )
        return (
            FxRateObservation(
                base_currency=row.base_currency,
                quote_currency=row.quote_currency,
                rate=Decimal(row.rate),
                effective_date=row.effective_date,
                source=row.source,
            )
            if row
            else None
        )


class SqlitePortfolioConfigurationRepository:
    BASE_CURRENCY_KEY = "portfolio_base_currency"

    def get_base_currency(self) -> str:
        initialize_database()
        with SessionFactory() as session:
            row = session.get(PortfolioConfigurationRecord, self.BASE_CURRENCY_KEY)
        return row.value.upper() if row else "BRL"

    def save_base_currency(self, currency: str) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                PortfolioConfigurationRecord(key=self.BASE_CURRENCY_KEY, value=currency.upper())
            )


class SqliteProviderHealthRepository:
    def get(self, provider: str) -> ProviderHealth | None:
        initialize_database()
        with SessionFactory() as session:
            row = session.get(ProviderHealthRecord, provider)
        return (
            ProviderHealth(
                provider=row.provider,
                last_success=SqliteAssetRepository._utc(row.last_success)
                if row.last_success
                else None,
                last_failure=SqliteAssetRepository._utc(row.last_failure)
                if row.last_failure
                else None,
                consecutive_failures=row.consecutive_failures,
                last_error_type=row.last_error_type,
            )
            if row
            else None
        )

    def save(self, health: ProviderHealth) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.merge(
                ProviderHealthRecord(
                    provider=health.provider,
                    last_success=health.last_success,
                    last_failure=health.last_failure,
                    consecutive_failures=health.consecutive_failures,
                    last_error_type=health.last_error_type,
                )
            )


class SqlitePaidIncomeSettingsRepository:
    def get(self):
        from income_analytics.application.paid_income import PaidIncomeSettings

        initialize_database()
        with SessionFactory() as session:
            row = session.get(PaidIncomeProviderSettingsRecord, 1)
        return PaidIncomeSettings(
            enabled=row.enabled if row else False,
            api_token=row.api_token if row else None,
            last_sync_at=SqliteAssetRepository._utc(row.last_sync_at)
            if row and row.last_sync_at
            else None,
            last_result=row.last_result if row else None,
        )

    def save(self, settings) -> None:
        initialize_database()
        now = datetime.now(UTC)
        with SessionFactory.begin() as session:
            current = session.get(PaidIncomeProviderSettingsRecord, 1)
            session.merge(
                PaidIncomeProviderSettingsRecord(
                    id=1,
                    provider="BRAPI",
                    enabled=settings.enabled,
                    api_token=settings.api_token,
                    last_sync_at=settings.last_sync_at,
                    last_result=str(settings.last_result) if settings.last_result else None,
                    created_at=current.created_at if current else now,
                    updated_at=now,
                )
            )


class SqliteImportedPaidIncomeRepository:
    def find_by_fingerprint(self, fingerprint: str):
        initialize_database()
        with SessionFactory() as session:
            return (
                session.query(ImportedPaidIncomeRecord)
                .filter_by(raw_fingerprint=fingerprint)
                .one_or_none()
            )

    def save(
        self,
        *,
        event,
        asset_id,
        import_status,
        detail,
        eligible_quantity,
        calculated_amount,
        financial_event_id,
    ) -> None:
        initialize_database()
        now = datetime.now(UTC)
        with SessionFactory.begin() as session:
            current = (
                session.query(ImportedPaidIncomeRecord)
                .filter_by(raw_fingerprint=event.fingerprint)
                .one_or_none()
            )
            record = ImportedPaidIncomeRecord(
                id=current.id if current else str(__import__("uuid").uuid4()),
                provider=event.provider,
                provider_event_id=event.provider_event_id,
                raw_fingerprint=event.fingerprint,
                asset_id=asset_id,
                income_type=event.income_type,
                record_date=event.record_date,
                payment_date=event.payment_date,
                amount_per_unit=str(event.amount_per_unit),
                eligible_quantity=str(eligible_quantity) if eligible_quantity is not None else None,
                calculated_amount=str(calculated_amount) if calculated_amount is not None else None,
                financial_event_id=financial_event_id,
                import_status=import_status,
                detail=detail,
                imported_at=now if import_status == "IMPORTED" else None,
                created_at=current.created_at if current else now,
                updated_at=now,
            )
            session.merge(record)


class SqlitePortfolioDataRepository:
    """Deletes user portfolio data in dependency order."""

    def clear(self) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.query(FinancialEventRecord).delete()
            session.query(ImportedPaidIncomeRecord).delete()
            session.query(PaidIncomeProviderSettingsRecord).delete()
            session.query(MarketPriceRecord).delete()
            session.query(RecurringRuleRecord).delete()
            session.query(FixedIncomeDetailsRecord).delete()
            session.query(PensionPlanDetailsRecord).delete()
            session.query(RealEstateDetailsRecord).delete()
            session.query(AssetTargetRecord).delete()
            session.query(AllocationTargetRecord).delete()
            session.query(AssetRecord).delete()
            session.query(BenchmarkRateRecord).delete()
            session.query(BenchmarkObservationRecord).delete()
            session.query(FxRateRecord).delete()
            session.query(PortfolioConfigurationRecord).delete()


class SqliteAllocationPolicyRepository:
    def save(self, policy: AllocationPolicy) -> None:
        initialize_database()
        with SessionFactory.begin() as session:
            session.query(AllocationTargetRecord).delete()
            session.add_all(
                AllocationTargetRecord(asset_class=key.value, target=str(value))
                for key, value in policy.targets.items()
            )

    def get(self) -> AllocationPolicy | None:
        from income_analytics.domain.enums.asset_class import AssetClass

        with SessionFactory() as session:
            rows = session.query(AllocationTargetRecord).all()
        return (
            AllocationPolicy(
                targets={AssetClass(row.asset_class): Decimal(row.target) for row in rows}
            )
            if rows
            else None
        )


class SqliteAssetAllocationPolicyRepository:
    def save(self, policy: AssetAllocationPolicy) -> None:
        initialize_database()
        assets = {str(asset.ticker): asset for asset in SqliteAssetRepository().list()}
        with SessionFactory.begin() as session:
            session.query(AssetTargetRecord).delete()
            for targets in policy.targets.values():
                for ticker, target in targets.items():
                    session.add(
                        AssetTargetRecord(asset_id=str(assets[ticker].id), target=str(target))
                    )

    def get(self) -> AssetAllocationPolicy | None:
        assets = {str(asset.id): asset for asset in SqliteAssetRepository().list()}
        with SessionFactory() as session:
            rows = session.query(AssetTargetRecord).all()
        if not rows:
            return None
        targets: dict[AssetClass, dict[str, Decimal]] = {}
        for row in rows:
            asset = assets.get(row.asset_id)
            if asset is None:
                continue
            targets.setdefault(asset.asset_class, {})[str(asset.ticker)] = Decimal(row.target)
        return AssetAllocationPolicy(targets=targets) if targets else None
