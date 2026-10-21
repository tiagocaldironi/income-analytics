"""SQLAlchemy tables for persisted source-of-truth records."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from income_analytics.infrastructure.database import Base


class PortfolioRecord(Base):
    __tablename__ = "portfolios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PortfolioAssetRecord(Base):
    __tablename__ = "portfolio_assets"
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), primary_key=True
    )
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), primary_key=True
    )


class AssetRecord(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    asset_class: Mapped[str] = mapped_column(String(50))
    asset_type: Mapped[str] = mapped_column(String(50))
    valuation_method: Mapped[str] = mapped_column(String(50), default="MARKET_PRICE")
    currency_code: Mapped[str] = mapped_column(String(3))
    country: Mapped[str] = mapped_column(String(16))
    sector: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FixedIncomeDetailsRecord(Base):
    __tablename__ = "fixed_income_details"
    __table_args__ = (
        ForeignKeyConstraint(
            ["portfolio_id", "asset_id"],
            ["portfolio_assets.portfolio_id", "portfolio_assets.asset_id"],
            ondelete="RESTRICT",
        ),
    )
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    instrument_type: Mapped[str] = mapped_column(String(50))
    issuer: Mapped[str | None] = mapped_column(String(200))
    indexer_type: Mapped[str] = mapped_column(String(50))
    contracted_rate: Mapped[str | None] = mapped_column(String(40))
    percentage_of_indexer: Mapped[str | None] = mapped_column(String(40))
    spread: Mapped[str | None] = mapped_column(String(40))
    application_date: Mapped[date] = mapped_column(Date)
    maturity_date: Mapped[date | None] = mapped_column(Date)
    principal_amount: Mapped[str] = mapped_column(String(40))
    liquidity_type: Mapped[str | None] = mapped_column(String(50))
    tax_exempt: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PensionPlanDetailsRecord(Base):
    __tablename__ = "pension_plan_details"
    __table_args__ = (
        ForeignKeyConstraint(
            ["portfolio_id", "asset_id"],
            ["portfolio_assets.portfolio_id", "portfolio_assets.asset_id"],
            ondelete="RESTRICT",
        ),
    )
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    pension_type: Mapped[str] = mapped_column(String(16))
    institution: Mapped[str] = mapped_column(String(200))
    institution_cnpj: Mapped[str | None] = mapped_column(String(14))
    plan_name: Mapped[str] = mapped_column(String(200))
    tax_regime: Mapped[str] = mapped_column(String(32))
    start_date: Mapped[date] = mapped_column(Date)
    reported_balance: Mapped[str] = mapped_column(String(40))
    reported_balance_date: Mapped[date] = mapped_column(Date)
    ownership_origin: Mapped[str] = mapped_column(String(16), default="PARTICULAR")
    pension_system_type: Mapped[str] = mapped_column(String(16), default="OPEN")
    product_type: Mapped[str | None] = mapped_column(String(16))
    closed_plan_modality: Mapped[str | None] = mapped_column(String(16))
    sponsor_name: Mapped[str | None] = mapped_column(String(200))
    sponsor_cnpj: Mapped[str | None] = mapped_column(String(14))
    susep_process_number: Mapped[str | None] = mapped_column(String(80))
    cnpb: Mapped[str | None] = mapped_column(String(80))
    participant_balance: Mapped[str | None] = mapped_column(String(40))
    sponsor_balance: Mapped[str | None] = mapped_column(String(40))
    employer_match_enabled: Mapped[bool | None] = mapped_column()
    employer_match_rate: Mapped[str | None] = mapped_column(String(40))
    match_limit: Mapped[str | None] = mapped_column(String(40))
    match_rule_notes: Mapped[str | None] = mapped_column(Text)
    vesting_enabled: Mapped[bool | None] = mapped_column()
    current_vested_percentage: Mapped[str | None] = mapped_column(String(40))
    vesting_rule_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")


class PensionInvestmentVehicleRecord(Base):
    __tablename__ = "pension_investment_vehicles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["portfolio_id", "pension_asset_id"],
            ["portfolio_assets.portfolio_id", "portfolio_assets.asset_id"],
            ondelete="RESTRICT",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    pension_asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    vehicle_name: Mapped[str] = mapped_column(String(300))
    vehicle_cnpj: Mapped[str] = mapped_column(String(14))
    vehicle_type: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(24))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)


class PensionFundQuotaRecord(Base):
    __tablename__ = "pension_fund_quotas"
    vehicle_cnpj: Mapped[str] = mapped_column(String(14), primary_key=True)
    reference_date: Mapped[date] = mapped_column(Date, primary_key=True)
    quota: Mapped[str] = mapped_column(String(48))
    source: Mapped[str] = mapped_column(String(16))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RealEstateDetailsRecord(Base):
    __tablename__ = "real_estate_details"
    __table_args__ = (
        ForeignKeyConstraint(
            ["portfolio_id", "asset_id"],
            ["portfolio_assets.portfolio_id", "portfolio_assets.asset_id"],
            ondelete="RESTRICT",
        ),
    )
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    property_type: Mapped[str] = mapped_column(String(32))
    country: Mapped[str] = mapped_column(String(16), default="BR")
    description: Mapped[str] = mapped_column(Text)
    cep: Mapped[str] = mapped_column(String(16))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(32))
    neighborhood: Mapped[str | None] = mapped_column(String(100))
    usable_area_m2: Mapped[str | None] = mapped_column(String(40))
    bedrooms: Mapped[int | None] = mapped_column()
    parking_spaces: Mapped[int | None] = mapped_column()
    acquisition_date: Mapped[date | None] = mapped_column(Date)
    acquisition_value: Mapped[str | None] = mapped_column(String(40))
    ownership_percentage: Mapped[str] = mapped_column(String(40), default="100")
    current_manual_value: Mapped[str] = mapped_column(String(40))
    valuation_date: Mapped[date] = mapped_column(Date)


class RecurringRuleRecord(Base):
    __tablename__ = "recurring_rules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["portfolio_id", "asset_id"],
            ["portfolio_assets.portfolio_id", "portfolio_assets.asset_id"],
            ondelete="RESTRICT",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(32))
    amount: Mapped[str] = mapped_column(String(40))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"))
    frequency: Mapped[str] = mapped_column(String(16))
    next_execution_date: Mapped[date] = mapped_column(Date)
    end_execution_date: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(default=True)


class FinancialEventRecord(Base):
    __tablename__ = "financial_events"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "id", name="uq_financial_events_portfolio_id"),
        ForeignKeyConstraint(
            ["portfolio_id", "asset_id"],
            ["portfolio_assets.portfolio_id", "portfolio_assets.asset_id"],
            ondelete="RESTRICT",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"))
    quantity: Mapped[str | None] = mapped_column(String(40))
    unit_price: Mapped[str | None] = mapped_column(String(40))
    amount: Mapped[str | None] = mapped_column(String(40))
    effective_date: Mapped[date] = mapped_column(Date)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[str | None] = mapped_column(Text)


class MarketPriceRecord(Base):
    __tablename__ = "market_prices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    price: Mapped[str] = mapped_column(String(40))
    effective_date: Mapped[date] = mapped_column(Date, index=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    price_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MarketPriceRefreshRunRecord(Base):
    """Append-only provider outcomes for one portfolio quote refresh."""

    __tablename__ = "market_price_refresh_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    outcomes_json: Mapped[str] = mapped_column(Text, nullable=False)


class BenchmarkRateRecord(Base):
    __tablename__ = "benchmark_rates"
    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    effective_date: Mapped[date] = mapped_column(Date, primary_key=True)
    return_percentage: Mapped[str] = mapped_column(String(40))


class BenchmarkObservationRecord(Base):
    __tablename__ = "benchmark_observations"
    benchmark: Mapped[str] = mapped_column(String(32), primary_key=True)
    effective_date: Mapped[date] = mapped_column(Date, primary_key=True)
    nature: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)


class FxRateRecord(Base):
    __tablename__ = "fx_rates"
    base_currency: Mapped[str] = mapped_column(String(12), primary_key=True)
    quote_currency: Mapped[str] = mapped_column(String(12), primary_key=True)
    effective_date: Mapped[date] = mapped_column(Date, primary_key=True)
    rate: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)


class PortfolioConfigurationRecord(Base):
    __tablename__ = "portfolio_configuration"
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), primary_key=True
    )
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(64), nullable=False)


class PortfolioDashboardSnapshotRecord(Base):
    """Atomically replaced read model used by the Minha Carteira first render."""

    __tablename__ = "portfolio_dashboard_snapshot"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="VALID")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class ProviderHealthRecord(Base):
    __tablename__ = "provider_health"
    provider: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(nullable=False, default=0)
    last_error_type: Mapped[str | None] = mapped_column(String(80))


class AllocationTargetRecord(Base):
    __tablename__ = "allocation_targets"
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), primary_key=True
    )
    asset_class: Mapped[str] = mapped_column(String(50), primary_key=True)
    target: Mapped[str] = mapped_column(String(40))


class IncomeStarterTemplateVersionRecord(Base):
    __tablename__ = "income_starter_template_versions"
    __table_args__ = (
        UniqueConstraint("template_key", "version", name="uq_income_starter_version"),
        CheckConstraint(
            "template_type IN ('GUIDED_JOURNEY', 'ALLOCATION_MODEL')",
            name="ck_income_starter_template_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    template_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template_type: Mapped[str] = mapped_column(
        String(24), nullable=False, default="ALLOCATION_MODEL"
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    risk_profile: Mapped[str] = mapped_column(String(80), nullable=False)
    horizon: Mapped[str] = mapped_column(String(120), nullable=False)
    volatility_tolerance: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge: Mapped[str] = mapped_column(Text, nullable=False)
    typical_profile: Mapped[str] = mapped_column(Text, nullable=False)
    characteristics_json: Mapped[str] = mapped_column(Text, nullable=False)
    not_suitable_json: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(120), nullable=False)
    methodology: Mapped[str] = mapped_column(Text, nullable=False)
    methodology_sources_json: Mapped[str] = mapped_column(Text, nullable=False)
    allocation_sources_json: Mapped[str] = mapped_column(Text, nullable=False)
    allocations_json: Mapped[str | None] = mapped_column(Text)
    allocations_validated: Mapped[bool] = mapped_column(nullable=False, default=False)
    financial_review_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING"
    )
    financial_approved_by: Mapped[str | None] = mapped_column(String(120))
    financial_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    regulatory_review_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING"
    )
    regulatory_approved_by: Mapped[str | None] = mapped_column(String(120))
    regulatory_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_by: Mapped[str | None] = mapped_column(String(120))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PortfolioStrategyMetadataRecord(Base):
    __tablename__ = "portfolio_strategy_metadata"
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(120), nullable=False)
    template_key: Mapped[str | None] = mapped_column(String(64))
    template_version: Mapped[int | None] = mapped_column(Integer)
    customized: Mapped[bool] = mapped_column(nullable=False, default=False)
    adopted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_allocations_json: Mapped[str] = mapped_column(Text, nullable=False)


class IncomeStarterJourneyProgressRecord(Base):
    __tablename__ = "income_starter_journey_progress"

    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), primary_key=True
    )
    template_key: Mapped[str] = mapped_column(String(64), nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    essential_monthly_expenses: Mapped[str | None] = mapped_column(String(40))
    coverage_months: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    reserve_goal: Mapped[str | None] = mapped_column(String(40))
    declared_reserved_amount: Mapped[str] = mapped_column(String(40), nullable=False, default="0")
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AssetEconomicExposureRecord(Base):
    __tablename__ = "asset_economic_exposures"
    __table_args__ = (
        UniqueConstraint(
            "asset_id", "category", "source", name="uq_asset_economic_exposure_source"
        ),
        CheckConstraint(
            "category IN ("
            "'BRAZIL_EQUITY','INTERNATIONAL_EQUITY','FIXED_INCOME',"
            "'LISTED_REAL_ESTATE','DIRECT_REAL_ESTATE','COMMODITIES',"
            "'CRYPTO','CASH_EQUIVALENTS','UNCLASSIFIED')",
            name="ck_economic_exposure_category",
        ),
        CheckConstraint(
            "classification_status IN ('CONFIRMED', 'UNKNOWN')",
            name="ck_economic_exposure_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    exposure_share: Mapped[str | None] = mapped_column(String(40))
    classification_status: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str | None] = mapped_column(String(80))
    source_reference_date: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class AssetTargetRecord(Base):
    __tablename__ = "asset_targets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["portfolio_id", "asset_id"],
            ["portfolio_assets.portfolio_id", "portfolio_assets.asset_id"],
            ondelete="RESTRICT",
        ),
    )
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), primary_key=True
    )
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), primary_key=True)
    target: Mapped[str] = mapped_column(String(40))


class PaidIncomeProviderSettingsRecord(Base):
    __tablename__ = "paid_income_provider_settings"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="BRAPI")
    enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    api_token: Mapped[str | None] = mapped_column(Text)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_result: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ImportedPaidIncomeRecord(Base):
    __tablename__ = "imported_paid_income"
    __table_args__ = (
        ForeignKeyConstraint(
            ["portfolio_id", "asset_id"],
            ["portfolio_assets.portfolio_id", "portfolio_assets.asset_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["portfolio_id", "financial_event_id"],
            ["financial_events.portfolio_id", "financial_events.id"],
            ondelete="RESTRICT",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str | None] = mapped_column(String(160), index=True)
    raw_fingerprint: Mapped[str] = mapped_column(String(128), index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False)
    income_type: Mapped[str] = mapped_column(String(32), nullable=False)
    record_date: Mapped[date | None] = mapped_column(Date)
    payment_date: Mapped[date | None] = mapped_column(Date)
    amount_per_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    eligible_quantity: Mapped[str | None] = mapped_column(String(40))
    calculated_amount: Mapped[str | None] = mapped_column(String(40))
    financial_event_id: Mapped[str | None] = mapped_column(ForeignKey("financial_events.id"))
    import_status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class B3ImportBatchRecord(Base):
    __tablename__ = "b3_import_batches"
    __table_args__ = (UniqueConstraint("portfolio_id", "id", name="uq_b3_batches_portfolio_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="B3")
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unsupported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class B3ImportedRecord(Base):
    __tablename__ = "b3_imported_records"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "source",
            "fingerprint",
            "occurrence_index",
            name="uq_b3_imported_record_identity",
        ),
        ForeignKeyConstraint(
            ["portfolio_id", "batch_id"],
            ["b3_import_batches.portfolio_id", "b3_import_batches.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["portfolio_id", "asset_id"],
            ["portfolio_assets.portfolio_id", "portfolio_assets.asset_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["portfolio_id", "financial_event_id"],
            ["financial_events.portfolio_id", "financial_events.id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    batch_id: Mapped[str] = mapped_column(ForeignKey("b3_import_batches.id"), index=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="B3")
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    occurrence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date)
    event_type: Mapped[str | None] = mapped_column(String(32))
    income_type: Mapped[str | None] = mapped_column(String(32))
    source_symbol: Mapped[str | None] = mapped_column(String(32))
    normalized_symbol: Mapped[str | None] = mapped_column(String(32), index=True)
    institution: Mapped[str | None] = mapped_column(String(200))
    market: Mapped[str | None] = mapped_column(String(80))
    quantity: Mapped[str | None] = mapped_column(String(40))
    unit_price: Mapped[str | None] = mapped_column(String(40))
    total_value: Mapped[str | None] = mapped_column(String(40))
    raw_payload: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"))
    financial_event_id: Mapped[str | None] = mapped_column(ForeignKey("financial_events.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MagicFormulaFundamentalsSnapshotRecord(Base):
    __tablename__ = "magic_formula_fundamentals_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    issuer_id: Mapped[str] = mapped_column(String(64), index=True)
    financial_reference_date: Mapped[date] = mapped_column(Date)
    market_reference_date: Mapped[date] = mapped_column(Date)
    statement_type: Mapped[str] = mapped_column(String(16))
    statement_scope: Mapped[str] = mapped_column(String(16))
    adapter_version: Mapped[str] = mapped_column(String(64))
    normalization_status: Mapped[str] = mapped_column(String(48))
    validation_status: Mapped[str] = mapped_column(String(32))
    metrics_json: Mapped[str] = mapped_column(Text)
    lineage_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CompanyNormalizationValidationRecord(Base):
    __tablename__ = "company_normalization_validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    issuer_id: Mapped[str] = mapped_column(String(64), index=True)
    reference_date: Mapped[date] = mapped_column(Date)
    adapter_version: Mapped[str] = mapped_column(String(64))
    metric: Mapped[str] = mapped_column(String(64))
    expected_value: Mapped[str] = mapped_column(String(64))
    actual_value: Mapped[str] = mapped_column(String(64))
    difference: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text)
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
