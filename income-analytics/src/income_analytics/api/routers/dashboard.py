"""HTTP endpoints for the local portfolio dashboard."""

from __future__ import annotations

import json
import logging
from base64 import b64decode
from binascii import Error as Base64Error
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from time import sleep
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from income_analytics.application.asset_discovery import AssetCandidate, AssetDiscoveryUnavailable
from income_analytics.application.b3_import import (
    B3ImportedRecordStatus,
    B3ImportReportType,
    B3ImportService,
)
from income_analytics.application.benchmark_comparison import build_performance_comparison
from income_analytics.application.benchmark_data import BenchmarkDataUnavailable
from income_analytics.application.capital_applied import calculate_capital_applied
from income_analytics.application.fx_data import FxRateUnavailable
from income_analytics.application.historical_portfolio_reconstruction import (
    HistoricalPortfolioReconstructionService,
)
from income_analytics.application.investment_tools import TOOLS, ranking_contract
from income_analytics.application.magic_formula_canonical_ranking import (
    MagicFormulaCanonicalRankingRepository,
    company_metadata_for_snapshot,
    ranking_read_model,
)
from income_analytics.application.market_data import (
    MarketDataProvider,
    MarketDataUnavailable,
    MarketPriceObservation,
)
from income_analytics.application.paid_income import (
    PaidIncomeIntegrationStatus,
    PaidIncomeSettings,
    PaidIncomeSyncService,
)
from income_analytics.application.pension_market_data import PensionMarketDataUnavailable
from income_analytics.application.portfolio_context import (
    MAIN_PORTFOLIO_ID,
    current_portfolio_id,
    get_request_session,
    reset_active_portfolio_id,
    set_active_portfolio_id,
)
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.application.provider_health import ProviderHealthRegistry
from income_analytics.application.wealth_explanation import WealthExplanationService
from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.asset_allocation_policy import AssetAllocationPolicy
from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.enums.capital_flow_type import CapitalFlowType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)
from income_analytics.domain.fixed_income_details import FixedIncomeDetails
from income_analytics.domain.projectors.asset_composition_projector import (
    AssetCompositionInput,
    AssetCompositionProjector,
)
from income_analytics.domain.projectors.asset_rebalancing_projector import AssetAllocationStrategy
from income_analytics.domain.projectors.performance_projector import PerformanceProjector
from income_analytics.domain.projectors.portfolio_projector import PortfolioProjector
from income_analytics.domain.read_models.diversification_projection import DiversificationDimension
from income_analytics.domain.read_models.portfolio_history import PortfolioSnapshot
from income_analytics.domain.read_models.portfolio_history_boundary import PortfolioHistoryBoundary
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection
from income_analytics.domain.read_models.position_projection import PositionProjection
from income_analytics.domain.recurring_rule import RecurrenceFrequency, RecurringRule
from income_analytics.domain.value_objects.money import Money
from income_analytics.infrastructure.b3_benchmark_data import (
    B3BenchmarkDataProvider,
    IVVB11BenchmarkDataProvider,
)
from income_analytics.infrastructure.b3_cotahist_market_data import B3CotahistMarketDataProvider
from income_analytics.infrastructure.b3_etf_market_data import B3EtfPriceProvider
from income_analytics.infrastructure.b3_report_parser import (
    B3LayoutError,
    B3MovementReportParser,
    B3NegotiationReportParser,
)
from income_analytics.infrastructure.bcb_benchmark_data import BcbBenchmarkDataProvider
from income_analytics.infrastructure.bcb_fx_data import BcbFxRateProvider
from income_analytics.infrastructure.brapi_asset_discovery import BrapiAssetDiscoveryProvider
from income_analytics.infrastructure.brapi_market_data import BrapiMarketDataProvider
from income_analytics.infrastructure.brapi_paid_income import BrapiPaidIncomeProvider
from income_analytics.infrastructure.coingecko_crypto_data import CoinGeckoCryptoProvider
from income_analytics.infrastructure.cvm_pension_market_data import CvmPensionMarketDataProvider
from income_analytics.infrastructure.irpf_xlsx_import import (
    IrpfBrazilianStockPosition,
    parse_irpf_brazilian_stocks,
)
from income_analytics.infrastructure.models import FinancialEventRecord
from income_analytics.infrastructure.sqlite_repositories import (
    SqliteB3ImportRepository,
    SqliteImportedPaidIncomeRepository,
    SqliteMarketPriceRefreshRunRepository,
    SqlitePaidIncomeSettingsRepository,
    SqlitePensionFundQuotaRepository,
    SqlitePensionInvestmentVehicleRepository,
    SqlitePortfolioDashboardSnapshotRepository,
    SqlitePortfolioRepository,
    SqliteProviderHealthRepository,
)
from income_analytics.infrastructure.twelve_data_us_market_data import TwelveDataUSMarketProvider

router = APIRouter(prefix="/api", tags=["Portfolio"])
logger = logging.getLogger(__name__)
B3_COMPARISON_BENCHMARKS = frozenset({"IBOV", "IFIX", "SMLL", "IDIV", "IVVB11"})
b3_import_router = APIRouter(tags=["B3 imports"])


class _PortfolioSessionProxy:
    """Compatibility resolver; a PortfolioSession lives only in request context."""

    def _target(self) -> PortfolioSession:
        current = get_request_session()
        if current is None:
            current = PortfolioSession(portfolio_id=current_portfolio_id(), persistent=True)
        return current  # type: ignore[return-value]

    def __getattr__(self, name: str):
        return getattr(self._target(), name)

    def __setattr__(self, name: str, value: object) -> None:
        setattr(self._target(), name, value)


class _PortfolioRepositoryProxy:
    """Resolve a portfolio-owned adapter against the current request context."""

    def __init__(self, factory):
        self._factory = factory

    def __getattr__(self, name: str):
        return getattr(self._factory(current_portfolio_id()), name)


session = _PortfolioSessionProxy()
_b3_preview_cache: dict[tuple[UUID, UUID], tuple[object, tuple[object, ...]]] = {}
asset_discovery = BrapiAssetDiscoveryProvider()
market_data = BrapiMarketDataProvider()
historical_market_data = B3CotahistMarketDataProvider()
crypto_data = CoinGeckoCryptoProvider()
us_market_data = TwelveDataUSMarketProvider()
cvm_pension_data = CvmPensionMarketDataProvider()
benchmark_data = BcbBenchmarkDataProvider()
index_benchmark_data = B3BenchmarkDataProvider()
ivvb11_benchmark_data = IVVB11BenchmarkDataProvider(historical_market_data)
fx_data = BcbFxRateProvider()
provider_health = ProviderHealthRegistry(SqliteProviderHealthRepository())
paid_income_settings = SqlitePaidIncomeSettingsRepository()
dashboard_snapshot_repository = _PortfolioRepositoryProxy(
    SqlitePortfolioDashboardSnapshotRepository
)
market_price_refresh_runs = _PortfolioRepositoryProxy(SqliteMarketPriceRefreshRunRepository)
PORTFOLIO_DASHBOARD_READ_MODEL_VERSION = 3


def _effective_analysis_end_date(start_date: date, end_date: date) -> date:
    """Prevent realised portfolio analyses from extending beyond today."""
    effective_end_date = min(end_date, date.today())
    if effective_end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O período selecionado ainda não possui dias realizados.",
        )
    return effective_end_date


class B3MarketDataFallbackProvider:
    """Use BRAPI, an optional category source, then official B3 COTAHIST."""

    source = "B3MarketDataFallbackProvider"

    def __init__(self, category_provider: MarketDataProvider | None = None) -> None:
        self._category_provider = category_provider

    def _chain(
        self, symbol: str, operation: str, effective_date: date | None = None
    ) -> MarketPriceObservation:
        attempts: list[tuple[str, str, str | None]] = []
        providers: list[tuple[str, MarketDataProvider]] = [("brapi", market_data)]
        if self._category_provider is not None:
            providers.append(("b3_etf", self._category_provider))
        providers.append(("b3_cotahist", historical_market_data))
        for index, (name, provider) in enumerate(providers):
            try:
                observation = (
                    provider.latest_price(symbol)
                    if operation == "latest"
                    else provider.price_on(symbol, effective_date or date.today())
                )
                attempts.append((name, "SUCCESS", None))
                attempts.extend(
                    (later_name, "NOT_REQUIRED", "provider anterior respondeu")
                    for later_name, _ in providers[index + 1 :]
                )
                return replace(observation, provider_attempts=tuple(attempts))
            except Exception as error:
                attempts.append((name, "NOT_FOUND", f"{type(error).__name__}: {str(error)[:300]}"))
        detail = "; ".join(f"{name} falhou ({reason})" for name, _, reason in attempts)
        raise MarketDataUnavailable(detail)

    def latest_prices(self, symbols: tuple[str, ...]) -> dict[str, MarketPriceObservation]:
        """Resolve a refresh batch by source while preserving per-ticker lineage."""
        if not symbols:
            return {}
        found: dict[str, MarketPriceObservation] = {}
        attempts: dict[str, list[tuple[str, str, str | None]]] = {symbol: [] for symbol in symbols}
        remaining = set(symbols)
        try:
            primary = market_data.latest_prices(symbols)
            if not isinstance(primary, dict):
                raise MarketDataUnavailable("BRAPI returned an invalid batch response.")
            for symbol, observation in primary.items():
                if symbol in remaining and isinstance(observation, MarketPriceObservation):
                    provider_attempts = [("brapi", "SUCCESS", None)]
                    later_providers = (
                        ("b3_etf", "b3_cotahist") if self._category_provider else ("b3_cotahist",)
                    )
                    provider_attempts.extend(
                        (later, "NOT_REQUIRED", "provider anterior respondeu")
                        for later in later_providers
                    )
                    found[symbol] = replace(observation, provider_attempts=tuple(provider_attempts))
                    remaining.remove(symbol)
            primary_error = None
        except Exception as error:
            primary_error = error
        if primary_error is None:
            for symbol in tuple(remaining):
                try:
                    observation = market_data.latest_price(symbol)
                    attempts[symbol].append(("brapi", "SUCCESS", None))
                    later_providers = (
                        ("b3_etf", "b3_cotahist") if self._category_provider else ("b3_cotahist",)
                    )
                    attempts[symbol].extend(
                        (later, "NOT_REQUIRED", "provider anterior respondeu")
                        for later in later_providers
                    )
                    found[symbol] = replace(observation, provider_attempts=tuple(attempts[symbol]))
                    remaining.remove(symbol)
                except Exception as error:
                    attempts[symbol].append(
                        ("brapi", "NOT_FOUND", f"{type(error).__name__}: {str(error)[:300]}")
                    )
        else:
            for symbol in remaining:
                attempts[symbol].append(
                    (
                        "brapi",
                        "NOT_FOUND",
                        f"{type(primary_error).__name__}: {str(primary_error)[:300]}",
                    )
                )

        category = self._category_provider
        batch = getattr(category, "latest_prices", None) if category else None
        if remaining and callable(batch):
            try:
                category_quotes = batch(tuple(sorted(remaining)))
                if isinstance(category_quotes, dict):
                    for symbol, observation in category_quotes.items():
                        if symbol in remaining and isinstance(observation, MarketPriceObservation):
                            attempts[symbol].append(("b3_etf", "SUCCESS", None))
                            attempts[symbol].append(
                                ("b3_cotahist", "NOT_REQUIRED", "provider anterior respondeu")
                            )
                            found[symbol] = replace(
                                observation, provider_attempts=tuple(attempts[symbol])
                            )
                            remaining.remove(symbol)
            except Exception as error:
                for symbol in remaining:
                    attempts[symbol].append(
                        ("b3_etf", "NOT_FOUND", f"{type(error).__name__}: {str(error)[:300]}")
                    )
        elif remaining and category is not None:
            for symbol in tuple(remaining):
                try:
                    observation = category.latest_price(symbol)
                    attempts[symbol].append(("b3_etf", "SUCCESS", None))
                    attempts[symbol].append(
                        ("b3_cotahist", "NOT_REQUIRED", "provider anterior respondeu")
                    )
                    found[symbol] = replace(observation, provider_attempts=tuple(attempts[symbol]))
                    remaining.remove(symbol)
                except Exception as error:
                    attempts[symbol].append(
                        ("b3_etf", "NOT_FOUND", f"{type(error).__name__}: {str(error)[:300]}")
                    )

        if remaining:
            history_batch = getattr(historical_market_data, "latest_prices", None)
            try:
                if callable(history_batch):
                    history_quotes = history_batch(tuple(sorted(remaining)))
                else:
                    history_quotes = {
                        symbol: historical_market_data.latest_price(symbol)
                        for symbol in sorted(remaining)
                    }
                if isinstance(history_quotes, dict):
                    for symbol, observation in history_quotes.items():
                        if symbol in remaining and isinstance(observation, MarketPriceObservation):
                            attempts[symbol].append(("b3_cotahist", "SUCCESS", None))
                            found[symbol] = replace(
                                observation, provider_attempts=tuple(attempts[symbol])
                            )
                            remaining.remove(symbol)
            except Exception as error:
                for symbol in remaining:
                    attempts[symbol].append(
                        ("b3_cotahist", "NOT_FOUND", f"{type(error).__name__}: {str(error)[:300]}")
                    )
        return found

    def latest_price(self, symbol: str) -> MarketPriceObservation:
        return self._chain(symbol, "latest")

    def price_on(self, symbol: str, effective_date: date) -> MarketPriceObservation:
        return self._chain(symbol, "historical", effective_date)


b3_market_data = B3MarketDataFallbackProvider()
b3_etf_price_data = B3EtfPriceProvider()
b3_etf_market_data = B3MarketDataFallbackProvider(b3_etf_price_data)


class UnavailableMarketDataProvider:
    """Explicitly skip assets whose valuation does not use market quotations."""

    supports_quotes = False

    def latest_price(self, symbol: str) -> MarketPriceObservation:
        raise MarketDataUnavailable(f"{symbol} não usa cotação de bolsa.")

    def price_on(self, symbol: str, effective_date: date) -> MarketPriceObservation:
        raise MarketDataUnavailable(f"{symbol} não usa cotação de bolsa.")


unavailable_market_data = UnavailableMarketDataProvider()


def market_data_provider_for(asset: Asset) -> MarketDataProvider:
    """Route listed assets to the provider that owns their market."""
    asset_class = asset.asset_class
    if asset_class is AssetClass.CRYPTO:
        return crypto_data
    if asset_class in {
        AssetClass.INTERNATIONAL,
        AssetClass.INTERNATIONAL_ETF,
        AssetClass.US_REIT,
    }:
        return us_market_data
    if asset_class in {
        AssetClass.FIXED_INCOME,
        AssetClass.PENSION,
        AssetClass.REAL_ESTATE,
        AssetClass.CASH,
    }:
        return unavailable_market_data
    if asset_class is AssetClass.BRAZILIAN_ETF:
        return b3_etf_market_data
    return b3_market_data


class TradeInput(BaseModel):
    event_type: Literal["BUY", "SELL"]
    ticker: str = Field(min_length=1, max_length=12)
    name: str | None = Field(default=None, max_length=200)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    effective_date: date
    asset_class: AssetClass
    country: str = Field(default="BR", min_length=1, max_length=16)
    currency_code: str = Field(default="BRL", min_length=1, max_length=12)
    sector: str | None = Field(default=None, max_length=80)
    capital_flow_type: CapitalFlowType = CapitalFlowType.INTERNAL_TRANSFER
    source_asset_class: AssetClass | None = None
    destination_asset_class: AssetClass | None = None


class FixedIncomeSaleInput(BaseModel):
    ticker: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=0)
    effective_date: date


class IrpfBrazilianStocksImportInput(BaseModel):
    workbook_base64: str = Field(min_length=1, max_length=15_000_000)


class B3ImportPreviewInput(BaseModel):
    workbook_base64: str = Field(min_length=1, max_length=20_000_000)
    file_name: str = Field(min_length=1, max_length=512)
    report_type: Literal["NEGOTIATION", "MOVEMENT"] | None = None


class MarketPriceInput(BaseModel):
    current_price: Decimal = Field(gt=0)
    effective_date: date


class B3EtfHistoryBackfillInput(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    start_date: date
    end_date: date


class DividendInput(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    amount: Decimal = Field(gt=0)
    effective_date: date


class JcpInput(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    gross_amount: Decimal = Field(gt=0)
    withheld_tax: Decimal = Field(ge=0)
    effective_date: date


class FiiIncomeInput(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    amount: Decimal = Field(gt=0)
    effective_date: date


class ExternalFlowInput(BaseModel):
    event_type: Literal["DEPOSIT", "WITHDRAWAL"]
    amount: Decimal = Field(gt=0)
    effective_date: date
    capital_flow_type: CapitalFlowType = CapitalFlowType.EXTERNAL_CAPITAL


class BenchmarkRateInput(BaseModel):
    return_percentage: Decimal = Field(gt=Decimal("-1"))
    effective_date: date


class AssetClassInput(BaseModel):
    asset_class: AssetClass


class AssetInput(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=200)
    asset_class: AssetClass
    country: str = Field(default="BR", min_length=1, max_length=16)
    currency_code: str = Field(default="BRL", min_length=3, max_length=12)
    sector: str | None = Field(default=None, max_length=80)


class FixedIncomeAssetInput(BaseModel):
    """Explicit contract input; no fixed-income rule is inferred from its name."""

    ticker: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    instrument_type: FixedIncomeInstrumentType
    indexer_type: FixedIncomeIndexerType
    application_date: date
    principal_amount: Decimal = Field(gt=0)
    issuer: str | None = Field(default=None, max_length=200)
    contracted_rate: Decimal | None = None
    percentage_of_indexer: Decimal | None = Field(default=None, gt=0)
    spread: Decimal | None = None
    maturity_date: date | None = None
    liquidity_type: str | None = Field(default=None, max_length=50)
    tax_exempt: bool = False


class PensionPlanInput(BaseModel):
    ticker: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    pension_type: Literal["PGBL", "VGBL", "OUTRO", "OTHER", "UNKNOWN"] = "OUTRO"
    institution: str = Field(min_length=1, max_length=200)
    institution_cnpj: str | None = Field(default=None, max_length=18)
    plan_name: str = Field(min_length=1, max_length=200)
    tax_regime: Literal[
        "UNDEFINED", "PROGRESSIVE", "REGRESSIVE", "DESCONHECIDO", "PROGRESSIVO", "REGRESSIVO"
    ] = "UNDEFINED"
    start_date: date
    reported_balance: Decimal = Field(ge=0)
    reported_balance_date: date
    ownership_origin: Literal["PARTICULAR", "EMPLOYER", "ASSOCIATION"] = "PARTICULAR"
    pension_system_type: Literal["OPEN", "CLOSED", "UNKNOWN"] = "OPEN"
    product_type: Literal["PGBL", "VGBL", "OUTRO", "OTHER", "UNKNOWN"] | None = None
    closed_plan_modality: Literal["CD", "CV", "BD", "UNKNOWN"] | None = None
    sponsor_name: str | None = Field(default=None, max_length=200)
    sponsor_cnpj: str | None = Field(default=None, max_length=18)
    susep_process_number: str | None = Field(default=None, max_length=80)
    cnpb: str | None = Field(default=None, max_length=80)
    participant_balance: Decimal | None = Field(default=None, ge=0)
    sponsor_balance: Decimal | None = Field(default=None, ge=0)
    employer_match_enabled: bool | None = None
    employer_match_rate: Decimal | None = Field(default=None, ge=0)
    match_limit: Decimal | None = Field(default=None, ge=0)
    match_rule_notes: str | None = None
    vesting_enabled: bool | None = None
    current_vested_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    vesting_rule_notes: str | None = None
    status: Literal["ACTIVE", "INACTIVE", "PORTED", "CLOSED"] = "ACTIVE"


class PensionVehicleInput(BaseModel):
    vehicle_cnpj: str = Field(min_length=14, max_length=18)
    vehicle_name: str | None = Field(default=None, max_length=300)
    vehicle_type: Literal["FIE", "FUND_CLASS", "UNKNOWN"] = "FUND_CLASS"


class RealEstateInput(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    property_type: str = Field(min_length=1, max_length=32)
    description: str = Field(min_length=1)
    cep: str = Field(min_length=1, max_length=16)
    country: str = Field(default="BR", min_length=2, max_length=16)
    state: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=100)
    acquisition_date: date | None = None
    acquisition_value: Decimal | None = Field(default=None, ge=0)
    ownership_percentage: Decimal = Field(default=Decimal("100"), gt=0, le=100)
    current_manual_value: Decimal = Field(gt=0)
    valuation_date: date


class RecurringRuleInput(BaseModel):
    event_type: Literal["DEPOSIT", "WITHDRAWAL", "DIVIDEND"]
    amount: Decimal = Field(gt=0)
    frequency: RecurrenceFrequency
    next_execution_date: date
    end_execution_date: date | None = None
    ticker: str | None = Field(default=None, max_length=32)


class RecurringRuleUpdateInput(BaseModel):
    amount: Decimal = Field(gt=0)
    frequency: RecurrenceFrequency
    end_execution_date: date | None = None


class AllocationPolicyInput(BaseModel):
    targets: dict[AssetClass, Decimal]


class AssetAllocationPolicyInput(BaseModel):
    targets: dict[AssetClass, dict[str, Decimal]]


class ContributionSimulationInput(BaseModel):
    amount: Decimal = Field(gt=0)
    mode: Literal["LEGACY_BEFORE_DEFICIT", "STRATEGY_GUIDED"] = "LEGACY_BEFORE_DEFICIT"
    include_asset_distribution: bool = False


class AssetRebalancingInput(BaseModel):
    asset_class: AssetClass
    amount: Decimal = Field(gt=0)
    strategy: AssetAllocationStrategy


class PortfolioConfigurationInput(BaseModel):
    portfolio_base_currency: str = Field(min_length=3, max_length=12)


class DataResetInput(BaseModel):
    confirmation: Literal["EXCLUIR"]


class PaidIncomeSettingsInput(BaseModel):
    enabled: bool
    api_token: str | None = Field(default=None, min_length=1)
    remove_token: bool = False


@router.get("/tools")
def list_investment_tools() -> dict[str, object]:
    items = [tool.serialize() for tool in TOOLS]
    if MagicFormulaCanonicalRankingRepository().latest() is not None:
        items[0]["status"] = "PARTIAL"
        items[0]["version"] = "MF_BR_2027_V1"
    return {
        "category": "OPPORTUNITY_DISCOVERY",
        "category_label": "Oportunidades",
        "items": items,
    }


@router.get("/tools/magic-formula/stocks")
def magic_formula_stocks(
    q: str = "",
    exclude_retail: bool = False,
    exclude_aviation: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> dict[str, object]:
    try:
        snapshot = MagicFormulaCanonicalRankingRepository().latest()
        if snapshot is None:
            return {
                "tool": TOOLS[0].id,
                "methodology_version": "MF_BR_2027_V1",
                "status": "NO_PUBLISHED_RANKING",
                **ranking_read_model(
                    None,
                    query=q,
                    exclude_retail=exclude_retail,
                    exclude_aviation=exclude_aviation,
                    page=page,
                    page_size=page_size,
                ),
            }
        result = ranking_read_model(
            snapshot,
            company_metadata=company_metadata_for_snapshot(snapshot),
            query=q,
            exclude_retail=exclude_retail,
            exclude_aviation=exclude_aviation,
            page=page,
            page_size=page_size,
        )
    except (OSError, ValueError) as error:
        logger.exception("Unable to read published Magic Formula ranking")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MAGIC_FORMULA_RANKING_UNAVAILABLE",
        ) from error
    return {
        "tool": TOOLS[0].id,
        "methodology_version": "MF_BR_2027_V1",
        "status": "AVAILABLE",
        **result,
    }


@router.get("/tools/magic-formula/stocks/{company_id}")
def magic_formula_stock_detail(
    company_id: str, snapshot_id: str | None = Query(default=None, min_length=1)
) -> dict[str, object]:
    repository = MagicFormulaCanonicalRankingRepository()
    try:
        snapshot = repository.read_published(snapshot_id) if snapshot_id else repository.latest()
        metadata = company_metadata_for_snapshot(snapshot) if snapshot else {}
    except ValueError as error:
        if str(error) in {"MISSING_RANKING_SNAPSHOT", "RANKING_NOT_PUBLISHED"}:
            raise HTTPException(status_code=404, detail="RANKING_SNAPSHOT_NOT_FOUND") from error
        logger.exception("Unable to read published Magic Formula company detail")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MAGIC_FORMULA_COMPANY_DETAIL_UNAVAILABLE",
        ) from error
    except OSError as error:
        logger.exception("Unable to read published Magic Formula company detail")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MAGIC_FORMULA_COMPANY_DETAIL_UNAVAILABLE",
        ) from error
    if snapshot is None:
        raise HTTPException(status_code=404, detail="RANKING_NOT_AVAILABLE")
    result = next((row for row in snapshot["results"] if row["company_id"] == company_id), None)
    provenance = next(
        (row for row in snapshot["provenance"] if row["company_id"] == company_id), None
    )
    if result is None or provenance is None:
        raise HTTPException(status_code=404, detail="COMPANY_NOT_FOUND")
    company = {
        "company_id": result["company_id"],
        "ticker": result["selected_security"],
        "company_name": result["company_name"],
        "cvm_code": result["cvm_code"],
        "isin": result.get("selected_isin"),
        "sector": metadata.get(company_id, {}).get("sector"),
        "sector_source": "CVM_FCA_GENERAL_2025",
        "sector_source_reference": metadata.get(company_id, {}).get("sector_source_reference"),
        "sector_point_in_time_safe": "UNKNOWN",
        "listing_segment": None,
    }
    ranking = {
        "global_rank": result["global_rank"],
        "earnings_yield": result["earnings_yield"],
        "earnings_yield_rank": result["earnings_yield_rank"],
        "return_on_capital": result["return_on_capital"],
        "return_on_capital_rank": result["return_on_capital_rank"],
        "combined_score": result["combined_score"],
    }
    accounting = provenance.get("accounting", [])

    def accounting_total(*metrics: str) -> str | None:
        values = [
            Decimal(item["normalized_value"])
            for item in accounting
            if item.get("metric") in metrics and item.get("normalized_value") is not None
        ]
        return str(sum(values, Decimal("0"))) if values else None

    cash = accounting_total("cash_and_equivalents")
    debt = accounting_total("financial_debt_short_term", "financial_debt_long_term")
    calculation = {
        "ebit": result.get("ebit"),
        "enterprise_value": result.get("enterprise_value"),
        "capital_employed": result.get("invested_capital"),
        "market_cap": None,
        "cash": cash,
        "debt": debt,
        "share_price": result.get("price"),
        "shares_outstanding": None,
        "value_types": {
            "ebit": "SOURCE_VALUE",
            "enterprise_value": "DERIVED",
            "capital_employed": "DERIVED",
            "cash": "SOURCE_VALUE" if cash is not None else "UNAVAILABLE",
            "debt": "DERIVED" if debt is not None else "UNAVAILABLE",
            "market_cap": "UNAVAILABLE",
            "share_price": "SOURCE_VALUE",
        },
        "lineage": {
            "ebit": [
                item["source_reference"] for item in accounting if item.get("metric") == "ebit"
            ],
            "enterprise_value": {
                "formula": (
                    "market_cap + financial_debt_short_term + "
                    "financial_debt_long_term - cash_and_equivalents"
                ),
                "market_cap_source": provenance.get("market", {}).get("capital_source_reference"),
                "accounting_sources": [
                    item["source_reference"]
                    for item in accounting
                    if item.get("metric")
                    in {
                        "cash_and_equivalents",
                        "financial_debt_short_term",
                        "financial_debt_long_term",
                    }
                ],
                "price_source": provenance.get("selected_security_source", {}).get(
                    "price_source_reference"
                ),
                "shares_source": provenance.get("point_in_time", {}).get("shares_source"),
            },
            "capital_employed": {
                "formula": (
                    "operating_current_assets - operating_current_liabilities + net_fixed_assets"
                ),
                "accounting_sources": [
                    item["source_reference"]
                    for item in accounting
                    if item.get("metric")
                    in {
                        "operating_current_assets",
                        "operating_current_liabilities",
                        "net_fixed_assets",
                    }
                ],
            },
        },
    }
    snapshot_context = {
        "ranking_snapshot_id": snapshot["ranking_snapshot_id"],
        "ranking_as_of_date": snapshot["ranking_reference_date"],
        "policy_id": snapshot["policy_id"],
        "ranking_hash": snapshot["ranking_hash"],
    }
    return {
        # Keep the established response keys while adding a typed company-detail contract.
        "item": result,
        "provenance": provenance,
        "snapshot": snapshot_context,
        "company": company,
        "ranking": ranking,
        "calculation": calculation,
        "data_basis": {
            "financial_document_type": "DFP",
            "financial_reference_period": result.get("financial_reference_date"),
            "filing_date": result.get("filing_date"),
            "information_available_date": result.get("filing_date"),
            "financial_source": "CVM",
            "price_date": result.get("price_reference_date"),
            "price_source": provenance.get("selected_security_source", {}).get(
                "price_source_reference"
            ),
            "shares_reference_date": provenance.get("market", {})
            .get("shares_resolution", {})
            .get("reference_date"),
            "shares_source": provenance.get("market", {})
            .get("shares_resolution", {})
            .get("source_reference"),
            "point_in_time": provenance.get("point_in_time"),
            "sector_classification_date": None,
            "sector_point_in_time_safe": "UNKNOWN",
        },
    }


@router.get("/tools/magic-formula/fiis")
def magic_formula_fiis() -> dict[str, object]:
    return ranking_contract(TOOLS[1])


@router.get("/assets/search")
def search_assets(
    q: str = "", limit: int = 8, asset_class: AssetClass | None = None
) -> dict[str, object]:
    if not q.strip():
        return {"candidates": [], "unavailable": False}
    requested_limit = min(max(limit, 1), 10)
    candidates: list[AssetCandidate] = []
    messages = []
    providers: tuple[object, ...]
    if asset_class in {
        AssetClass.INTERNATIONAL,
        AssetClass.INTERNATIONAL_ETF,
        AssetClass.US_REIT,
    }:
        providers = (us_market_data,)
    elif asset_class is AssetClass.CRYPTO:
        providers = (crypto_data,)
    elif asset_class in {
        AssetClass.BRAZILIAN_STOCK,
        AssetClass.BRAZILIAN_ETF,
        AssetClass.FII,
    }:
        providers = (asset_discovery,)
    else:
        # Preserve discovery for an unspecified class while allowing clients
        # that know the target market to select a provider deterministically.
        providers = (asset_discovery, crypto_data, us_market_data)
    for provider in providers:
        try:
            candidates.extend(provider.search(q, limit=requested_limit))
        except AssetDiscoveryUnavailable as error:
            messages.append(str(error))
    if not candidates:
        return {
            "candidates": [],
            "unavailable": bool(messages),
            "message": messages[0] if messages else None,
        }
    return {
        "candidates": [
            {
                "external_id": candidate.external_id,
                "symbol": candidate.symbol,
                "name": candidate.name,
                "instrument_type": candidate.instrument_type,
                "suggested_asset_class": candidate.suggested_asset_class,
                "country": candidate.country,
                "currency_code": candidate.currency_code,
                "sector": candidate.sector,
                "source": candidate.source,
            }
            for candidate in candidates[:requested_limit]
        ],
        "unavailable": False,
    }


@router.post("/assets", status_code=status.HTTP_201_CREATED)
def create_asset(asset: AssetInput) -> dict[str, object]:
    created = session.register_asset(
        ticker=asset.ticker,
        name=asset.name,
        asset_class=asset.asset_class,
        country=asset.country,
        currency_code=asset.currency_code,
        sector=asset.sector,
    )
    return {"ticker": str(created.ticker), "name": created.name, "status": "created"}


@router.post("/assets/fixed-income", status_code=status.HTTP_201_CREATED)
def create_fixed_income_asset(asset: FixedIncomeAssetInput) -> dict[str, object]:
    """Create one contract-based fixed-income position with its principal."""
    try:
        created = session.register_fixed_income_asset(
            ticker=asset.ticker,
            name=asset.name,
            instrument_type=asset.instrument_type,
            indexer_type=asset.indexer_type,
            application_date=asset.application_date,
            principal_amount=asset.principal_amount,
            issuer=asset.issuer,
            contracted_rate=asset.contracted_rate,
            percentage_of_indexer=asset.percentage_of_indexer,
            spread=asset.spread,
            maturity_date=asset.maturity_date,
            liquidity_type=asset.liquidity_type,
            tax_exempt=asset.tax_exempt,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error

    refreshed_references = _refresh_fixed_income_reference_history(
        indexer_type=asset.indexer_type,
        application_date=asset.application_date,
    )
    rebuild_portfolio_dashboard_snapshot()
    return {
        "ticker": str(created.ticker),
        "name": created.name,
        "asset_class": created.asset_class.value,
        "valuation_method": created.valuation_method.value,
        "reference_data_refreshed": refreshed_references,
        "status": "created",
    }


@router.post("/assets/pension-plans", status_code=status.HTTP_201_CREATED)
def create_pension_plan(asset: PensionPlanInput) -> dict[str, object]:
    try:
        created = session.register_pension_plan(**asset.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    rebuild_portfolio_dashboard_snapshot()
    return {"ticker": str(created.ticker), "status": "created"}


@router.put("/pensions/{ticker}/vehicle")
def associate_pension_vehicle(ticker: str, payload: PensionVehicleInput) -> dict[str, object]:
    asset = session._assets.get(ticker.strip().upper())
    details = session._pension_plan_details.get(asset.id) if asset else None
    if asset is None or details is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado.")
    if details.pension_system_type != "OPEN":
        return {"status": "NOT_SUPPORTED"}
    try:
        reference = cvm_pension_data.resolve_vehicle(payload.vehicle_cnpj)
    except PensionMarketDataUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    vehicle = replace(
        reference,
        pension_asset_id=asset.id,
        vehicle_name=payload.vehicle_name or reference.vehicle_name,
        vehicle_type=payload.vehicle_type,
    )
    SqlitePensionInvestmentVehicleRepository(current_portfolio_id()).save(vehicle)
    return {
        "status": "ASSOCIATED",
        "vehicle": {"name": vehicle.vehicle_name, "cnpj": vehicle.vehicle_cnpj},
    }


@router.post("/pensions/{ticker}/vehicle/refresh")
def refresh_pension_vehicle(ticker: str) -> dict[str, object]:
    asset = session._assets.get(ticker.strip().upper())
    details = session._pension_plan_details.get(asset.id) if asset else None
    if asset is None or details is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado.")
    if details.pension_system_type != "OPEN":
        return {"status": "NOT_SUPPORTED"}
    vehicles = SqlitePensionInvestmentVehicleRepository(current_portfolio_id()).list_for(asset.id)
    if not vehicles:
        return {"status": "NO_VEHICLE"}
    vehicle = max(vehicles, key=lambda item: item.valid_from or date.min)
    repository = SqlitePensionFundQuotaRepository()
    previous = repository.list_for(vehicle.id)
    start_date = (
        (previous[-1].reference_date + timedelta(days=1))
        if previous
        else date.today() - timedelta(days=31)
    )
    try:
        quotas = cvm_pension_data.quota_history(vehicle, start_date, date.today())
    except PensionMarketDataUnavailable as error:
        provider_health.failure("CVM Previdência", error)
        return {"status": "SOURCE_ERROR", "detail": str(error)}
    repository.save_all(quotas)
    provider_health.success("CVM Previdência")
    return {"status": "UPDATED", "ingested": len(quotas)}


@router.get("/pensions/{ticker}/fund-return")
def pension_fund_return(
    ticker: str, start_date: date | None = None, end_date: date | None = None
) -> dict[str, object]:
    asset = session._assets.get(ticker.strip().upper())
    details = session._pension_plan_details.get(asset.id) if asset else None
    if asset is None or details is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado.")
    if details.pension_system_type != "OPEN":
        return {"status": "NOT_SUPPORTED"}
    vehicles = SqlitePensionInvestmentVehicleRepository(current_portfolio_id()).list_for(asset.id)
    if not vehicles:
        return {"status": "NO_VEHICLE"}
    vehicle = max(vehicles, key=lambda item: item.valid_from or date.min)
    quotas = SqlitePensionFundQuotaRepository().list_for(vehicle.id)
    if len(quotas) < 2:
        return {"status": "INSUFFICIENT_DATA"}
    requested_start, requested_end = (
        start_date or quotas[0].reference_date,
        end_date or quotas[-1].reference_date,
    )
    available_start = [item for item in quotas if item.reference_date <= requested_start]
    available_end = [item for item in quotas if item.reference_date <= requested_end]
    if not available_start or not available_end:
        return {"status": "INSUFFICIENT_DATA"}
    first, last = available_start[-1], available_end[-1]
    if first.reference_date >= last.reference_date:
        return {"status": "INSUFFICIENT_DATA"}
    return {
        "status": "AVAILABLE",
        "vehicle": {"name": vehicle.vehicle_name, "cnpj": vehicle.vehicle_cnpj},
        "requested_start_date": requested_start,
        "effective_start_date": first.reference_date,
        "requested_end_date": requested_end,
        "effective_end_date": last.reference_date,
        "start_quota": first.quota,
        "end_quota": last.quota,
        "return_rate": last.quota / first.quota - Decimal("1"),
        "source": "CVM",
    }


@router.post("/assets/real-estate", status_code=status.HTTP_201_CREATED)
def create_real_estate(asset: RealEstateInput) -> dict[str, object]:
    try:
        created = session.register_real_estate(**asset.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    rebuild_portfolio_dashboard_snapshot()
    return {"ticker": str(created.ticker), "status": "created"}


@router.post("/recurring-rules", status_code=status.HTTP_201_CREATED)
def create_recurring_rule(input: RecurringRuleInput) -> dict[str, object]:
    asset_id = None
    if input.event_type == "DIVIDEND":
        asset = session._assets.get((input.ticker or "").strip().upper())
        if asset is None:
            raise HTTPException(
                status_code=422, detail="Ativo do provento recorrente não encontrado."
            )
        asset_id = asset.id
    try:
        rule = RecurringRule(
            event_type=FinancialEventType(input.event_type),
            amount=input.amount,
            frequency=input.frequency,
            next_execution_date=input.next_execution_date,
            end_execution_date=input.end_execution_date,
            asset_id=asset_id,
        )
        session.schedule_recurring_rule(rule)
        executed = session.execute_recurring_rules(through=date.today())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    stored_rule = next(item for item in session.recurring_rules() if item.id == rule.id)
    return {
        "id": str(rule.id),
        "next_execution_date": stored_rule.next_execution_date,
        "executed": len(executed),
    }


@router.post("/recurring-rules/execute")
def execute_recurring_rules(through: date | None = None) -> dict[str, object]:
    executed = session.execute_recurring_rules(through=through or date.today())
    return {"executed": len(executed)}


@router.put("/recurring-rules/{rule_id}")
def update_recurring_rule(rule_id: UUID, input: RecurringRuleUpdateInput) -> dict[str, object]:
    try:
        rule = session.update_recurring_rule(
            rule_id,
            amount=input.amount,
            frequency=input.frequency,
            end_execution_date=input.end_execution_date,
        )
        executed = session.execute_recurring_rules(through=date.today())
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    stored_rule = next(item for item in session.recurring_rules() if item.id == rule.id)
    return {
        "id": str(rule.id),
        "next_execution_date": stored_rule.next_execution_date,
        "end_execution_date": stored_rule.end_execution_date,
        "active": stored_rule.active,
        "executed": len(executed),
    }


@router.post("/recurring-rules/{rule_id}/close")
def close_recurring_rule(rule_id: UUID) -> dict[str, object]:
    try:
        rule = session.update_recurring_rule(rule_id, end_execution_date=date.today())
        executed = session.execute_recurring_rules(through=date.today())
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    stored_rule = next(item for item in session.recurring_rules() if item.id == rule.id)
    return {"id": str(rule.id), "active": stored_rule.active, "executed": len(executed)}


@router.delete(
    "/recurring-rules/{rule_id}",
    status_code=status.HTTP_200_OK,
    response_class=Response,
)
def delete_recurring_rule(rule_id: UUID) -> None:
    try:
        session.delete_recurring_rule(rule_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/recurring-rules")
def list_recurring_rules() -> dict[str, object]:
    assets = {asset.id: str(asset.ticker) for asset in session._assets.values()}
    return {
        "rules": [
            {
                "id": str(rule.id),
                "event_type": rule.event_type.value,
                "amount": rule.amount,
                "frequency": rule.frequency.value,
                "next_execution_date": rule.next_execution_date,
                "end_execution_date": rule.end_execution_date,
                "ticker": assets.get(rule.asset_id) if rule.asset_id else None,
                "active": rule.active,
            }
            for rule in session.recurring_rules()
        ]
    }


def serialize_portfolio(
    projection: PortfolioProjection,
    *,
    as_of: date | None = None,
    include_history: bool = True,
) -> dict[str, object]:
    valuation = session.base_currency_valuation(as_of=as_of)
    effective_date = as_of or date.today()
    events = tuple(session.history())
    boundary = PortfolioHistoryBoundary.from_observed_events(events)
    opening_equity_reliable = boundary.has_reliable_opening_equity
    implicit_capital = PerformanceProjector._implicit_capital(events, effective_date).amount
    capital_applied = calculate_capital_applied(
        projection, base_currency=valuation.base_currency
    )
    payload: dict[str, object] = {
        "cash": valuation.cash if opening_equity_reliable else None,
        "confirmed_cash": boundary.opening_cash if opening_equity_reliable else None,
        "cash_status": boundary.opening_cash_status.value,
        "reconstructed_cash_effect": valuation.known_cash,
        "history_boundary": boundary.as_payload(),
        "total_cost": projection.total_cost.amount,
        **capital_applied.as_payload(),
        "realized_result": projection.total_realized_result.amount,
        "income_received": projection.income_received.amount,
        "total_contributions": projection.total_contributions.amount,
        "total_withdrawals": projection.total_withdrawals.amount,
        "net_external_flow": projection.net_external_flow.amount,
        "base_currency": valuation.base_currency,
        "portfolio_equity": (
            valuation.equity + implicit_capital
            if opening_equity_reliable and valuation.equity is not None
            else None
        ),
        "reconstructed_portfolio_equity": valuation.equity,
        "opening_equity_status": boundary.opening_equity_status.value,
        "total_market_value": valuation.market_value,
        "valuation_complete": valuation.complete,
        "unrealized_result": projection.total_unrealized_result.amount,
        "total_result": projection.total_result.amount,
        "positions": [
            {
                "ticker": str(position.asset.ticker),
                "name": position.asset.name,
                "asset_type": position.asset.asset_type.value,
                "asset_class": position.asset.asset_class.value,
                "valuation_method": position.asset.valuation_method.value,
                "quantity": position.quantity.value,
                "cost": position.cost.amount,
                "average_price": position.average_price.amount,
                "realized_result": position.realized_result.amount,
                "current_price": (
                    position.current_price.amount if position.current_price else None
                ),
                "market_value": position.market_value.amount,
                "unrealized_result": position.unrealized_result.amount,
                "unrealized_return_percentage": position.unrealized_return_percentage,
                "income_received": position.income_received.amount,
                "total_result": position.total_result.amount,
                "currency_code": position.asset.currency.code,
                "market_value_base": next(
                    value.market_value_base
                    for value in valuation.positions
                    if value.ticker == str(position.asset.ticker)
                ),
            }
            for position in projection.positions
        ],
    }
    if include_history:
        payload["history"] = [
            {
                "type": event.event_type.value,
                "ticker": str(event.asset.ticker) if event.asset else "",
                "quantity": event.quantity.value if event.quantity else Decimal("0"),
                "unit_price": event.unit_price.amount if event.unit_price else None,
                "total": event.known_total_amount.amount if event.known_total_amount else None,
                "effective_date": event.effective_date,
            }
            for event in session.history()
        ]
    return payload


@router.get("/portfolio")
def get_portfolio(as_of: date | None = None) -> dict[str, object]:
    return serialize_portfolio(session.projection(as_of=as_of), as_of=as_of)


def rebuild_portfolio_dashboard_snapshot() -> dict[str, object]:
    """Build once on writes, then atomically replace the dashboard read model."""
    payload = {
        "read_model_version": PORTFOLIO_DASHBOARD_READ_MODEL_VERSION,
        "portfolio": serialize_portfolio(session.projection(), include_history=False),
        "performance": _portfolio_performance_summary(),
        "holdings": _build_portfolio_holdings(),
        "history": get_portfolio_history(),
        "allocation": get_portfolio_allocation(),
        "class_allocation": get_portfolio_class_allocation(),
    }
    return dashboard_snapshot_repository.save(jsonable_encoder(payload))


def ensure_portfolio_dashboard_snapshot_current() -> dict[str, object]:
    """Rebuild at startup only when the persisted dashboard schema is stale."""
    snapshot = dashboard_snapshot_repository.get()
    if snapshot and snapshot.get("read_model_version") == PORTFOLIO_DASHBOARD_READ_MODEL_VERSION:
        return snapshot
    return rebuild_portfolio_dashboard_snapshot()


def _performance_payload(start_date: date, end_date: date) -> dict[str, object]:
    performance = session.performance(start_date=start_date, end_date=end_date)
    return {
        "requested_start_date": start_date,
        "requested_end_date": end_date,
        "effective_start_date": performance.start_date,
        "effective_end_date": performance.end_date,
        "twr": performance.twr,
        "income": sum(
            (
                event.amount.amount
                for event in session.history()
                if event.event_type
                in {
                    FinancialEventType.DIVIDEND,
                    FinancialEventType.INTEREST_ON_EQUITY,
                    FinancialEventType.FII_INCOME,
                }
                and start_date <= event.effective_date <= performance.end_date
                and event.amount is not None
            ),
            Decimal("0"),
        ),
        "external_inflows": performance.total_contributions.amount,
        "external_outflows": performance.total_withdrawals.amount,
        "status": performance.performance_status,
        "unavailable_reason": performance.unavailable_reason,
    }


def _portfolio_performance_summary() -> dict[str, object]:
    """Persist the global TWR summaries with the dashboard read model."""
    observed_dates = {
        *(event.effective_date for event in session._events),
        *(price.effective_date for price in session._market_prices),
    }
    if len(observed_dates) < 2:
        return {
            "twelve_months": {
                "status": "INSUFFICIENT_DATA",
                "unavailable_reason": "Histórico insuficiente.",
            },
            "total": {
                "status": "INSUFFICIENT_DATA",
                "unavailable_reason": "Histórico insuficiente.",
            },
        }
    start_date, end_date = min(observed_dates), max(observed_dates)
    return {
        "twelve_months": _performance_payload(
            max(start_date, end_date - timedelta(days=365)), end_date
        ),
        "total": _performance_payload(start_date, end_date),
    }


def _dashboard_snapshot_for_request(request: Request | None) -> dict[str, object] | None:
    if request is None:
        return dashboard_snapshot_repository.get()
    portfolio_header = request.headers.get("x-portfolio-id")
    portfolio_id = UUID(portfolio_header) if portfolio_header else MAIN_PORTFOLIO_ID
    return SqlitePortfolioDashboardSnapshotRepository(portfolio_id).get()


@router.get("/portfolio/dashboard")
def get_portfolio_dashboard(request: Request = None) -> dict[str, object]:
    """Fast read path for Minha Carteira; never projects when a snapshot exists."""
    snapshot = _dashboard_snapshot_for_request(request)
    if snapshot is not None:
        return snapshot
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="A visão consolidada ainda está sendo preparada na inicialização.",
    )


@router.post("/portfolio/dashboard/rebuild")
def rebuild_portfolio_dashboard() -> dict[str, object]:
    """Explicit, idempotent recovery path for the persisted read model."""
    try:
        return rebuild_portfolio_dashboard_snapshot()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível reconstruir a visão consolidada da carteira.",
        ) from error


@router.get("/portfolio/holdings")
def get_portfolio_holdings(
    request: Request = None, as_of: date | None = None
) -> dict[str, object]:
    """Read the current holdings projection; historical as-of views remain computed."""
    if as_of is not None:
        return _build_portfolio_holdings(as_of=as_of)
    if not session.persistent:
        return _build_portfolio_holdings()
    snapshot = _dashboard_snapshot_for_request(request)
    holdings = snapshot.get("holdings") if snapshot else None
    if isinstance(holdings, dict):
        return holdings
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="A visão consolidada ainda está sendo preparada na inicialização.",
    )


def _build_portfolio_holdings(as_of: date | None = None) -> dict[str, object]:
    """Build the holdings read model on startup or after a portfolio write."""
    portfolio = session.projection(as_of=as_of)
    valuation = session.base_currency_valuation(as_of=as_of)
    base_values = {item.ticker: item.market_value_base for item in valuation.positions}
    fx_rates = {item.ticker: item.fx_rate for item in valuation.positions}
    latest_quotes = {}
    for quote in sorted(
        session._market_prices,
        key=lambda item: (item.effective_date, item.registered_at, str(item.id)),
    ):
        if as_of is None or quote.effective_date <= as_of:
            latest_quotes[quote.asset.id] = quote
    analysis_by_class = {}
    portfolio_drift = None
    if session.allocation_policy is not None:
        analysis = session.allocation_analysis(as_of=as_of)
        analysis_by_class = {item.asset_class: item for item in analysis.comparisons}
        portfolio_drift = analysis.portfolio_drift
    by_class: dict[AssetClass, list[PositionProjection]] = {}
    for position in portfolio.positions:
        if position.is_empty:
            continue
        by_class.setdefault(position.asset.asset_class, []).append(position)
    labels = {
        AssetClass.BRAZILIAN_STOCK: "Ações Brasil",
        AssetClass.BRAZILIAN_ETF: "ETF Brasil",
        AssetClass.FII: "FIIs",
        AssetClass.FIXED_INCOME: "Renda Fixa",
        AssetClass.PENSION: "Previdência",
        AssetClass.REAL_ESTATE: "Imóveis",
        AssetClass.INTERNATIONAL: "Exterior",
        AssetClass.INTERNATIONAL_ETF: "ETF Internacional",
        AssetClass.US_REIT: "REITs EUA",
        AssetClass.CRYPTO: "Cripto",
        AssetClass.OTHER: "Outros",
    }
    groups = []
    for asset_class, positions in by_class.items():
        strategy = analysis_by_class.get(asset_class)
        values = [base_values.get(str(position.asset.ticker)) for position in positions]
        class_market_value = (
            sum((value for value in values if value is not None), Decimal("0"))
            if all(value is not None for value in values)
            else None
        )
        class_weight = (
            class_market_value / valuation.market_value
            if class_market_value is not None and valuation.market_value not in (None, Decimal("0"))
            else None
        )
        open_ids = {position.asset.id for position in positions}
        open_asset_ids = {str(asset_id) for asset_id in open_ids}
        target_only_assets = tuple(
            asset
            for asset in session._assets.values()
            if asset.asset_class is asset_class
            and asset.id not in open_ids
            and session.asset_allocation_policy
            and session.asset_allocation_policy.target_for(asset) is not None
        )
        composition = AssetCompositionProjector.project(
            tuple(
                AssetCompositionInput(
                    asset_id=str(position.asset.id),
                    label=_fixed_income_contract_label(
                        position.asset, session._fixed_income_details.get(position.asset.id)
                    ),
                    is_open=True,
                    current_value=base_values.get(str(position.asset.ticker)),
                    target_weight=(
                        session.asset_allocation_policy.target_for(position.asset)
                        if session.asset_allocation_policy
                        else None
                    ),
                )
                for position in positions
            )
            + tuple(
                AssetCompositionInput(
                    asset_id=str(asset.id),
                    label=_fixed_income_contract_label(
                        asset, session._fixed_income_details.get(asset.id)
                    ),
                    is_open=False,
                    current_value=None,
                    target_weight=session.asset_allocation_policy.target_for(asset),
                )
                for asset in target_only_assets
            )
        )
        composition_by_id = {item.asset_id: item for item in composition.items}
        group = {
            "asset_class": asset_class.value,
            "label": labels[asset_class],
            "asset_count": len(positions),
            "market_value": class_market_value,
            "total_cost": (
                sum((position.cost.amount for position in positions), Decimal("0"))
                if all(
                    position.asset.currency.code == valuation.base_currency
                    for position in positions
                )
                else None
            ),
            "weight": class_weight,
            # Group headers use the portfolio base currency. Position rows keep
            # their native currency, while their result is converted with the
            # same FX rate applied to the current market value.
            "total_result": (
                sum(
                    (
                        position.total_result.amount * fx_rates[str(position.asset.ticker)]
                        for position in positions
                    ),
                    Decimal("0"),
                )
                if all(
                    fx_rates.get(str(position.asset.ticker)) is not None for position in positions
                )
                else None
            ),
            "target_weight": strategy.target_weight if strategy else None,
            "deviation": strategy.deviation if strategy else None,
            "performance_coverage": _class_performance_coverage(asset_class, as_of),
            "assets": [
                {
                    "asset_id": str(position.asset.id),
                    "ticker": str(position.asset.ticker),
                    "name": position.asset.name,
                    "country": position.asset.country,
                    "sector": position.asset.sector,
                    "currency_code": position.asset.currency.code,
                    "quantity": position.quantity.value,
                    "average_price": position.average_price.amount,
                    "current_price": (
                        position.current_price.amount if position.current_price else None
                    ),
                    "price_as_of": (
                        latest_quotes[position.asset.id].effective_date
                        if position.asset.id in latest_quotes
                        else None
                    ),
                    "price_provider": (
                        latest_quotes[position.asset.id].provider
                        if position.asset.id in latest_quotes
                        else None
                    ),
                    "price_retrieved_at": (
                        latest_quotes[position.asset.id].registered_at
                        if position.asset.id in latest_quotes
                        else None
                    ),
                    "price_timestamp": (
                        latest_quotes[position.asset.id].price_timestamp
                        if position.asset.id in latest_quotes
                        else None
                    ),
                    "market_value": (
                        position.market_value.amount if position.current_price else None
                    ),
                    "total_result": position.total_result.amount,
                    "return_percentage": position.unrealized_return_percentage,
                    "income_received": position.income_received.amount,
                    "market_value_base": base_values.get(str(position.asset.ticker)),
                    "portfolio_weight": (
                        (base_values[str(position.asset.ticker)] or Decimal("0"))
                        / valuation.market_value
                        if base_values.get(str(position.asset.ticker)) is not None
                        and valuation.market_value not in (None, Decimal("0"))
                        else None
                    ),
                    "class_weight": (
                        (base_values[str(position.asset.ticker)] or Decimal("0"))
                        / class_market_value
                        if base_values.get(str(position.asset.ticker)) is not None
                        and class_market_value
                        else None
                    ),
                    "target_weight": (
                        session.asset_allocation_policy.target_for(position.asset)
                        if session.asset_allocation_policy
                        else None
                    ),
                    "instrument": _fixed_income_instrument_label(
                        session._fixed_income_details[position.asset.id]
                    )
                    if position.asset.id in session._fixed_income_details
                    else None,
                    "indexer": (
                        _fixed_income_indexer_label(
                            session._fixed_income_details[position.asset.id]
                        )
                        if position.asset.id in session._fixed_income_details
                        else None
                    ),
                    "condition": _fixed_income_condition(
                        session._fixed_income_details.get(position.asset.id)
                    ),
                    "contract_key": _fixed_income_contract_key(
                        position.asset,
                        session._fixed_income_details.get(position.asset.id),
                    ),
                    "contract_label": _fixed_income_contract_label(
                        position.asset,
                        session._fixed_income_details.get(position.asset.id),
                    ),
                }
                for position in sorted(
                    positions, key=lambda item: item.market_value.amount, reverse=True
                )
            ],
        }
        for asset_row in group["assets"]:
            item = composition_by_id[asset_row["asset_id"]]
            asset_row.update(
                {
                    "display_label": item.label,
                    "current_weight_in_class": item.current_weight,
                    "gap_pp": item.gap_pp,
                    "target_weight_total_portfolio": (
                        strategy.target_weight * item.target_weight
                        if strategy and item.target_weight is not None
                        else None
                    ),
                }
            )
        group["assets"].extend(
            {
                "asset_id": item.asset_id,
                "ticker": item.label,
                "name": item.label,
                "display_label": item.label,
                "current_value": item.current_value,
                "market_value_base": item.current_value,
                "current_weight_in_class": item.current_weight,
                "class_weight": item.current_weight,
                "target_weight": item.target_weight,
                "gap_pp": item.gap_pp,
                "target_weight_total_portfolio": (
                    strategy.target_weight * item.target_weight
                    if strategy and item.target_weight is not None
                    else None
                ),
                "target_only": True,
            }
            for item in composition.items
            if item.asset_id not in open_asset_ids
        )
        group["composition_distance"] = composition.distance
        group["valuation_quality"] = composition.valuation_quality
        group["valuation_unavailable_reason"] = composition.unavailable_reason
        groups.append(group)
    groups.sort(key=lambda item: item["market_value"] or Decimal("0"), reverse=True)
    return {
        "base_currency": valuation.base_currency,
        "portfolio_equity": valuation.equity,
        "portfolio_market_value": valuation.market_value,
        "total_cost": portfolio.total_cost.amount,
        "total_result": portfolio.total_result.amount,
        "income_received": portfolio.income_received.amount,
        "valuation_complete": valuation.complete,
        "portfolio_drift": portfolio_drift,
        "classes": groups,
    }


@router.get("/portfolio/assets/{asset_id}/transactions")
def get_asset_transactions(
    asset_id: UUID,
    page: int = 1,
    page_size: int = 10,
    sort: Literal["effective_date_desc"] = "effective_date_desc",
    group: Literal["MOVEMENT", "INCOME"] | None = None,
) -> dict[str, object]:
    """Return one asset's persisted write-model events without rebuilding a snapshot."""
    if page < 1 or not 1 <= page_size <= 100:
        raise HTTPException(status_code=422, detail="Paginação inválida.")

    events = [event for event in session.history() if event.asset and event.asset.id == asset_id]
    if not events:
        known_asset = any(asset.id == asset_id for asset in session._assets.values())
        if not known_asset:
            raise HTTPException(status_code=404, detail="Ativo não encontrado.")

    movement_types = {FinancialEventType.BUY, FinancialEventType.SELL}
    income_types = {
        FinancialEventType.DIVIDEND,
        FinancialEventType.INTEREST_ON_EQUITY,
        FinancialEventType.FII_INCOME,
    }
    movement_count = sum(event.event_type in movement_types for event in events)
    income_count = sum(event.event_type in income_types for event in events)
    if group == "MOVEMENT":
        events = [event for event in events if event.event_type in movement_types]
    elif group == "INCOME":
        events = [event for event in events if event.event_type in income_types]
    events.sort(
        key=lambda event: (event.effective_date, event.registered_at, str(event.id)),
        reverse=True,
    )
    total = len(events)
    start = (page - 1) * page_size
    items = [_serialize_asset_transaction(event) for event in events[start : start + page_size]]
    total_pages = (total + page_size - 1) // page_size
    return {
        "asset_id": str(asset_id),
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "movement_count": movement_count,
        "income_count": income_count,
        "total_pages": total_pages,
        "has_previous": page > 1,
        "has_next": start + page_size < total,
        "sort": sort,
    }


def _serialize_asset_transaction(event: FinancialEvent) -> dict[str, object]:
    """Serialize the stored event facts; no presentation defaults are invented."""
    asset = event.asset
    assert asset is not None
    source = event.metadata.get("source")
    amount = event.amount.amount if event.amount else None
    if amount is None and event.quantity is not None and event.unit_price is not None:
        amount = event.quantity.value * event.unit_price.amount
    return {
        "id": str(event.id),
        "asset_id": str(asset.id),
        "event_type": event.event_type.value,
        "operation": _operation_label(event.event_type),
        "effective_date": event.effective_date,
        "quantity": event.quantity.value if event.quantity else None,
        "unit_price": event.unit_price.amount if event.unit_price else None,
        "amount": amount,
        "currency_code": asset.currency.code,
        "source": str(source) if source else None,
    }


def _class_performance_coverage(
    asset_class: AssetClass, end_date: date | None = None
) -> dict[str, object]:
    """Report class history availability without mistaking trades for flows.

    BUY/SELL are internal portfolio activity; only deposits and withdrawals
    define external-capital boundaries. Legacy UNKNOWN trade metadata is safe.
    """
    relevant = [
        event
        for event in session.history()
        if event.asset is not None and event.asset.asset_class is asset_class
    ]
    first_event_date = min((event.effective_date for event in relevant), default=None)
    effective_end_date = end_date or date.today()
    if first_event_date is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "performance_coverage_start_date": None,
            "twr": None,
            "coverage_ratio": None,
            "unavailable_reason": "Não há operações registradas para esta classe.",
        }

    start_date = max(first_event_date, effective_end_date - timedelta(days=365))
    performance = session.performance(
        start_date=start_date, end_date=effective_end_date, asset_class=asset_class
    )
    return {
        "status": performance.performance_status,
        "performance_coverage_start_date": start_date,
        "performance_coverage_end_date": effective_end_date,
        "twr": performance.twr,
        "coverage_ratio": performance.coverage_ratio,
        "unavailable_reason": performance.unavailable_reason,
        "missing_assets": performance.missing_assets,
        "missing_periods": performance.missing_periods,
    }


@router.get("/operations")
def get_operations() -> dict[str, object]:
    events = sorted(
        session.history(),
        key=lambda event: (event.effective_date, event.registered_at, str(event.id)),
        reverse=True,
    )
    return {
        "operations": [
            {
                "id": str(event.id),
                "effective_date": event.effective_date,
                "type": event.event_type.value,
                "ticker": str(event.asset.ticker) if event.asset else None,
                "quantity": event.quantity.value if event.quantity else None,
                "unit_price": event.unit_price.amount if event.unit_price else None,
                "amount": event.known_total_amount.amount if event.known_total_amount else None,
                "currency_code": event.asset.currency.code if event.asset else "BRL",
            }
            for event in events
        ]
    }


@router.get("/operations/history")
def get_operations_history(
    start_date: date | None = None,
    end_date: date | None = None,
    asset_class: str | None = None,
    movement_type: Literal["ASSET_OPERATION", "CONTRIBUTION", "INCOME", "WITHDRAWAL", "MOVEMENTS"]
    | None = None,
    event_type: str | None = None,
    group_by: Literal["ASSET", "DATE", "TYPE"] = "ASSET",
    group_key: str | None = None,
    offset: int = 0,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict[str, object]:
    """Return the realized-event audit trail with explicit, independent cursors."""
    if page < 1 or offset < 0 or not 1 <= page_size <= 100:
        raise HTTPException(status_code=422, detail="Paginação inválida.")
    query = (search or "").strip().casefold()
    available_group_metadata: dict[str, tuple[str, str]] = {}
    selected: list[tuple[FinancialEvent, dict[str, object], str, str, str]] = []
    ordered_events = sorted(
        session.history(),
        key=lambda item: (item.effective_date, item.registered_at, str(item.id)),
        reverse=True,
    )
    for event in ordered_events:
        group_key_legacy, group_label, group_kind, event_movement = _operation_group(event)
        asset = event.asset
        if group_kind == "income" and asset is not None:
            available_group_metadata[asset.asset_class.value] = (
                asset.asset_class.value.replace("_", " ").title(),
                "asset",
            )
        elif group_kind != "cash":
            available_group_metadata[group_key_legacy] = (group_label, group_kind)
        searchable = " ".join(
            value
            for value in (
                str(asset.ticker) if asset else "",
                asset.name if asset else "",
                event.description or "",
            )
            if value
        ).casefold()
        if start_date and event.effective_date < start_date:
            continue
        if end_date and event.effective_date > end_date:
            continue
        if asset_class and (
            asset.asset_class.value != asset_class
            if event_movement == "INCOME" and asset is not None
            else asset_class != group_key_legacy
        ):
            continue
        if movement_type == "MOVEMENTS" and event_movement == "INCOME":
            continue
        if movement_type and movement_type != "MOVEMENTS" and movement_type != event_movement:
            continue
        if event_type and event.event_type.value != event_type:
            continue
        if query and query not in searchable:
            continue
        type_key = event.event_type.value
        if group_by == "TYPE" and group_key and type_key != group_key:
            continue
        fixed_income = session._fixed_income_details.get(asset.id) if asset else None
        item = {
            "id": str(event.id),
            "effective_date": event.effective_date,
            "registered_at": event.registered_at,
            "event_type": type_key,
            "operation": _operation_label(event.event_type),
            "ticker": str(asset.ticker) if asset else None,
            "asset_name": asset.name if asset else None,
            "asset_type": asset.asset_type.value if asset else None,
            "asset_class": asset.asset_class.value if asset else None,
            "quantity": event.quantity.value if event.quantity else None,
            "unit_price": event.unit_price.amount if event.unit_price else None,
            "amount": event.known_total_amount.amount if event.known_total_amount else None,
            "currency_code": asset.currency.code if asset else "BRL",
            "description": event.description,
            "source": "Manual",
            "movement_type": event_movement,
            "condition": _fixed_income_condition(fixed_income),
            "instrument": (_fixed_income_instrument_label(fixed_income) if fixed_income else None),
            "indexer": (_fixed_income_indexer_label(fixed_income) if fixed_income else None),
            "contract_key": _fixed_income_contract_key(asset, fixed_income),
            "contract_label": _fixed_income_contract_label(asset, fixed_income),
            "maturity_date": fixed_income.maturity_date if fixed_income else None,
        }
        selected.append((event, item, group_key_legacy, group_label, group_kind))

    if group_by == "DATE":
        cursor = offset if offset else (page - 1) * page_size
        page_items = selected[cursor : cursor + page_size]
        total = len(selected)
        groups = [
            {
                "key": "TIMELINE",
                "label": "Todos os lançamentos",
                "kind": "timeline",
                "event_count": total,
                "total": total,
                "moved_amount": None,
                "events": [row[1] for row in page_items],
                "has_more": cursor + len(page_items) < total,
                "next_cursor": cursor + len(page_items)
                if cursor + len(page_items) < total
                else None,
            }
        ]
        total_count = total
    elif group_by == "TYPE":
        by_type: dict[str, list[tuple[FinancialEvent, dict[str, object], str, str, str]]] = {}
        for row in selected:
            by_type.setdefault(row[1]["event_type"], []).append(row)
        groups = []
        for key, rows in by_type.items():
            cursor = offset if group_key == key else 0
            page_rows = rows[cursor : cursor + page_size]
            amounts = [
                row[0].known_total_amount.amount
                for row in rows
                if row[0].known_total_amount is not None
            ]
            amount_total = (
                sum(amounts, Decimal("0")) if amounts and len(amounts) == len(rows) else None
            )
            has_more = cursor + len(page_rows) < len(rows)
            groups.append(
                {
                    "key": key,
                    "label": _operation_group_type_label(key),
                    "kind": "event_type",
                    "event_count": len(rows),
                    "total": len(rows),
                    "moved_amount": amount_total,
                    "events": [row[1] for row in page_rows],
                    "has_more": has_more,
                    "next_cursor": cursor + len(page_rows) if has_more else None,
                }
            )
        total_count = sum(len(rows) for rows in by_type.values())
    else:
        grouped: dict[str, list[dict[str, object]]] = {}
        group_totals: dict[str, Decimal] = {}
        group_metadata: dict[str, tuple[str, str]] = {}
        visible_count = page * page_size
        for event, item, key, label, kind in selected:
            grouped.setdefault(key, []).append(item)
            if event.known_total_amount is not None:
                group_totals[key] = (
                    group_totals.get(key, Decimal("0")) + event.known_total_amount.amount
                )
            group_metadata[key] = (label, kind)
        groups = []
        for key, events in grouped.items():
            label, kind = group_metadata[key]
            groups.append(
                {
                    "key": key,
                    "label": label,
                    "kind": kind,
                    "event_count": len(events),
                    "total": len(events),
                    "moved_amount": group_totals.get(key),
                    "events": events[:visible_count],
                    "has_more": len(events) > visible_count,
                    "next_cursor": visible_count if len(events) > visible_count else None,
                }
            )
        total_count = len(selected)
    return {
        "groups": groups,
        "page": page,
        "offset": offset,
        "page_size": page_size,
        "total_count": total_count,
        "available_classes": [
            {"key": key, "label": label}
            for key, (label, _) in sorted(
                available_group_metadata.items(), key=lambda item: item[1][0]
            )
        ],
    }


def _operation_group_type_label(event_type: str) -> str:
    labels = {
        "BUY": "Compras",
        "SELL": "Vendas",
        "DEPOSIT": "Aportes",
        "WITHDRAWAL": "Retiradas",
        "DIVIDEND": "Dividendos",
        "INTEREST_ON_EQUITY": "JCP",
        "FII_INCOME": "Rendimentos de FII",
        "FIXED_INCOME_INTEREST": "Juros de renda fixa",
        "APPLICATION": "Aplicações",
        "REDEMPTION": "Resgates",
        "SPLIT": "Desdobramentos",
        "REVERSE_SPLIT": "Grupamentos",
        "BONUS_SHARE": "Bonificações",
        "SUBSCRIPTION": "Subscrições",
        "BROKERAGE_FEE": "Corretagem",
        "TAX": "Impostos",
        "FX_EXCHANGE": "Câmbio",
        "STAKING_REWARD": "Recompensas de staking",
    }
    return labels.get(event_type, event_type.replace("_", " ").title())


def _operation_group(event: FinancialEvent) -> tuple[str, str, str, str]:
    if event.event_type is FinancialEventType.DEPOSIT:
        return "CONTRIBUTIONS", "Aportes", "cash", "CONTRIBUTION"
    if event.event_type is FinancialEventType.WITHDRAWAL:
        return "WITHDRAWALS", "Retiradas", "cash", "WITHDRAWAL"
    if event.event_type in {
        FinancialEventType.DIVIDEND,
        FinancialEventType.INTEREST_ON_EQUITY,
        FinancialEventType.FII_INCOME,
        FinancialEventType.FIXED_INCOME_INTEREST,
    }:
        return "INCOME", "Proventos", "income", "INCOME"
    asset = event.asset
    if asset is None:
        return "OTHER", "Outros", "cash", "ASSET_OPERATION"
    if asset.asset_type is AssetType.PENSION:
        return "PENSION", "Previdência", "pension", "ASSET_OPERATION"
    if asset.asset_type is AssetType.REAL_ESTATE:
        return "REAL_ESTATE", "Imóveis", "real_estate", "ASSET_OPERATION"
    labels = {
        AssetClass.BRAZILIAN_STOCK: "Ações",
        AssetClass.BRAZILIAN_ETF: "ETF Brasil",
        AssetClass.FII: "FIIs",
        AssetClass.FIXED_INCOME: "Renda Fixa",
        AssetClass.PENSION: "Previdência",
        AssetClass.REAL_ESTATE: "Imóveis",
        AssetClass.INTERNATIONAL: "Exterior",
        AssetClass.INTERNATIONAL_ETF: "ETF Internacional",
        AssetClass.US_REIT: "REITs EUA",
        AssetClass.CRYPTO: "Cripto",
        AssetClass.CASH: "Caixa",
        AssetClass.OTHER: "Outros",
    }
    kind = "fixed_income" if asset.asset_class is AssetClass.FIXED_INCOME else "asset"
    return asset.asset_class.value, labels[asset.asset_class], kind, "ASSET_OPERATION"


def _fixed_income_condition(details: FixedIncomeDetails | None) -> str | None:
    if details is None:
        return None
    if details.indexer_type is FixedIncomeIndexerType.CDI_PLUS:
        percentage = details.percentage_of_indexer or Decimal("100")
        return f"{percentage}% do CDI + {details.spread}%"
    if details.indexer_type is FixedIncomeIndexerType.IPCA_PLUS:
        return f"IPCA + {details.spread}%"
    if details.contracted_rate is not None:
        return f"{details.contracted_rate}% a.a."
    if details.percentage_of_indexer is not None:
        return f"{details.percentage_of_indexer}% do CDI"
    if details.spread is not None:
        return f"{details.indexer_type.value} + {details.spread}%"
    return details.indexer_type.value


def _fixed_income_instrument_label(details: FixedIncomeDetails) -> str:
    return {
        FixedIncomeInstrumentType.TESOURO_DIRETO: "Tesouro Direto",
        FixedIncomeInstrumentType.SAVINGS_ACCOUNT: "Poupança",
    }.get(details.instrument_type, details.instrument_type.value)


def _fixed_income_indexer_label(details: FixedIncomeDetails) -> str:
    return {
        FixedIncomeIndexerType.PREFIXED: "Prefixado",
        FixedIncomeIndexerType.CDI_PERCENT: "CDI",
        FixedIncomeIndexerType.CDI_PLUS: "CDI + spread",
        FixedIncomeIndexerType.IPCA_PLUS: "IPCA + spread",
        FixedIncomeIndexerType.SELIC: "Selic",
        FixedIncomeIndexerType.SAVINGS_RULE: "Regra da poupança",
        FixedIncomeIndexerType.OTHER: "Outro indexador",
    }[details.indexer_type]


def _fixed_income_contract_key(
    asset: Asset | None, details: FixedIncomeDetails | None
) -> str | None:
    if asset is None or details is None:
        return None
    return "|".join(
        (
            asset.name.casefold().strip(),
            details.instrument_type.value,
            details.indexer_type.value,
            str(details.contracted_rate or ""),
            str(details.percentage_of_indexer or ""),
            str(details.spread or ""),
        )
    )


def _fixed_income_contract_label(
    asset: Asset | None, details: FixedIncomeDetails | None
) -> str | None:
    if asset is None or details is None:
        return asset.name if asset else None
    return " · ".join(
        (
            asset.name,
            _fixed_income_instrument_label(details),
            _fixed_income_indexer_label(details),
            _fixed_income_condition(details) or "",
        )
    )


def _operation_label(event_type: FinancialEventType) -> str:
    labels = {
        FinancialEventType.BUY: "Compra",
        FinancialEventType.SELL: "Venda",
        FinancialEventType.DIVIDEND: "Dividendo",
        FinancialEventType.INTEREST_ON_EQUITY: "JCP",
        FinancialEventType.FII_INCOME: "Rendimento",
        FinancialEventType.DEPOSIT: "Aporte",
        FinancialEventType.WITHDRAWAL: "Retirada",
        FinancialEventType.APPLICATION: "Aplicação",
        FinancialEventType.REDEMPTION: "Resgate",
        FinancialEventType.FIXED_INCOME_INTEREST: "Juros",
        FinancialEventType.STAKING_REWARD: "Recompensa de staking",
    }
    return labels.get(event_type, event_type.value.replace("_", " ").title())


@router.delete(
    "/operations/{event_id}",
    status_code=status.HTTP_200_OK,
    response_class=Response,
)
def delete_operation(event_id: str) -> None:
    try:
        session.delete_event(event_id)
        rebuild_portfolio_dashboard_snapshot()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/portfolio/configuration")
def get_portfolio_configuration() -> dict[str, str]:
    return {"portfolio_base_currency": session.base_currency}


@router.put("/portfolio/configuration")
def update_portfolio_configuration(
    configuration: PortfolioConfigurationInput,
) -> dict[str, str]:
    try:
        currency = session.set_base_currency(configuration.portfolio_base_currency)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {"portfolio_base_currency": currency}


def _paid_income_settings_view(settings: PaidIncomeSettings) -> dict[str, object]:
    return {
        "provider": "BRAPI",
        "enabled": settings.enabled,
        "token_configured": bool(settings.api_token),
        "status": settings.status,
        "last_sync_at": settings.last_sync_at,
        "last_result": settings.last_result,
    }


@router.get("/settings/paid-income")
def get_paid_income_settings() -> dict[str, object]:
    return _paid_income_settings_view(paid_income_settings.get())


@router.put("/settings/paid-income")
def update_paid_income_settings(input: PaidIncomeSettingsInput) -> dict[str, object]:
    current = paid_income_settings.get()
    token = (
        None
        if input.remove_token
        else (input.api_token if input.api_token is not None else current.api_token)
    )
    updated = PaidIncomeSettings(
        enabled=input.enabled,
        api_token=token,
        last_sync_at=current.last_sync_at,
        last_result=current.last_result,
    )
    paid_income_settings.save(updated)
    return _paid_income_settings_view(updated)


@router.post("/settings/paid-income/test")
def test_paid_income_connection() -> dict[str, object]:
    settings = paid_income_settings.get()
    if not settings.api_token:
        return {"status": PaidIncomeIntegrationStatus.TOKEN_MISSING}
    response = BrapiPaidIncomeProvider(settings.api_token).get_paid_income(
        "TASA4", date.today() - timedelta(days=30), date.today()
    )
    return {"status": response.status}


@router.post("/settings/paid-income/sync")
def sync_paid_income() -> dict[str, object]:
    settings = paid_income_settings.get()
    if not settings.enabled or not settings.api_token:
        return {
            "status": settings.status,
            "consulted": 0,
            "found": 0,
            "imported": 0,
        }
    service = PaidIncomeSyncService(
        paid_income_settings, SqliteImportedPaidIncomeRepository(current_portfolio_id())
    )
    return service.sync(session, BrapiPaidIncomeProvider(settings.api_token))


@router.post("/fx/{base_currency}/{quote_currency}/refresh")
def refresh_fx_rate(
    base_currency: str, quote_currency: str, effective_date: date
) -> dict[str, object]:
    try:
        rate = session.refresh_fx_rate(
            fx_data,
            base_currency=base_currency,
            quote_currency=quote_currency,
            effective_date=effective_date,
        )
    except FxRateUnavailable as error:
        provider_health.failure("BCB PTAX", error)
        raise HTTPException(status_code=503, detail=str(error)) from error
    provider_health.success("BCB PTAX")
    return {
        "base_currency": rate.base_currency,
        "quote_currency": rate.quote_currency,
        "rate": rate.rate,
        "effective_date": rate.effective_date,
        "source": rate.source,
    }


@router.post("/trades", status_code=status.HTTP_201_CREATED)
def create_trade(trade: TradeInput) -> dict[str, object]:
    try:
        projection = session.register_trade(
            event_type=FinancialEventType(trade.event_type),
            ticker=trade.ticker,
            name=trade.name,
            asset_class=trade.asset_class,
            country=trade.country,
            currency_code=trade.currency_code,
            sector=trade.sector,
            quantity=trade.quantity,
            unit_price=trade.unit_price,
            effective_date=trade.effective_date,
            capital_flow_type=trade.capital_flow_type,
            source_asset_class=trade.source_asset_class,
            destination_asset_class=trade.destination_asset_class,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    rebuild_portfolio_dashboard_snapshot()
    return serialize_portfolio(projection)


@router.post("/fixed-income/sales", status_code=status.HTTP_201_CREATED)
def create_fixed_income_sale(sale: FixedIncomeSaleInput) -> dict[str, object]:
    """Sell an existing fixed-income position for its total cash proceeds."""
    ticker = sale.ticker.strip().upper()
    asset = session._assets.get(ticker)
    if asset is None or asset.asset_class is not AssetClass.FIXED_INCOME:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selecione um ativo de Renda Fixa existente na carteira.",
        )

    position = next(
        (
            item
            for item in session.project(as_of=sale.effective_date).positions
            if item.asset.id == asset.id and not item.is_empty
        ),
        None,
    )
    if position is None or position.current_price is None or position.market_value.is_zero:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Este ativo não possui saldo aberto e valorizado na data informada.",
        )

    if sale.amount > position.market_value.amount:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O valor da venda não pode ser maior que o saldo atual da posição.",
        )

    # Fixed-income contracts are represented as one application unit whose
    # quote is the full current balance. Convert the requested BRL redemption
    # into the proportional quantity so a partial sale leaves the remainder
    # invested instead of selling the whole application one-for-one.
    sale_quantity = sale.amount / position.current_price.amount

    try:
        projection = session.register_trade(
            event_type=FinancialEventType.SELL,
            ticker=ticker,
            name=asset.name,
            asset_class=AssetClass.FIXED_INCOME,
            country=asset.country,
            currency_code=asset.currency.code,
            quantity=sale_quantity,
            unit_price=position.current_price.amount,
            effective_date=sale.effective_date,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    rebuild_portfolio_dashboard_snapshot()
    return serialize_portfolio(projection)


def _irpf_brazilian_stocks_import(
    payload: IrpfBrazilianStocksImportInput,
) -> tuple[IrpfBrazilianStockPosition, ...]:
    try:
        workbook = b64decode(payload.workbook_base64, validate=True)
    except Base64Error as error:
        raise HTTPException(status_code=422, detail="Arquivo de importação inválido.") from error
    if len(workbook) > 10_000_000:
        raise HTTPException(status_code=422, detail="A planilha deve ter no máximo 10 MB.")
    try:
        return parse_irpf_brazilian_stocks(workbook)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _serialize_irpf_brazilian_stock(position: IrpfBrazilianStockPosition) -> dict[str, object]:
    return {
        "ticker": position.ticker,
        "name": position.name,
        "quantity": position.quantity,
        "total_cost": position.total_cost,
        "unit_price": position.unit_price,
        "effective_date": date(2025, 12, 31),
    }


@router.post("/imports/irpf/brazilian-stocks/preview")
def preview_irpf_brazilian_stocks_import(
    payload: IrpfBrazilianStocksImportInput,
) -> dict[str, object]:
    """Preview only the Brazilian stock positions in an Investidor10 IRPF report."""
    positions = _irpf_brazilian_stocks_import(payload)
    return {
        "effective_date": date(2025, 12, 31),
        "asset_class": AssetClass.BRAZILIAN_STOCK,
        "items": [_serialize_irpf_brazilian_stock(position) for position in positions],
        "total_cost": sum((position.total_cost for position in positions), Decimal("0")),
    }


@router.post("/imports/irpf/brazilian-stocks", status_code=status.HTTP_201_CREATED)
def import_irpf_brazilian_stocks(
    payload: IrpfBrazilianStocksImportInput,
) -> dict[str, object]:
    """Create one consolidated BUY per Brazilian stock after an explicit preview."""
    positions = _irpf_brazilian_stocks_import(payload)
    existing = [position for position in session.projection().positions if not position.is_empty]
    if existing:
        raise HTTPException(
            status_code=409,
            detail="O piloto IRPF exige carteira vazia para evitar posições duplicadas.",
        )
    for position in positions:
        session.register_trade(
            event_type=FinancialEventType.BUY,
            ticker=position.ticker,
            name=position.name,
            asset_class=AssetClass.BRAZILIAN_STOCK,
            country="BR",
            currency_code="BRL",
            quantity=position.quantity,
            unit_price=position.unit_price,
            effective_date=date(2025, 12, 31),
            capital_flow_type=CapitalFlowType.EXTERNAL_CAPITAL,
            destination_asset_class=AssetClass.BRAZILIAN_STOCK,
        )
    rebuild_portfolio_dashboard_snapshot()
    return {
        "imported": len(positions),
        "effective_date": date(2025, 12, 31),
        "total_cost": sum((position.total_cost for position in positions), Decimal("0")),
        "asset_class": AssetClass.BRAZILIAN_STOCK,
    }


def _decode_b3_workbook(payload: B3ImportPreviewInput) -> bytes:
    try:
        workbook = b64decode(payload.workbook_base64, validate=True)
    except Base64Error as error:
        raise HTTPException(status_code=422, detail="Arquivo B3 inválido.") from error
    if len(workbook) > 12_000_000:
        raise HTTPException(status_code=422, detail="A planilha deve ter no máximo 12 MB.")
    return workbook


def _serialize_b3_batch(batch: object, records: tuple[object, ...]) -> dict[str, object]:
    return {
        "batch_id": str(batch.id),
        "status": batch.status.value,
        "file_name": batch.file_name,
        "report_type": batch.report_type.value,
        "counts": {
            "total": batch.total_rows,
            "new": batch.new_rows,
            "duplicate": batch.duplicate_rows,
            "review_required": batch.review_rows,
            "unsupported": batch.unsupported_rows,
            "invalid": batch.invalid_rows,
        },
        "items": [
            {
                "source_row": item.source_row,
                "status": item.status.value,
                "reason_code": item.detail,
                "event_date": item.event_date,
                "event_type": item.event_type,
                "income_type": item.income_type,
                "source_symbol": item.source_symbol,
                "normalized_symbol": item.normalized_symbol,
                "institution": item.institution,
                "market": item.market,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_value": item.total_value,
                "quantity_status": item.quantity_status,
                "financial_status": item.financial_status,
                "occurrence_index": item.occurrence_index,
            }
            for item in records
        ],
    }


def _resolve_b3_assets(rows: tuple[object, ...]) -> None:
    """Resolve missing B3 symbols from the authoritative discovery provider.

    This registers only verified master data.  Financial events remain exclusive
    to the explicit ``apply`` step.
    """
    rows_by_symbol: dict[str, list[object]] = {}
    for row in rows:
        if row.normalized_symbol:
            rows_by_symbol.setdefault(row.normalized_symbol, []).append(row)
    for symbol, source_rows in sorted(rows_by_symbol.items()):
        if symbol in session._assets:
            continue
        try:
            candidates = asset_discovery.search(symbol, limit=8)
        except AssetDiscoveryUnavailable:
            candidates = ()
        candidate = next(
            (
                item
                for item in candidates
                if item.symbol == symbol
                and item.suggested_asset_class is not None
                and item.country == "BR"
                and item.currency_code == "BRL"
            ),
            None,
        )
        if candidate is not None:
            session.register_asset(
                ticker=candidate.symbol,
                name=candidate.name,
                asset_class=candidate.suggested_asset_class,
                country=candidate.country,
                currency_code=candidate.currency_code,
                sector=candidate.sector,
            )
            continue
        # The official B3 movement type is itself authoritative registry
        # evidence.  It lets historical income retain its asset identity when
        # the optional public catalogue is offline, without guessing from the
        # ticker text or requiring a current position.
        asset_class = (
            AssetClass.FII
            if any(row.income_type == "INCOME" for row in source_rows)
            else AssetClass.BRAZILIAN_STOCK
        )
        session.register_asset(
            ticker=symbol,
            name=symbol,
            asset_class=asset_class,
            country="BR",
            currency_code="BRL",
        )


@router.get("/imports/b3/history")
def list_b3_import_history(offset: int = 0, page_size: int = 20) -> dict[str, object]:
    """List persisted B3 import batches for the import audit history."""
    if offset < 0 or not 1 <= page_size <= 100:
        raise HTTPException(status_code=422, detail="Paginação inválida.")
    batches, total = SqliteB3ImportRepository(current_portfolio_id()).list_batches(
        offset=offset, limit=page_size
    )
    next_cursor = offset + len(batches) if offset + len(batches) < total else None
    return {
        "items": [
            {
                "id": str(batch.id),
                "file_name": batch.file_name,
                "report_type": batch.report_type.value,
                "total_rows": batch.total_rows,
                "new_rows": batch.new_rows,
                "duplicate_rows": batch.duplicate_rows,
                "review_rows": batch.review_rows,
                "unsupported_rows": batch.unsupported_rows,
                "invalid_rows": batch.invalid_rows,
                "status": batch.status.value,
                "created_at": batch.created_at,
                "completed_at": batch.completed_at,
            }
            for batch in batches
        ],
        "total": total,
        "has_more": next_cursor is not None,
        "next_cursor": next_cursor,
    }


@router.post("/imports/b3/preview")
@b3_import_router.post("/imports/b3/preview")
def preview_b3_import(payload: B3ImportPreviewInput) -> dict[str, object]:
    """Persist a reviewable B3 preview; no financial event is created here."""
    workbook = _decode_b3_workbook(payload)
    report_type = (
        B3ImportReportType(payload.report_type)
        if payload.report_type
        else (
            B3ImportReportType.NEGOTIATION
            if "negocia" in payload.file_name.casefold()
            else B3ImportReportType.MOVEMENT
        )
    )
    parser = (
        B3NegotiationReportParser()
        if report_type is B3ImportReportType.NEGOTIATION
        else B3MovementReportParser()
    )
    try:
        rows = parser.parse(workbook)
    except B3LayoutError as error:
        raise HTTPException(
            status_code=422, detail={"code": error.code, "message": str(error)}
        ) from error
    batch, records = B3ImportService(
        SqliteB3ImportRepository(current_portfolio_id()), session._assets, session._events
    ).preview(
        workbook=workbook,
        file_name=payload.file_name,
        report_type=report_type,
        rows=rows,
        persist=False,
    )
    _b3_preview_cache[(current_portfolio_id(), batch.id)] = (batch, records)
    return _serialize_b3_batch(batch, records)


@router.post("/imports/b3/{batch_id}/apply")
@b3_import_router.post("/imports/b3/{batch_id}/apply")
def apply_b3_import(batch_id: UUID) -> dict[str, object]:
    """Apply only previewed, resolved rows in chronological source order atomically."""
    repository = SqliteB3ImportRepository(current_portfolio_id())
    batch = repository.get_batch(batch_id)
    cached = _b3_preview_cache.pop((current_portfolio_id(), batch_id), None)
    if batch is None and cached is not None:
        batch, records = cached
        repository.create_batch(batch)
        for record in records:
            if record.status is not B3ImportedRecordStatus.DUPLICATE:
                repository.save_record(record)
    if batch is None:
        raise HTTPException(status_code=404, detail="Lote de importação B3 não encontrado.")
    applied = 0

    def operation(db: object, audit: object) -> None:
        nonlocal applied
        records = sorted(
            repository.list_records(batch_id),
            key=lambda row: (row.event_date or date.min, row.source_row),
        )
        for record in records:
            if record.status is not B3ImportedRecordStatus.NEW:
                continue
            # Recheck just before persistence; a concurrent/overlapping import wins safely.
            existing = repository.get_record_by_identity(
                record.fingerprint, record.occurrence_index
            )
            if existing is not None and existing.id != record.id:
                continue
            if record.asset_id is None or record.event_date is None:
                raise ValueError("Registro B3 novo sem ativo ou data resolvidos.")
            if record.event_type:
                event_type = FinancialEventType(record.event_type)
                quantity = str(record.quantity) if record.quantity is not None else None
                unit_price = str(record.unit_price) if record.unit_price is not None else None
                amount = None
                metadata = {
                    "source": "B3",
                    "import_batch_id": str(batch_id),
                    # A trade moves value inside the portfolio; it is not an
                    # external deposit or withdrawal.
                    "capital_flow_type": CapitalFlowType.INTERNAL_TRANSFER.value,
                }
                if record.raw_payload:
                    metadata.update(json.loads(record.raw_payload))
            else:
                asset = session._assets.get(record.normalized_symbol or "")
                if asset is None:
                    raise ValueError("Ativo deixou de estar resolvido para o lote B3.")
                event_type = (
                    FinancialEventType.INTEREST_ON_EQUITY
                    if record.income_type == "JCP"
                    else FinancialEventType.FII_INCOME
                    if asset.asset_class is AssetClass.FII
                    else FinancialEventType.DIVIDEND
                )
                quantity = unit_price = None
                amount = str(record.total_value)
                metadata = {
                    "source": "B3",
                    "import_batch_id": str(batch_id),
                    "income_type": record.income_type,
                }
                if record.raw_payload:
                    metadata.update(json.loads(record.raw_payload))
            event_id = uuid4()
            db.add(
                FinancialEventRecord(
                    id=str(event_id),
                    portfolio_id=str(current_portfolio_id()),
                    account_id=str(session.account_id),
                    event_type=event_type.value,
                    asset_id=str(record.asset_id),
                    quantity=quantity,
                    unit_price=unit_price,
                    amount=amount,
                    effective_date=record.event_date,
                    occurred_at=datetime.now().astimezone(),
                    registered_at=datetime.now().astimezone(),
                    description="Importação B3",
                    metadata_json=json.dumps(metadata),
                )
            )
            audit.save_record_in_session(
                db,
                replace(
                    record,
                    status=B3ImportedRecordStatus.APPLIED,
                    financial_event_id=event_id,
                    applied_at=datetime.now().astimezone(),
                ),
            )
            applied += 1

    try:
        completed = repository.apply_batch(batch_id, operation)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    rebuild_portfolio_dashboard_snapshot()
    return {
        "batch_id": str(completed.id),
        "status": "APPLIED",
        "applied_count": applied,
        "duplicate_count": completed.new_rows if applied == 0 else 0,
        "counts": {
            "total": completed.total_rows,
            "new": completed.new_rows,
            "duplicate": completed.duplicate_rows,
            "review_required": completed.review_rows,
            "unsupported": completed.unsupported_rows,
            "invalid": completed.invalid_rows,
        },
    }


@router.put("/market-prices/{ticker}")
def update_market_price(
    ticker: str,
    market_price: MarketPriceInput,
) -> dict[str, object]:
    try:
        projection = session.update_market_price(
            ticker=ticker,
            current_price=market_price.current_price,
            effective_date=market_price.effective_date,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    rebuild_portfolio_dashboard_snapshot()
    return serialize_portfolio(projection)


@router.get("/market-prices/refresh-runs")
def list_market_price_refresh_runs(limit: int = 20) -> dict[str, object]:
    return {"runs": market_price_refresh_runs.list_recent(limit)}


@router.post("/market-prices/refresh")
def refresh_market_prices() -> dict[str, object]:
    started_at = datetime.now(UTC)
    try:
        result = session.refresh_open_market_prices_report(
            market_data_provider_for, today=date.today(), force=True
        )
        fx_outcomes = _refresh_open_fx_rates(today=date.today())
        result["providers"].extend(fx_outcomes)
    except Exception as error:
        provider_health.failure("Atualização da carteira", error)
        failed_run = {
            "id": str(uuid4()),
            "started_at": started_at,
            "finished_at": datetime.now(UTC),
            "status": "FAILED",
            "providers": [
                {
                    "provider": "Atualização da carteira",
                    "status": "FAILED",
                    "requested_assets": [],
                    "resolved_assets": 0,
                    "failed_assets": [],
                    "errors": [
                        {
                            "stage": "refresh_run",
                            "error_type": type(error).__name__,
                            "message": str(error)[:500],
                        }
                    ],
                }
            ],
        }
        market_price_refresh_runs.save(failed_run)
        raise HTTPException(
            status_code=503, detail="Atualização de cotações indisponível."
        ) from error
    for item in result["providers"]:
        if item["status"] in {"SUCCESS", "PARTIAL", "DEGRADED"}:
            provider_health.success(str(item["provider"]))
    provider_health.success("Atualização da carteira")
    if result["updated"]:
        rebuild_portfolio_dashboard_snapshot()
    refresh_run = {
        "id": str(uuid4()),
        "started_at": started_at,
        "finished_at": datetime.now(UTC),
        "status": (
            "PARTIAL"
            if result["unavailable"]
            or any(item["status"] not in {"SUCCESS", "STALE"} for item in result["providers"])
            else "SUCCESS"
        ),
        "providers": result["providers"],
    }
    market_price_refresh_runs.save(refresh_run)
    return {**result, "run_id": refresh_run["id"], "status": refresh_run["status"]}


def _refresh_open_fx_rates(*, today: date) -> list[dict[str, object]]:
    outcomes = []
    for currency in session.open_foreign_currencies():
        if session.has_fx_rate_for(currency, today):
            outcomes.append(
                {
                    "provider": "bcb_ptax",
                    "status": "STALE",
                    "requested_assets": [currency],
                    "resolved_assets": 0,
                    "failed_assets": [],
                    "duration_seconds": 0,
                }
            )
            continue
        started = datetime.now(UTC)
        try:
            rate = session.refresh_fx_rate(
                fx_data,
                base_currency=currency,
                quote_currency=session.base_currency,
                effective_date=today,
            )
            outcomes.append(
                {
                    "provider": rate.source,
                    "status": "SUCCESS",
                    "requested_assets": [currency],
                    "resolved_assets": 1,
                    "failed_assets": [],
                    "effective_date": rate.effective_date,
                    "duration_seconds": (datetime.now(UTC) - started).total_seconds(),
                }
            )
        except Exception as error:
            provider_health.failure("BCB PTAX", error)
            outcomes.append(
                {
                    "provider": "bcb_ptax",
                    "status": "FAILED",
                    "requested_assets": [currency],
                    "resolved_assets": 0,
                    "failed_assets": [currency],
                    "errors": [
                        {
                            "asset": currency,
                            "stage": "fx_quote",
                            "error_type": type(error).__name__,
                            "message": str(error)[:500],
                        }
                    ],
                    "duration_seconds": (datetime.now(UTC) - started).total_seconds(),
                }
            )
    return outcomes


def run_daily_market_data_refresh() -> None:
    """Best-effort startup refresh; persist outcomes without stopping other work."""

    for portfolio in SqlitePortfolioRepository().list(include_archived=False):
        token = set_active_portfolio_id(portfolio.id)
        try:
            _run_daily_market_data_refresh_for_portfolio()
        finally:
            reset_active_portfolio_id(token)


def _run_daily_market_data_refresh_for_portfolio() -> None:

    started_at = datetime.now(UTC)
    try:
        result = session.refresh_open_market_prices_report(
            market_data_provider_for, today=date.today()
        )
        fx_outcomes = _refresh_open_fx_rates(today=date.today())
        result["providers"].extend(fx_outcomes)
        if result["updated"] or any(item["status"] == "SUCCESS" for item in fx_outcomes):
            rebuild_portfolio_dashboard_snapshot()
        provider_health.success("Atualização da carteira")
        if result["updated"] or not result["unavailable"]:
            provider_health.success("Daily market refresh")
        run_status = (
            "PARTIAL"
            if result["unavailable"]
            or any(item["status"] not in {"SUCCESS", "STALE"} for item in result["providers"])
            else "SUCCESS"
        )
        market_price_refresh_runs.save(
            {
                "id": str(uuid4()),
                "started_at": started_at,
                "finished_at": datetime.now(UTC),
                "status": run_status,
                "providers": result["providers"],
            }
        )
    except Exception as error:
        provider_health.failure("Daily market refresh", error)
        provider_health.failure("Atualização da carteira", error)
        market_price_refresh_runs.save(
            {
                "id": str(uuid4()),
                "started_at": started_at,
                "finished_at": datetime.now(UTC),
                "status": "FAILED",
                "providers": [
                    {
                        "provider": "Daily market refresh",
                        "status": "FAILED",
                        "requested_assets": [],
                        "resolved_assets": 0,
                        "failed_assets": [],
                        "errors": [
                            {
                                "stage": "refresh_run",
                                "error_type": type(error).__name__,
                                "message": str(error)[:500],
                            }
                        ],
                    }
                ],
            }
        )


def run_daily_recurring_rule_execution() -> None:
    """Materialize due occurrences from rules that are still within their validity."""
    for portfolio in SqlitePortfolioRepository().list(include_archived=False):
        token = set_active_portfolio_id(portfolio.id)
        try:
            today = date.today()
            session.execute_recurring_rules(through=today)
            provider_health.success("Agendamentos recorrentes")
        except Exception as error:
            provider_health.failure("Agendamentos recorrentes", error)
        finally:
            reset_active_portfolio_id(token)


def run_daily_paid_income_sync() -> None:
    """Best-effort daily sync; the service short-circuits while disabled."""
    settings = paid_income_settings.get()
    if not settings.enabled or not settings.api_token:
        return
    for portfolio in SqlitePortfolioRepository().list(include_archived=False):
        token = set_active_portfolio_id(portfolio.id)
        try:
            service = PaidIncomeSyncService(
                paid_income_settings, SqliteImportedPaidIncomeRepository(portfolio.id)
            )
            result = service.sync(session, BrapiPaidIncomeProvider(settings.api_token))
            if result["status"] is PaidIncomeIntegrationStatus.CONNECTED:
                provider_health.success("BRAPI Proventos")
        except Exception as error:
            provider_health.failure("BRAPI Proventos", error)
        finally:
            reset_active_portfolio_id(token)


def refresh_historical_market_cache(*, reference_date: date | None = None) -> bool:
    """Warm the two annual official archives and save today's daily archive when ready."""
    requested_date = reference_date or date.today()
    try:
        historical_market_data.preload_last_two_years(reference_date=requested_date)
        daily_available = historical_market_data.refresh_daily_archive(
            effective_date=requested_date
        )
        provider_health.success("B3 COTAHIST")
        return daily_available
    except MarketDataUnavailable as error:
        provider_health.failure("B3 COTAHIST", error)
        return False


def run_scheduled_historical_market_refresh() -> None:
    """Refresh B3's daily official file around 23:59 without blocking the API."""
    refresh_historical_market_cache()
    while True:
        now = datetime.now()
        next_run = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        sleep((next_run - now).total_seconds())
        daily_available = refresh_historical_market_cache()
        run_daily_market_data_refresh()
        run_daily_recurring_rule_execution()
        run_daily_reference_data_refresh()
        if not daily_available:
            # B3 can publish the daily archive shortly after the market-day close.
            sleep(21 * 60)
            refresh_historical_market_cache()
            run_daily_market_data_refresh()
            run_daily_recurring_rule_execution()
            run_daily_reference_data_refresh()


def run_daily_reference_data_refresh() -> None:
    """Refresh only references that lack coverage for their expected cadence."""
    today = date.today()
    refresh_plan = (
        ("CDI", benchmark_data, today),
        ("IBOV", index_benchmark_data, today),
        ("IFIX", index_benchmark_data, today),
        ("SMLL", index_benchmark_data, today),
        ("IDIV", index_benchmark_data, today),
        ("IVVB11", ivvb11_benchmark_data, today),
        ("IPCA", benchmark_data, today.replace(day=1)),
        ("TR", benchmark_data, today),
        ("SELIC_TARGET", benchmark_data, today),
    )
    for name, provider, freshness_date in refresh_plan:
        if session.has_benchmark_data_for(name, freshness_date):
            continue
        provider_name = "B3" if name in B3_COMPARISON_BENCHMARKS else "BCB"
        try:
            requested_start = (
                max(date.min, today - timedelta(days=7))
                if name in {"IBOV", "IFIX", "SMLL", "IDIV", "IVVB11"}
                else freshness_date
            )
            imported = session.refresh_benchmark(
                provider, name=name, start_date=requested_start, end_date=today
            )
            logger.info(
                "benchmark_update benchmark=%s provider=%s requested=%s..%s "
                "received=%s persisted=%s status=SUCCESS",
                name,
                provider_name,
                requested_start,
                today,
                imported,
                imported,
            )
            provider_health.success(provider_name)
        except BenchmarkDataUnavailable as error:
            logger.warning(
                "benchmark_update benchmark=%s status=PROVIDER_ERROR error=%s", name, error
            )
            provider_health.failure(provider_name, error)
    for currency in session.open_foreign_currencies():
        if session.has_fx_rate_for(currency, today):
            continue
        try:
            session.refresh_fx_rate(
                fx_data,
                base_currency=currency,
                quote_currency=session.base_currency,
                effective_date=today,
            )
            provider_health.success("BCB PTAX")
        except FxRateUnavailable as error:
            provider_health.failure("BCB PTAX", error)


def _refresh_fixed_income_reference_history(
    *, indexer_type: FixedIncomeIndexerType, application_date: date
) -> tuple[str, ...]:
    """Fetch the curve needed to value a newly registered past application.

    The portfolio never invents a return. Once the official observations are
    persisted, every holdings read derives the current contract value from its
    application date through the latest available CDI or IPCA observation.
    A temporary BCB failure must not undo a valid investment registration.
    """
    benchmarks = _fixed_income_benchmarks(indexer_type)
    if not benchmarks or application_date >= date.today():
        return ()
    try:
        for benchmark in benchmarks:
            session.refresh_benchmark(
                benchmark_data,
                name=benchmark,
                start_date=application_date,
                end_date=date.today(),
            )
        provider_health.success("BCB")
        return benchmarks
    except BenchmarkDataUnavailable as error:
        provider_health.failure("BCB", error)
        return ()


def run_fixed_income_reference_backfill() -> None:
    """Restore missing official history for contracts created before this rollout."""
    oldest_by_benchmark: dict[str, date] = {}
    for details in session._fixed_income_details.values():
        benchmarks = _fixed_income_benchmarks(details.indexer_type)
        if not benchmarks or details.application_date >= date.today():
            continue
        for benchmark in benchmarks:
            oldest = oldest_by_benchmark.get(benchmark)
            if oldest is None or details.application_date < oldest:
                oldest_by_benchmark[benchmark] = details.application_date
    for benchmark, start_date in oldest_by_benchmark.items():
        try:
            session.refresh_benchmark(
                benchmark_data,
                name=benchmark,
                start_date=start_date,
                end_date=date.today(),
            )
            provider_health.success("BCB")
        except BenchmarkDataUnavailable as error:
            provider_health.failure("BCB", error)


def run_reference_data_bootstrap() -> None:
    """Load current and historical official series without concurrent BCB calls."""
    portfolio_start = min((event.effective_date for event in session._events), default=None)
    if portfolio_start is not None:
        end_date = date.today()
        for name, provider in (
            ("CDI", benchmark_data),
            ("IPCA", benchmark_data),
            ("IBOV", index_benchmark_data),
            ("IFIX", index_benchmark_data),
            ("SMLL", index_benchmark_data),
            ("IDIV", index_benchmark_data),
            ("IVVB11", ivvb11_benchmark_data),
        ):
            provider_name = "B3" if name in B3_COMPARISON_BENCHMARKS else "BCB"
            stored_dates = (
                [
                    rate.effective_date
                    for rate in session._benchmark_rates
                    if rate.name.upper() == name
                ]
                if name == "CDI"
                else [item.effective_date for item in session.benchmark_observations(name)]
            )
            latest_stored = max(stored_dates, default=None)
            requested_start = (
                portfolio_start
                if latest_stored is None
                else max(portfolio_start, latest_stored - timedelta(days=7))
            )
            try:
                imported = session.refresh_benchmark(
                    provider, name=name, start_date=requested_start, end_date=end_date
                )
                logger.info(
                    "benchmark_update benchmark=%s provider=%s requested=%s..%s "
                    "received=%s persisted=%s latest=%s status=SUCCESS",
                    name,
                    provider_name,
                    requested_start,
                    end_date,
                    imported,
                    imported,
                    max(
                        (
                            item.effective_date
                            for item in (
                                session.benchmark_observations(name)
                                if name != "CDI"
                                else tuple(
                                    rate
                                    for rate in session._benchmark_rates
                                    if rate.name.upper() == name
                                )
                            )
                        ),
                        default=None,
                    ),
                )
                provider_health.success(provider_name)
            except BenchmarkDataUnavailable as error:
                logger.warning(
                    "benchmark_update benchmark=%s status=PROVIDER_ERROR error=%s",
                    name,
                    error,
                )
                provider_health.failure(provider_name, error)
    run_daily_reference_data_refresh()
    run_fixed_income_reference_backfill()


def _fixed_income_benchmarks(indexer_type: FixedIncomeIndexerType) -> tuple[str, ...]:
    return {
        FixedIncomeIndexerType.CDI_PERCENT: ("CDI",),
        FixedIncomeIndexerType.CDI_PLUS: ("CDI",),
        FixedIncomeIndexerType.IPCA_PLUS: ("IPCA",),
        FixedIncomeIndexerType.SAVINGS_RULE: ("TR", "SELIC_TARGET"),
    }.get(indexer_type, ())


def _fixed_income_benchmark(indexer_type: FixedIncomeIndexerType) -> str | None:
    """Backward-compatible single-index view of the reference mapping."""
    benchmarks = _fixed_income_benchmarks(indexer_type)
    return benchmarks[0] if benchmarks else None


@router.get("/market-prices/{ticker}/automatic")
def get_automatic_market_price(
    ticker: str,
    effective_date: date,
    asset_class: AssetClass | None = None,
) -> dict[str, object]:
    try:
        if asset_class is AssetClass.CRYPTO:
            observation = crypto_data.price_on(ticker, effective_date)
        elif asset_class in (
            AssetClass.INTERNATIONAL,
            AssetClass.INTERNATIONAL_ETF,
            AssetClass.US_REIT,
        ):
            observation = us_market_data.price_on(ticker, effective_date)
        else:
            try:
                observation = market_data.price_on(ticker, effective_date)
            except MarketDataUnavailable:
                try:
                    observation = historical_market_data.price_on(ticker, effective_date)
                except MarketDataUnavailable:
                    if asset_class is None:
                        observation = crypto_data.price_on(ticker, effective_date)
                    else:
                        raise
    except Exception:
        provider_health.failure("Mercado automático", MarketDataUnavailable())
        raise HTTPException(
            status_code=404, detail="Não há cotação automática para a data escolhida."
        )
    source_name = {
        "coingecko": "CoinGecko",
        "b3_cotahist": "B3 COTAHIST",
        "twelve_data": "Twelve Data",
    }.get(observation.source, "Brapi")
    provider_health.success(source_name)
    return {
        "ticker": observation.symbol,
        "price": observation.price,
        "effective_date": observation.effective_date,
        "source": observation.source,
    }


@router.post("/market-prices/historical-cache/refresh")
def refresh_historical_price_cache() -> dict[str, object]:
    """Manually warm the local two-year official B3 archive cache."""
    try:
        years = historical_market_data.preload_last_two_years()
        daily_available = historical_market_data.refresh_daily_archive()
    except MarketDataUnavailable as error:
        provider_health.failure("B3 COTAHIST", error)
        raise HTTPException(status_code=503, detail=str(error)) from error
    provider_health.success("B3 COTAHIST")
    return {"years": years, "daily_available": daily_available, "source": "b3_cotahist"}


@router.post("/market-prices/history/b3-etf/backfill")
def backfill_b3_etf_price_history(
    request: B3EtfHistoryBackfillInput,
) -> dict[str, object]:
    """Persist official B3 BDI closes for one fixed-income ETF and date range."""
    if request.end_date < request.start_date:
        raise HTTPException(status_code=422, detail="A data final deve ser posterior à inicial.")
    if request.end_date > date.today():
        raise HTTPException(status_code=422, detail="A data final não pode estar no futuro.")
    history_start = request.start_date - timedelta(days=7)
    if history_start < date.today() - timedelta(days=20):
        raise HTTPException(
            status_code=422,
            detail=(
                "O BDI estruturado disponibiliza apenas a janela recente; "
                "datas mais antigas precisam ser obtidas no acervo de boletins da B3."
            ),
        )
    asset = session._assets.get(request.ticker.strip().upper())
    if asset is None:
        raise HTTPException(status_code=404, detail="Ativo não encontrado na carteira local.")
    if asset.asset_class is not AssetClass.BRAZILIAN_ETF:
        raise HTTPException(
            status_code=422,
            detail="O backfill BDI de renda fixa atende ativos da classe ETF Brasil.",
        )

    # Include a short pre-period window so valuation on the opening date can
    # use the previous B3 trading session when the date itself has no trade.
    try:
        observations = b3_etf_price_data.history(
            request.ticker, start_date=history_start, end_date=request.end_date
        )
    except MarketDataUnavailable as error:
        provider_health.failure("B3 BDI histórico de ETFs", error)
        raise HTTPException(status_code=503, detail=str(error)) from error
    if not observations:
        raise HTTPException(
            status_code=404, detail="A B3 não retornou negócios de ETF para o intervalo solicitado."
        )

    imported = session.import_market_price_history(ticker=request.ticker, prices=observations)
    if imported:
        rebuild_portfolio_dashboard_snapshot()
    provider_health.success("B3 BDI histórico de ETFs")
    return {
        "ticker": request.ticker.strip().upper(),
        "requested_start_date": request.start_date,
        "backfill_start_date": history_start,
        "requested_end_date": request.end_date,
        "source": "b3_etf",
        "observations_found": len(observations),
        "observations_imported": imported,
        "prices": [
            {"effective_date": item.effective_date, "price": item.price} for item in observations
        ],
    }


@router.post("/market-prices/history/backfill")
def backfill_market_price_history() -> dict[str, object]:
    """Persist official B3 closes for assets held at any point in their history."""
    supported = {AssetClass.BRAZILIAN_STOCK, AssetClass.BRAZILIAN_ETF, AssetClass.FII}
    events_by_asset: dict[UUID, list[FinancialEvent]] = {}
    for event in session.history():
        if event.asset is not None and event.asset.asset_class in supported:
            events_by_asset.setdefault(event.asset.id, []).append(event)

    # Include positions that have since been fully sold. Reconstruct enough
    # quantity history to avoid limiting the cache to today's open positions.
    tickers: dict[str, date] = {}
    for asset_id, asset_events in events_by_asset.items():
        quantity = Decimal("0")
        ever_held = False
        for event in sorted(
            asset_events, key=lambda item: (item.effective_date, item.registered_at)
        ):
            if event.event_type is FinancialEventType.BUY and event.quantity is not None:
                quantity += event.quantity.value
                ever_held = quantity > 0 or ever_held
            elif event.event_type is FinancialEventType.SELL and event.quantity is not None:
                if event.quantity.value <= quantity:
                    quantity -= event.quantity.value
        if ever_held:
            asset = asset_events[0].asset
            assert asset is not None
            first_date = min(event.effective_date for event in asset_events)
            tickers[str(asset.ticker)] = max(first_date, date(2021, 1, 1))

    imported = 0
    unavailable: list[str] = []
    earliest = min(tickers.values(), default=None)
    cache_refresh_warning: str | None = None
    if earliest is not None:
        try:
            # The current-year local archive can be months behind. Refresh it
            # only in this explicit backfill path; the performance projector
            # itself consumes persisted quotes and never calls a provider.
            try:
                historical_market_data.refresh_annual_archive(date.today().year)
            except MarketDataUnavailable as error:
                # Existing local annual archives remain usable offline. Surface
                # their freshness limitation while still completing the cache.
                cache_refresh_warning = str(error)
            series_by_ticker = historical_market_data.history_many(
                set(tickers), start_date=earliest, end_date=date.today()
            )
        except MarketDataUnavailable as error:
            provider_health.failure("B3 COTAHIST", error)
            raise HTTPException(status_code=503, detail=str(error)) from error
        for ticker, start_date in tickers.items():
            series = tuple(
                observation
                for observation in series_by_ticker.get(ticker, ())
                if observation.effective_date >= start_date
            )
            if not series:
                unavailable.append(ticker)
                continue
            try:
                imported += session.import_market_price_history(ticker=ticker, prices=series)
            except ValueError:
                unavailable.append(ticker)
        provider_health.success("B3 COTAHIST")
    if imported:
        rebuild_portfolio_dashboard_snapshot()
    return {
        "imported": imported,
        "unavailable": unavailable,
        "source": "b3_cotahist",
        "assets_considered": len(tickers),
        "history_start_date": earliest,
        "history_end_date": date.today() if earliest else None,
        "cache_refresh_warning": cache_refresh_warning,
    }


@router.post("/fx-rates/history/backfill")
def backfill_fx_rate_history() -> dict[str, object]:
    """Import source-dated BCB PTAX history for the portfolio measurement window."""
    first_event = min((event.effective_date for event in session.history()), default=date.today())
    start_date = max(first_event, date(2021, 1, 1))
    end_date = date.today()
    outcomes: list[dict[str, object]] = []
    imported = 0
    for currency in session.open_foreign_currencies():
        if currency != "USD":
            outcomes.append({"currency": currency, "status": "UNSUPPORTED"})
            continue
        try:
            observations = fx_data.history(currency, session.base_currency, start_date, end_date)
            imported += session.import_fx_rate_history(observations)
            outcomes.append(
                {
                    "currency": currency,
                    "status": "SUCCESS",
                    "observations": len(observations),
                    "first_date": observations[0].effective_date if observations else None,
                    "last_date": observations[-1].effective_date if observations else None,
                }
            )
        except FxRateUnavailable as error:
            outcomes.append({"currency": currency, "status": "FAILED", "reason": str(error)})
    return {
        "source": "bcb_ptax",
        "start_date": start_date,
        "end_date": end_date,
        "imported": imported,
        "currencies": outcomes,
    }


@router.post("/market-prices/us/history/backfill")
def backfill_us_market_price_history() -> dict[str, object]:
    """Import historical closes for USD-denominated assets held by the portfolio."""
    events = tuple(
        event
        for event in session.history()
        if event.asset is not None
        and event.asset.currency.code.upper() == "USD"
        and event.asset.asset_class
        in {AssetClass.INTERNATIONAL, AssetClass.INTERNATIONAL_ETF, AssetClass.US_REIT}
    )
    by_ticker: dict[str, date] = {}
    for event in events:
        ticker = str(event.asset.ticker)
        # Weekend/holiday trades can be valued with the last close at or before
        # the trade date; retrieve a short pre-roll without assigning it earlier.
        first_needed_date = max(date(2021, 1, 1), event.effective_date - timedelta(days=10))
        by_ticker[ticker] = min(by_ticker.get(ticker, first_needed_date), first_needed_date)
    imported = 0
    outcomes = []
    for ticker, first_date in by_ticker.items():
        try:
            observations = us_market_data.history(ticker, first_date, date.today())
            imported += session.import_market_price_history(ticker=ticker, prices=observations)
            outcomes.append(
                {
                    "ticker": ticker,
                    "status": "SUCCESS",
                    "observations": len(observations),
                    "first_date": observations[0].effective_date if observations else None,
                    "last_date": observations[-1].effective_date if observations else None,
                }
            )
        except MarketDataUnavailable as error:
            outcomes.append({"ticker": ticker, "status": "FAILED", "reason": str(error)})
    if imported:
        rebuild_portfolio_dashboard_snapshot()
    return {"source": "twelve_data", "imported": imported, "assets": outcomes}


@router.post("/market-prices/crypto/history/backfill")
def backfill_crypto_market_price_history() -> dict[str, object]:
    """Import source-dated CoinGecko daily history for held crypto assets."""
    events = tuple(
        event
        for event in session.history()
        if event.asset is not None and event.asset.asset_class is AssetClass.CRYPTO
    )
    by_ticker: dict[str, date] = {}
    for event in events:
        ticker = str(event.asset.ticker)
        first_needed_date = max(date(2021, 1, 1), event.effective_date - timedelta(days=10))
        by_ticker[ticker] = min(by_ticker.get(ticker, first_needed_date), first_needed_date)
    imported = 0
    outcomes = []
    for ticker, first_date in by_ticker.items():
        try:
            observations = crypto_data.history(ticker, first_date, date.today())
            imported += session.import_market_price_history(ticker=ticker, prices=observations)
            outcomes.append(
                {
                    "ticker": ticker,
                    "status": "SUCCESS",
                    "observations": len(observations),
                    "first_date": observations[0].effective_date if observations else None,
                    "last_date": observations[-1].effective_date if observations else None,
                }
            )
        except MarketDataUnavailable as error:
            outcomes.append({"ticker": ticker, "status": "FAILED", "reason": str(error)})
    if imported:
        rebuild_portfolio_dashboard_snapshot()
    return {"source": "coingecko", "imported": imported, "assets": outcomes}


@router.post("/dividends", status_code=status.HTTP_201_CREATED)
def create_dividend(dividend: DividendInput) -> dict[str, object]:
    try:
        projection = session.register_dividend(
            ticker=dividend.ticker,
            amount=dividend.amount,
            effective_date=dividend.effective_date,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    rebuild_portfolio_dashboard_snapshot()
    return serialize_portfolio(projection)


@router.post("/jcp", status_code=status.HTTP_201_CREATED)
def create_jcp(jcp: JcpInput) -> dict[str, object]:
    if jcp.withheld_tax >= jcp.gross_amount:
        raise HTTPException(
            status_code=422, detail="O IR retido deve ser menor que o valor bruto do JCP."
        )
    asset = session._assets.get(jcp.ticker.strip().upper())
    if asset is None:
        raise HTTPException(status_code=422, detail="Ativo não encontrado na carteira local.")
    session.register_income(
        event_type=FinancialEventType.INTEREST_ON_EQUITY,
        asset=asset,
        amount=jcp.gross_amount - jcp.withheld_tax,
        effective_date=jcp.effective_date,
        description=f"JCP bruto {jcp.gross_amount}; IR retido {jcp.withheld_tax}",
    )
    projection = session.projection()
    rebuild_portfolio_dashboard_snapshot()
    return serialize_portfolio(projection)


@router.post("/fii-income", status_code=status.HTTP_201_CREATED)
def create_fii_income(income: FiiIncomeInput) -> dict[str, object]:
    asset = session._assets.get(income.ticker.strip().upper())
    if asset is None:
        raise HTTPException(status_code=422, detail="Ativo não encontrado na carteira local.")
    session.register_income(
        event_type=FinancialEventType.FII_INCOME,
        asset=asset,
        amount=income.amount,
        effective_date=income.effective_date,
    )
    projection = session.projection()
    rebuild_portfolio_dashboard_snapshot()
    return serialize_portfolio(projection)


@router.post("/external-flows", status_code=status.HTTP_201_CREATED)
def create_external_flow(flow: ExternalFlowInput) -> dict[str, object]:
    try:
        projection = session.register_external_flow(
            event_type=FinancialEventType(flow.event_type),
            amount=flow.amount,
            effective_date=flow.effective_date,
            capital_flow_type=flow.capital_flow_type,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    rebuild_portfolio_dashboard_snapshot()
    return serialize_portfolio(projection)


@router.get("/portfolio/performance")
def get_portfolio_performance(
    start_date: date, end_date: date, asset_class: AssetClass | None = None
) -> dict[str, object]:
    effective_end_date = _effective_analysis_end_date(start_date, end_date)
    try:
        performance = session.performance(
            start_date=start_date, end_date=effective_end_date, asset_class=asset_class
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    incomplete_trades = [
        event
        for event in session.history()
        if start_date <= event.effective_date <= effective_end_date
        and event.event_type in {FinancialEventType.BUY, FinancialEventType.SELL}
        and event.financial_status == "DATA_GAP"
        and (
            asset_class is None
            or event.asset is not None
            and event.asset.asset_class is asset_class
        )
    ]
    return {
        "requested_end_date": end_date,
        "asset_class": asset_class.value if asset_class else None,
        "financial_data_status": "PARTIAL" if incomplete_trades else "COMPLETE",
        "incomplete_trade_count": len(incomplete_trades),
        "incomplete_trades": [
            {
                "date": event.effective_date,
                "ticker": str(event.asset.ticker) if event.asset else None,
                "event_type": event.event_type.value,
                "quantity": event.quantity.value if event.quantity else None,
                "missing_fields": ["unit_price", "proceeds"],
            }
            for event in incomplete_trades
        ],
        "start_date": performance.start_date,
        "end_date": performance.end_date,
        "beginning_equity": performance.beginning_equity.amount
        if performance.beginning_equity
        else None,
        "ending_equity": performance.ending_equity.amount if performance.ending_equity else None,
        "total_contributions": performance.total_contributions.amount,
        "total_withdrawals": performance.total_withdrawals.amount,
        "net_external_flow": performance.net_external_flow.amount,
        "twr": performance.twr,
        "xirr": performance.xirr,
        "performance_status": performance.performance_status,
        "coverage_ratio": performance.coverage_ratio,
        "price_max_age_days": PerformanceProjector.MAX_STALE_PRICE_AGE_DAYS,
        "missing_assets": performance.missing_assets,
        "missing_value": performance.missing_value.amount,
        "missing_periods": performance.missing_periods,
        "unavailable_reason": performance.unavailable_reason,
        "periods": [
            {
                "start_date": period.start_date,
                "end_date": period.end_date,
                "return_percentage": period.return_percentage,
            }
            for period in performance.periods
        ],
    }


@router.get("/analytics/wealth-explanation")
def get_wealth_explanation(start_date: date, end_date: date) -> dict[str, object]:
    """Explain wealth movement from persisted ledger, prices and FX observations only."""
    effective_end_date = _effective_analysis_end_date(start_date, end_date)
    events = session.history()
    projection_dates = {start_date, effective_end_date}
    projection_dates.update(
        event.effective_date
        for event in events
        if start_date < event.effective_date <= effective_end_date
        and event.asset is not None
        and event.asset.currency.code.upper() != session.base_currency.upper()
        and event.event_type
        in {
            FinancialEventType.BUY,
            FinancialEventType.SELL,
            FinancialEventType.DIVIDEND,
            FinancialEventType.INTEREST_ON_EQUITY,
            FinancialEventType.FII_INCOME,
        }
    )
    ordered_dates = tuple(sorted(projection_dates))
    portfolio_by_date = dict(zip(ordered_dates, session.projections_at(ordered_dates), strict=True))
    valuation_by_date = {}

    def portfolio_at(as_of: date) -> PortfolioProjection:
        portfolio = portfolio_by_date.get(as_of)
        if portfolio is None:
            portfolio = session.projection(as_of=as_of)
            portfolio_by_date[as_of] = portfolio
        return portfolio

    def valuation_at(as_of: date):
        valuation = valuation_by_date.get(as_of)
        if valuation is None:
            valuation = session.base_currency_valuation(as_of=as_of, projection=portfolio_at(as_of))
            valuation_by_date[as_of] = valuation
        return valuation

    try:
        explanation = WealthExplanationService(
            events=events,
            portfolio_at=portfolio_at,
            valuation_at=valuation_at,
            performance_at=lambda start, end: session.performance(start_date=start, end_date=end),
        ).explain(start_date=start_date, end_date=effective_end_date)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return explanation.payload


@router.get("/analytics/wealth-evolution")
def get_wealth_evolution(start_date: date, end_date: date) -> dict[str, object]:
    """Reconstruct persisted valuations as-of relevant economic dates only."""
    effective_end_date = _effective_analysis_end_date(start_date, end_date)
    reconstruction = HistoricalPortfolioReconstructionService(
        events=session.history(),
        market_prices=session._market_prices,
        portfolio_at=lambda as_of: session.projection(as_of=as_of),
        valuation_at=lambda as_of: session.base_currency_valuation(as_of=as_of),
        valuation_for_portfolio=lambda as_of, portfolio: session.base_currency_valuation(
            as_of=as_of, projection=portfolio
        ),
        portfolio_series=session.projections_at,
    )
    points = reconstruction.wealth_series(start_date=start_date, end_date=effective_end_date)
    return {
        "start_date": start_date,
        "requested_end_date": end_date,
        "end_date": effective_end_date,
        "points": [
            {
                "effective_date": point.as_of_date,
                "valued_wealth": point.valued_wealth,
                "coverage_status": point.coverage_status,
                "valued_positions": point.valued_positions,
                "unvalued_position_count": point.unvalued_positions,
                "issues": point.issues,
                "unvalued_positions": [
                    {
                        "ticker": position.ticker,
                        "asset_class": position.asset_class,
                        "status": position.status,
                        "issue": position.issue,
                    }
                    for position in point.positions
                    if position.status == "UNVALUED"
                ],
            }
            for point in points
        ],
    }


def _performance_read_model_revision() -> tuple[object, ...]:
    events = tuple(
        (
            event.id,
            event.effective_date,
            event.event_type.value,
            event.known_total_amount,
            event.capital_flow_type.value,
        )
        for event in session._events
    )
    prices = tuple(
        (price.id, price.asset.id, price.effective_date, price.price.amount)
        for price in session._market_prices
    )
    rates = tuple(session._benchmark_rates)
    fixed_income = tuple(
        sorted(
            (str(asset_id), details) for asset_id, details in session._fixed_income_details.items()
        )
    )
    benchmark_revision = tuple(
        (
            name,
            tuple(
                (item.effective_date, item.value, item.nature, item.source)
                for item in session.benchmark_observations(name)
            ),
        )
        for name in ("IBOV", "IFIX", "IPCA", "SMLL", "IDIV", "IVVB11")
    )
    return (
        events,
        prices,
        rates,
        benchmark_revision,
        fixed_income,
        session.base_currency,
    )


@lru_cache(maxsize=32)
def _cached_performance_comparison(
    portfolio_id: UUID,
    start_date: date,
    end_date: date,
    asset_class: AssetClass | None,
    revision: tuple[object, ...],
) -> dict[str, object]:
    del (
        portfolio_id,
        revision,
    )  # Immutable ownership/revision values are cache keys and invalidation tokens.
    stored = {
        name: session.benchmark_observations(name)
        for name in ("IBOV", "IFIX", "IPCA", "SMLL", "IDIV", "IVVB11")
    }

    periods: dict[tuple[date, date], object] = {}

    def performance_at(start: date, end: date) -> object:
        key = (start, end)
        if key not in periods:
            periods[key] = session.performance(
                start_date=start, end_date=end, asset_class=asset_class
            )
        return periods[key]

    comparison = build_performance_comparison(
        start_date=start_date,
        end_date=end_date,
        rates=tuple(session._benchmark_rates),
        observations=stored,
        performance_at=performance_at,
    )
    class_start_dates = {
        item.value: min(
            event.effective_date
            for event in session._events
            if event.asset is not None and event.asset.asset_class is item
        )
        for item in AssetClass
        if any(
            event.asset is not None and event.asset.asset_class is item
            for event in session._events
        )
    }
    all_start_dates = [
        event.effective_date for event in session._events if event.asset is not None
    ]
    comparison["available_start_dates"] = {
        "ALL": min(all_start_dates).isoformat() if all_start_dates else None,
        **{name: value.isoformat() for name, value in class_start_dates.items()},
    }
    comparison["available_asset_classes"] = tuple(sorted(class_start_dates))
    comparison["asset_class"] = asset_class.value if asset_class is not None else None
    return comparison


@router.get("/analytics/performance-comparison")
def get_performance_comparison(
    end_date: date,
    start_date: date | None = None,
    asset_class: AssetClass | None = None,
) -> dict[str, object]:
    """Serve the Entender comparison from persisted streams without provider calls."""
    if start_date is None:
        event_dates = [
            event.effective_date
            for event in session._events
            if event.asset is not None
            and (asset_class is None or event.asset.asset_class is asset_class)
        ]
        start_date = min(event_dates) if event_dates else end_date
    if end_date < start_date:
        raise HTTPException(
            status_code=422, detail="A data final deve ser posterior à data inicial."
        )
    return _cached_performance_comparison(
        current_portfolio_id(),
        start_date,
        end_date,
        asset_class,
        _performance_read_model_revision(),
    )


@router.get("/portfolio/benchmark-comparison")
def get_benchmark_comparison(name: str, start_date: date, end_date: date) -> dict[str, object]:
    effective_end_date = _effective_analysis_end_date(start_date, end_date)
    comparison = session.benchmark_comparison(
        name=name, start_date=start_date, end_date=effective_end_date
    )
    return {
        "requested_end_date": end_date,
        "benchmark_name": comparison.benchmark_name,
        "portfolio_twr": comparison.portfolio_twr,
        "benchmark_return": comparison.benchmark_return,
        "difference": comparison.difference,
        "observed_rates": comparison.observed_rates,
        "unavailable_reason": comparison.unavailable_reason,
    }


@router.post("/benchmarks/{name}", status_code=status.HTTP_201_CREATED)
def create_benchmark_rate(name: str, benchmark: BenchmarkRateInput) -> dict[str, str]:
    try:
        session.register_benchmark_rate(
            name=name,
            return_percentage=benchmark.return_percentage,
            effective_date=benchmark.effective_date,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {"status": "registered"}


@router.post("/benchmarks/{name}/refresh")
def refresh_benchmark(name: str, start_date: date, end_date: date) -> dict[str, object]:
    try:
        normalized_name = name.upper()
        provider = (
            ivvb11_benchmark_data
            if normalized_name == "IVVB11"
            else index_benchmark_data
            if normalized_name in B3_COMPARISON_BENCHMARKS
            else benchmark_data
        )
        imported = session.refresh_benchmark(
            provider, name=name, start_date=start_date, end_date=end_date
        )
    except BenchmarkDataUnavailable as error:
        provider_name = "B3" if normalized_name in B3_COMPARISON_BENCHMARKS else "BCB"
        provider_health.failure(provider_name, error)
        raise HTTPException(status_code=503, detail=str(error)) from error
    provider_name = "B3" if normalized_name in B3_COMPARISON_BENCHMARKS else "BCB"
    provider_health.success(provider_name)
    return {
        "benchmark": name.upper(),
        "observations": imported,
        "source": "b3" if normalized_name in B3_COMPARISON_BENCHMARKS else "bcb",
    }


@router.get("/data-sources")
def get_data_sources() -> dict[str, object]:
    providers = provider_health.statuses(
        (
            "Brapi",
            "B3 COTAHIST",
            "Atualização da carteira",
            "BCB",
            "BCB PTAX",
            "CoinGecko",
            "B3",
            "Agendamentos recorrentes",
        )
    )
    descriptions = {
        "B3 COTAHIST": "Arquivos oficiais em cache: dois anos e arquivo diário.",
        "Atualização da carteira": "Últimas cotações válidas aplicadas às posições abertas.",
        "Agendamentos recorrentes": (
            "Verifica diariamente regras vigentes e materializa somente ocorrências até hoje."
        ),
    }
    now = datetime.now().astimezone()
    next_market_refresh = now.replace(hour=23, minute=59, second=0, microsecond=0)
    if next_market_refresh <= now:
        next_market_refresh += timedelta(days=1)
    scheduled_providers = {
        "Brapi",
        "B3 COTAHIST",
        "Atualização da carteira",
        "Agendamentos recorrentes",
    }
    return {
        "providers": [
            {
                "provider": item.provider,
                "status": item.status,
                "last_success": item.last_success,
                "last_failure": item.last_failure,
                "consecutive_failures": item.consecutive_failures,
                "last_error_type": item.last_error_type,
                "description": descriptions.get(
                    item.provider, "Consulta e atualização de dados públicos."
                ),
                "next_execution": (
                    next_market_refresh if item.provider in scheduled_providers else None
                ),
                "execution_note": (
                    None
                    if item.provider in scheduled_providers
                    else "Sob demanda ou ao iniciar o backend"
                ),
                "group": (
                    "Agendamentos do sistema"
                    if item.provider == "Agendamentos recorrentes"
                    else "Fontes de dados"
                ),
            }
            for item in providers
        ]
    }


@router.get("/benchmarks/{name}")
def get_benchmark_observations(name: str) -> dict[str, object]:
    benchmark = name.upper()
    if benchmark == "CDI":
        observations = tuple(
            {
                "effective_date": rate.effective_date,
                "value": rate.return_percentage,
                "nature": "PERIODIC_RATE",
                "source": "manual_or_bcb",
            }
            for rate in session._benchmark_rates
            if rate.name.upper() == benchmark
        )
    else:
        observations = tuple(
            {
                "effective_date": observation.effective_date,
                "value": observation.value,
                "nature": observation.nature,
                "source": observation.source,
            }
            for observation in session.benchmark_observations(benchmark)
        )
    return {"benchmark": benchmark, "observations": observations}


@router.get("/portfolio/risk")
def get_portfolio_risk(start_date: date, end_date: date) -> dict[str, object]:
    try:
        risk = session.risk(start_date=start_date, end_date=end_date)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {
        "start_date": risk.start_date,
        "end_date": risk.end_date,
        "frequency": risk.frequency,
        "observations": len(risk.returns),
        "periodic_volatility": risk.periodic_volatility,
        "annualized_volatility": risk.annualized_volatility,
        "maximum_drawdown": risk.maximum_drawdown,
        "peak_date": risk.peak_date,
        "trough_date": risk.trough_date,
        "recovery_date": risk.recovery_date,
        "sharpe_ratio": risk.sharpe_ratio,
        "sharpe_unavailable_reason": risk.sharpe_unavailable_reason,
    }


@router.get("/portfolio/risk-contribution")
def get_portfolio_risk_contribution(as_of: date | None = None) -> dict[str, object]:
    risk = session.risk_contribution(as_of=as_of)
    return {
        "portfolio_volatility": risk.portfolio_volatility,
        "risk_coverage": risk.risk_coverage,
        "covariance": risk.covariance,
        "correlation": risk.correlation,
        "assets": [
            {
                "ticker": item.ticker,
                "weight": item.weight,
                "volatility": item.volatility,
                "risk_contribution": item.contribution,
                "risk_contribution_share": item.contribution_share,
            }
            for item in risk.assets
        ],
    }


@router.get("/portfolio/allocation")
def get_portfolio_allocation(as_of: date | None = None) -> dict[str, object]:
    allocation = session.allocation(as_of=as_of)
    return {
        "portfolio_market_value": allocation.portfolio_market_value.amount,
        "valued_assets": allocation.valued_assets,
        "total_open_assets": allocation.total_open_assets,
        "valuation_coverage": allocation.valuation_coverage,
        "largest_position_weight": allocation.largest_position_weight,
        "top_3_weight": allocation.top_3_weight,
        "top_5_weight": allocation.top_5_weight,
        "hhi": allocation.hhi,
        "assets": [
            {
                "ticker": str(asset.position.asset.ticker),
                "market_value": asset.position.market_value.amount
                if asset.position.current_price
                else None,
                "portfolio_weight": asset.portfolio_weight,
                "total_result": asset.position.total_result.amount,
                "result_contribution_share": asset.result_contribution_share,
                "is_open": not asset.position.is_empty,
            }
            for asset in allocation.assets
        ],
    }


@router.put("/assets/{ticker}/class")
def update_asset_class(ticker: str, classification: AssetClassInput) -> dict[str, str]:
    try:
        session.update_asset_class(ticker=ticker, asset_class=classification.asset_class)
        rebuild_portfolio_dashboard_snapshot()
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {"status": "updated"}


@router.get("/portfolio/class-allocation")
def get_portfolio_class_allocation(as_of: date | None = None) -> dict[str, object]:
    valuation = session.base_currency_valuation(as_of=as_of)
    values = {item.ticker: item.market_value_base for item in valuation.positions}
    positions = session.projection(as_of=as_of).positions
    by_class: dict[AssetClass, list[Decimal | None]] = {}
    for position in positions:
        if not position.is_empty:
            by_class.setdefault(position.asset.asset_class, []).append(
                values.get(str(position.asset.ticker))
            )
    classes = []
    for asset_class, class_values in by_class.items():
        market_value = (
            sum((value for value in class_values if value is not None), Decimal("0"))
            if all(value is not None for value in class_values)
            else None
        )
        classes.append(
            {
                "asset_class": asset_class,
                "market_value": market_value,
                "weight": (
                    market_value / valuation.market_value
                    if market_value is not None
                    and valuation.market_value not in (None, Decimal("0"))
                    else None
                ),
                "asset_count": len(class_values),
                "total_result": None,
                "income_received": None,
                "result_contribution_share": None,
            }
        )
    classes.sort(key=lambda item: item["market_value"] or Decimal("0"), reverse=True)
    return {
        "base_currency": valuation.base_currency,
        "valuation_complete": valuation.complete,
        "classes": classes,
    }


@router.get("/portfolio/diversification")
def get_portfolio_diversification(as_of: date | None = None) -> dict[str, object]:
    projection = session.diversification(as_of=as_of)

    def serialize(dimension: DiversificationDimension) -> dict[str, object]:
        return {
            "exposures": [{"key": item.key, "weight": item.weight} for item in dimension.exposures],
            "hhi": dimension.hhi,
            "coverage": dimension.coverage,
            "unavailable_reason": dimension.unavailable_reason,
        }

    return {
        "asset": serialize(projection.asset),
        "asset_class": serialize(projection.asset_class),
        "sector": serialize(projection.sector),
        "country": serialize(projection.country),
        "currency": serialize(projection.currency),
    }


@router.get("/portfolio/intelligence")
def get_portfolio_intelligence(as_of: date | None = None) -> dict[str, object]:
    intelligence = session.intelligence(as_of=as_of)
    return {
        "as_of": intelligence.as_of,
        "counts": {
            "info": intelligence.info_count,
            "attention": intelligence.attention_count,
            "high_attention": intelligence.high_attention_count,
        },
        "findings": [
            {
                "code": finding.code,
                "category": finding.category,
                "severity": finding.severity,
                "title": finding.title,
                "description": finding.description,
                "evidence": finding.evidence,
                "as_of": finding.as_of,
                "logical_key": finding.logical_key,
                "current_value": finding.current_value,
                "comparison_value": finding.comparison_value,
                "comparison_as_of": finding.comparison_as_of,
                "change": finding.change,
                "change_pp": finding.change_pp,
                "decomposition": finding.decomposition,
                "subject": finding.subject,
                "reference": finding.reference,
                "trajectory": finding.trajectory,
                "materiality": finding.materiality,
                "materiality_reasons": finding.materiality_reasons,
                "should_surface": finding.should_surface,
                "structured_evidence": finding.structured_evidence,
                "causes": finding.causes,
                "data_quality": finding.data_quality,
            }
            for finding in intelligence.findings
        ],
    }


@router.put("/allocation-policy")
def set_allocation_policy(policy: AllocationPolicyInput) -> dict[str, str]:
    try:
        session.set_allocation_policy(AllocationPolicy(targets=policy.targets))
        rebuild_portfolio_dashboard_snapshot()
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {"status": "updated"}


@router.put("/asset-allocation-policy")
def set_asset_allocation_policy(policy: AssetAllocationPolicyInput) -> dict[str, str]:
    try:
        session.set_asset_allocation_policy(AssetAllocationPolicy(targets=policy.targets))
        rebuild_portfolio_dashboard_snapshot()
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {"status": "updated"}


@router.get("/portfolio/allocation-analysis")
def get_allocation_analysis(as_of: date | None = None) -> dict[str, object]:
    try:
        analysis = session.allocation_analysis(as_of=as_of)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {
        "portfolio_drift": analysis.portfolio_drift,
        "portfolio_drift_value": analysis.portfolio_drift_value.amount,
        "comparisons": [
            {
                "asset_class": item.asset_class,
                "current_weight": item.current_weight,
                "target_weight": item.target_weight,
                "deviation": item.deviation,
                "value_deviation": item.value_deviation.amount,
                "status": item.status,
            }
            for item in analysis.comparisons
        ],
    }


@router.get("/portfolio/rebalancing")
def get_rebalancing(as_of: date | None = None) -> dict[str, object]:
    try:
        plan = session.rebalancing(as_of=as_of)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {
        "mode": "FULL_REBALANCING",
        "total_excess": plan.total_excess.amount,
        "total_deficit": plan.total_deficit.amount,
        "classes": [
            {
                "asset_class": item.asset_class,
                "excess_value": max(item.value_deviation.amount, Decimal("0")),
                "deficit_value": max(-item.value_deviation.amount, Decimal("0")),
                "status": item.status,
            }
            for item in plan.analysis.comparisons
        ],
    }


@router.post("/portfolio/rebalancing/contribution-only")
def simulate_contribution_rebalancing(simulation: ContributionSimulationInput) -> dict[str, object]:
    try:
        plan = session.rebalancing()
        allocations = plan.contribution_only(Money(simulation.amount))
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return {
        "mode": "CONTRIBUTION_ONLY_REBALANCING",
        "contribution": simulation.amount,
        "allocations": [
            {"asset_class": asset_class, "simulated_amount": amount.amount}
            for asset_class, amount in allocations
        ],
        "notice": "Simulação analítica; nenhuma ordem será executada.",
    }


@router.post("/portfolio/simulation/contribution")
def project_hypothetical_contribution(simulation: ContributionSimulationInput) -> dict[str, object]:
    """Return a non-persistent before/scenario/after projection in base currency."""
    try:
        projection = session.hypothetical_contribution(
            amount=simulation.amount, allocation_mode=simulation.mode
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error

    detail_by_class = (
        {item.asset_class: item for item in projection.scenario.class_details}
        if simulation.include_asset_distribution
        else {}
    )

    def state(value: object) -> dict[str, object]:
        portfolio_state = value
        return {
            "as_of": portfolio_state.as_of,
            "base_currency": portfolio_state.base_currency,
            "invested_wealth": portfolio_state.invested_wealth,
            "strategy_distance": portfolio_state.strategy_distance,
            "valuation_status": portfolio_state.valuation_status,
            "issues": portfolio_state.issues,
            "class_allocations": [
                {
                    "asset_class": item.asset_class,
                    "current_value": item.current_value,
                    "weight": item.weight,
                    "target_weight": item.target_weight,
                    "gap_pp": item.gap_pp,
                }
                for item in portfolio_state.class_allocations
            ],
        }

    return {
        "status": projection.status,
        "issues": projection.issues,
        "before": state(projection.before),
        "scenario": {
            "scenario_type": projection.scenario.scenario_type,
            "allocation_mode": projection.scenario.allocation_mode,
            "contribution_amount": projection.scenario.contribution_amount,
            "base_currency": projection.scenario.base_currency,
            "allocated_amount": projection.scenario.allocated_amount,
            "unallocated_amount": projection.scenario.unallocated_amount,
            "class_allocations": [
                {
                    "asset_class": asset_class,
                    "amount": amount,
                    **(
                        {
                            "asset_distribution_status": (
                                detail_by_class[asset_class].asset_distribution_status
                            ),
                            "asset_distributed_amount": (
                                detail_by_class[asset_class].asset_distributed_amount
                            ),
                            "undistributed_within_class": (
                                detail_by_class[asset_class].undistributed_within_class
                            ),
                            "asset_composition_distance_before": (
                                detail_by_class[asset_class].asset_composition_distance_before
                            ),
                            "asset_composition_distance_after": (
                                detail_by_class[asset_class].asset_composition_distance_after
                            ),
                            "asset_composition_distance_change": (
                                detail_by_class[asset_class].asset_composition_distance_change
                            ),
                            "asset_allocations": [
                                {
                                    "asset_id": asset.asset_id,
                                    "asset_label": asset.asset_label,
                                    "amount": asset.amount,
                                    "value_before": asset.value_before,
                                    "value_after": asset.value_after,
                                    "weight_before_in_class": asset.weight_before_in_class,
                                    "weight_after_in_class": asset.weight_after_in_class,
                                    "target_weight_in_class": asset.target_weight_in_class,
                                    "gap_before_pp": asset.gap_before_pp,
                                    "gap_after_pp": asset.gap_after_pp,
                                    "reason_code": asset.reason_code,
                                }
                                for asset in detail_by_class[asset_class].asset_allocations
                            ],
                        }
                        if asset_class in detail_by_class
                        else {}
                    ),
                }
                for asset_class, amount in projection.scenario.class_allocations
            ],
            "class_reason_codes": [
                {"asset_class": asset_class, "reason_code": reason_code}
                for asset_class, reason_code in projection.scenario.class_reason_codes
            ],
        },
        "after": state(projection.after),
        "comparison": {
            "wealth_before": projection.comparison.wealth_before,
            "invested_wealth_after": projection.comparison.invested_wealth_after,
            "wealth_change": projection.comparison.wealth_change,
            "strategy_distance_before": projection.comparison.strategy_distance_before,
            "strategy_distance_after": projection.comparison.strategy_distance_after,
            "strategy_distance_change": projection.comparison.strategy_distance_change,
            "class_changes": [
                {
                    "asset_class": item.asset_class,
                    "weight_before": item.weight_before,
                    "weight_after": item.weight_after,
                    "target_weight": item.target_weight,
                    "weight_change_pp": item.weight_change_pp,
                    "gap_before_pp": item.gap_before_pp,
                    "gap_after_pp": item.gap_after_pp,
                }
                for item in projection.comparison.class_changes
            ],
        },
        "notice": "Simulação analítica; nenhuma ordem será executada.",
    }


@router.post("/portfolio/rebalancing/assets")
def simulate_asset_rebalancing(simulation: AssetRebalancingInput) -> dict[str, object]:
    allocations = session.asset_rebalancing(
        asset_class=simulation.asset_class,
        amount=simulation.amount,
        strategy=simulation.strategy,
    )
    return {
        "strategy": simulation.strategy,
        "allocations": [
            {"ticker": ticker, "simulated_amount": amount.amount} for ticker, amount in allocations
        ],
        "notice": "Simulação analítica; nenhuma ordem será executada.",
    }


@router.get("/portfolio/history")
def get_portfolio_history(
    period_months: int = 12,
    asset_class: AssetClass | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, object]:
    """Return a bounded, period-aggregated evolution series for the dashboard."""
    allowed_periods = {1, 3, 6, 12, 36, 60, 120, 0}
    if period_months not in allowed_periods:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Período inválido.",
        )
    observed_dates = sorted(
        {event.effective_date for event in session._events}
        | {price.effective_date for price in session._market_prices}
    )
    if start_date is not None or end_date is not None:
        requested_start_date = start_date or date.min
        effective_end_date = _effective_analysis_end_date(
            requested_start_date, end_date or date.today()
        )
        observed_dates = [
            item
            for item in observed_dates
            if (start_date is None or item >= start_date) and item <= effective_end_date
        ]
    if observed_dates and period_months:
        end = observed_dates[-1]
        month_index = end.year * 12 + end.month - period_months + 1
        start = date(month_index // 12, (month_index % 12) + 1, 1)
        observed_dates = [item for item in observed_dates if item >= start]
    granularity = "year" if period_months >= 36 or period_months == 0 else "month"
    buckets = {}
    for effective_date in observed_dates:
        key = (
            str(effective_date.year) if granularity == "year" else effective_date.strftime("%Y-%m")
        )
        buckets[key] = effective_date

    snapshots = tuple(
        PortfolioSnapshot(
            effective_date=effective_date,
            portfolio=PortfolioProjector.project_as_of(
                session._events,
                session._market_prices_for_projection(
                    as_of=effective_date, include_fixed_income=False
                ),
                effective_date,
                market_data_available=bool(session._market_prices),
            ),
        )
        for effective_date in buckets.values()
    )

    boundary = PortfolioHistoryBoundary.from_observed_events(session.history())
    opening_equity_reliable = boundary.has_reliable_opening_equity

    def serialize(snapshot: PortfolioSnapshot) -> dict[str, object]:
        portfolio = snapshot.portfolio
        positions = tuple(
            position
            for position in portfolio.positions
            if asset_class is None or position.asset.asset_class is asset_class
        )
        if asset_class is None:
            market_value = (
                portfolio.total_market_value.amount if portfolio.has_complete_market_data else None
            )
            total_result = portfolio.total_result.amount
            capital_gain = (
                portfolio.total_realized_result.amount + portfolio.total_unrealized_result.amount
            )
            total_cost = portfolio.total_cost.amount
            cash = portfolio.cash.amount if opening_equity_reliable else None
            reconstructed_cash_effect = portfolio.cash.amount
        else:
            complete = all(position.current_price is not None for position in positions)
            market_value = (
                sum((position.market_value.amount for position in positions), Decimal("0"))
                if complete
                else None
            )
            total_result = sum(
                (position.total_result.amount for position in positions), Decimal("0")
            )
            capital_gain = sum(
                (
                    position.realized_result.amount + position.unrealized_result.amount
                    for position in positions
                ),
                Decimal("0"),
            )
            total_cost = sum((position.cost.amount for position in positions), Decimal("0"))
            cash = Decimal("0")
            reconstructed_cash_effect = Decimal("0")
        return {
            "effective_date": snapshot.effective_date,
            "total_cost": total_cost,
            "market_value": market_value,
            "total_result": total_result,
            "capital_gain": capital_gain,
            "cash": cash,
            "reconstructed_cash_effect": reconstructed_cash_effect,
        }

    return {
        "history_boundary": boundary.as_payload(),
        "cash_status": boundary.opening_cash_status.value,
        "requested_start_date": start_date,
        "requested_end_date": end_date,
        "effective_end_date": min(end_date or date.today(), date.today()),
        "period_months": period_months,
        "asset_class": asset_class.value if asset_class else None,
        "granularity": granularity,
        "snapshots": [serialize(snapshot) for snapshot in snapshots],
    }


@router.post("/data/reset", status_code=status.HTTP_200_OK, response_class=Response)
def reset_all_data(reset: DataResetInput) -> None:
    """Purge user portfolio data while preserving schema and provider health."""
    session.clear()
