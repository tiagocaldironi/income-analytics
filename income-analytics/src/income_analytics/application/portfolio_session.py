"""In-memory portfolio session used by the local MVP interface."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from income_analytics.application.base_currency_valuation import (
    MAX_FX_STALE_AGE_DAYS,
    BaseCurrencyValuation,
    BaseCurrencyValuationProjector,
)
from income_analytics.application.benchmark_data import BenchmarkDataProvider, BenchmarkObservation
from income_analytics.application.fixed_income_valuation import FixedIncomeValuationEngine
from income_analytics.application.fx_data import FxRateObservation, FxRateProvider
from income_analytics.application.market_data import (
    MarketDataProvider,
    MarketDataUnavailable,
    MarketPriceObservation,
)
from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.asset_allocation_policy import AssetAllocationPolicy
from income_analytics.domain.benchmark_rate import BenchmarkRate
from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.entities.currency import Currency
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.entities.institution import Institution
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.enums.capital_flow_type import CapitalFlowType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)
from income_analytics.domain.enums.valuation_method import ValuationMethod
from income_analytics.domain.fixed_income_details import FixedIncomeDetails
from income_analytics.domain.market_price import MarketPrice
from income_analytics.domain.projectors.allocation_analysis_projector import (
    AllocationAnalysisProjector,
)
from income_analytics.domain.projectors.allocation_projector import AllocationProjector
from income_analytics.domain.projectors.asset_rebalancing_projector import (
    AssetAllocationStrategy,
    AssetRebalancingProjector,
)
from income_analytics.domain.projectors.benchmark_comparison_projector import (
    BenchmarkComparisonProjector,
)
from income_analytics.domain.projectors.class_allocation_projector import ClassAllocationProjector
from income_analytics.domain.projectors.contribution_target_allocator import (
    ContributionTargetAllocator,
)
from income_analytics.domain.projectors.diversification_projector import DiversificationProjector
from income_analytics.domain.projectors.hypothetical_portfolio_projector import (
    HypotheticalPortfolioProjector,
)
from income_analytics.domain.projectors.performance_projector import PerformanceProjector
from income_analytics.domain.projectors.portfolio_diagnostic_engine import (
    PortfolioDiagnosticEngine,
)
from income_analytics.domain.projectors.portfolio_projector import PortfolioProjector
from income_analytics.domain.projectors.risk_contribution_projector import (
    RiskContributionProjector,
)
from income_analytics.domain.projectors.risk_projector import RiskProjector
from income_analytics.domain.read_models.allocation_analysis import PortfolioAllocationAnalysis
from income_analytics.domain.read_models.allocation_projection import AllocationProjection
from income_analytics.domain.read_models.benchmark_comparison_projection import (
    BenchmarkComparisonProjection,
)
from income_analytics.domain.read_models.class_allocation_projection import (
    ClassAllocationProjection,
)
from income_analytics.domain.read_models.diversification_projection import DiversificationProjection
from income_analytics.domain.read_models.hypothetical_portfolio_projection import (
    HypotheticalPortfolioProjection,
    SimulationAssetContribution,
    SimulationClassContribution,
)
from income_analytics.domain.read_models.performance_projection import PerformanceProjection
from income_analytics.domain.read_models.portfolio_history import PortfolioHistory
from income_analytics.domain.read_models.portfolio_intelligence import PortfolioIntelligence
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection
from income_analytics.domain.read_models.rebalancing_projection import RebalancingProjection
from income_analytics.domain.read_models.risk_contribution_projection import (
    RiskContributionProjection,
)
from income_analytics.domain.read_models.risk_projection import RiskProjection
from income_analytics.domain.recurring_rule import RecurrenceFrequency, RecurringRule
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from income_analytics.domain.value_objects.ticker import Ticker
from income_analytics.domain.wealth_details import PensionPlanDetails, RealEstateDetails
from income_analytics.infrastructure.database import initialize_database
from income_analytics.infrastructure.sqlite_repositories import (
    SqliteAllocationPolicyRepository,
    SqliteAssetAllocationPolicyRepository,
    SqliteAssetRepository,
    SqliteBenchmarkObservationRepository,
    SqliteBenchmarkRateRepository,
    SqliteFinancialEventRepository,
    SqliteFixedIncomeDetailsRepository,
    SqliteFxRateRepository,
    SqliteMarketPriceRepository,
    SqlitePensionPlanDetailsRepository,
    SqlitePortfolioConfigurationRepository,
    SqlitePortfolioDataRepository,
    SqlitePortfolioRepository,
    SqliteRealEstateDetailsRepository,
    SqliteRecurringRuleRepository,
)

DEFAULT_EFFECTIVE_DATE = date(2026, 1, 1)


@dataclass(slots=True)
class PortfolioSession:
    """Keeps a local, non-persistent event stream for the dashboard."""

    portfolio_id: UUID
    account_id: UUID = field(default_factory=uuid4)
    persistent: bool = False
    _assets: dict[str, Asset] = field(default_factory=dict, init=False)
    _events: list[FinancialEvent] = field(default_factory=list, init=False)
    _market_prices: list[MarketPrice] = field(default_factory=list, init=False)
    _market_prices_by_asset: dict[UUID, tuple[MarketPrice, ...]] = field(
        default_factory=dict, init=False
    )
    _market_prices_indexed_source: list[MarketPrice] | None = field(
        default=None, init=False, repr=False
    )
    _market_prices_indexed_length: int = field(default=0, init=False, repr=False)
    _fx_rate_cache: dict[tuple[str, str], tuple[FxRateObservation, ...]] = field(
        default_factory=dict, init=False
    )
    _benchmark_rates: list[BenchmarkRate] = field(default_factory=list, init=False)
    _benchmark_observations: dict[str, list[BenchmarkObservation]] = field(
        default_factory=dict, init=False
    )
    _base_currency: str = field(default="BRL", init=False)
    _allocation_policy: AllocationPolicy | None = field(default=None, init=False)
    _asset_allocation_policy: AssetAllocationPolicy | None = field(default=None, init=False)
    _fixed_income_details: dict[UUID, FixedIncomeDetails] = field(default_factory=dict, init=False)
    _pension_plan_details: dict[UUID, PensionPlanDetails] = field(default_factory=dict, init=False)
    _real_estate_details: dict[UUID, RealEstateDetails] = field(default_factory=dict, init=False)
    _recurring_rules: dict[UUID, RecurringRule] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.persistent:
            initialize_database()
            if SqlitePortfolioRepository().get(self.portfolio_id) is None:
                raise ValueError(f"Portfolio not found: {self.portfolio_id}")
            self._assets = {
                str(asset.ticker): asset
                for asset in SqliteAssetRepository(self.portfolio_id).list()
            }
            self._events = list(SqliteFinancialEventRepository(self.portfolio_id).list())
            market_prices = SqliteMarketPriceRepository()
            self._market_prices = list(market_prices.list())
            self._market_prices_by_asset = market_prices.list_by_asset()
            self._market_prices_indexed_source = self._market_prices
            self._market_prices_indexed_length = len(self._market_prices)
            self._benchmark_rates = list(SqliteBenchmarkRateRepository().list())
            observations = SqliteBenchmarkObservationRepository()
            self._benchmark_observations = {
                name: list(observations.list(name))
                for name in ("IPCA", "IBOV", "TR", "SELIC_TARGET")
            }
            self._allocation_policy = SqliteAllocationPolicyRepository(self.portfolio_id).get()
            self._asset_allocation_policy = SqliteAssetAllocationPolicyRepository(
                self.portfolio_id
            ).get()
            self._base_currency = SqlitePortfolioConfigurationRepository(
                self.portfolio_id
            ).get_base_currency()
            self._fixed_income_details = {
                details.asset_id: details
                for details in SqliteFixedIncomeDetailsRepository(self.portfolio_id).list()
            }
            self._pension_plan_details = {
                details.asset_id: details
                for details in SqlitePensionPlanDetailsRepository(self.portfolio_id).list()
            }
            self._real_estate_details = {
                details.asset_id: details
                for details in SqliteRealEstateDetailsRepository(self.portfolio_id).list()
            }
            self._recurring_rules = {
                rule.id: rule for rule in SqliteRecurringRuleRepository(self.portfolio_id).list()
            }

    def register_trade(
        self,
        *,
        event_type: FinancialEventType,
        ticker: str,
        name: str | None = None,
        asset_class: AssetClass = AssetClass.OTHER,
        country: str = "BR",
        currency_code: str = "BRL",
        sector: str | None = None,
        quantity: Decimal,
        unit_price: Decimal,
        effective_date: date = DEFAULT_EFFECTIVE_DATE,
        capital_flow_type: CapitalFlowType = CapitalFlowType.UNKNOWN,
        source_asset_class: AssetClass | None = None,
        destination_asset_class: AssetClass | None = None,
    ) -> PortfolioProjection:
        """Register a trade only when it can be applied to the current portfolio."""
        normalized_ticker = ticker.strip().upper()
        asset = self._assets.get(normalized_ticker)
        if asset is None:
            asset = (
                SqliteAssetRepository(self.portfolio_id).get_by_ticker(normalized_ticker)
                if self.persistent
                else None
            )
            shared_asset = asset is not None
            if asset is None:
                asset = self._create_asset(
                    normalized_ticker,
                    name=name or normalized_ticker,
                    asset_class=asset_class,
                    country=country,
                    currency_code=currency_code,
                    sector=sector,
                )
            self._assets[normalized_ticker] = asset
            if self.persistent:
                repository = SqliteAssetRepository(self.portfolio_id)
                repository.link(asset.id) if shared_asset else repository.save(asset)
        elif event_type is FinancialEventType.BUY and asset.asset_class is not asset_class:
            self._reclassify_market_traded_asset(asset, asset_class)

        event = FinancialEvent(
            account_id=self.account_id,
            asset=asset,
            event_type=event_type,
            occurred_at=datetime.now(UTC),
            effective_date=effective_date,
            quantity=Quantity(quantity),
            unit_price=Money(unit_price),
            metadata={
                "capital_flow_type": capital_flow_type.value,
                "source_asset_class": source_asset_class.value if source_asset_class else None,
                "destination_asset_class": (
                    destination_asset_class.value if destination_asset_class else None
                ),
            },
        )

        candidate_events = [*self._events, event]
        projection = PortfolioProjector.project(
            candidate_events,
            market_prices=self._market_prices_for_projection(as_of=effective_date),
            market_data_available=bool(self._market_prices or self._fixed_income_details),
        )
        self._events.append(event)
        if self.persistent:
            SqliteFinancialEventRepository(self.portfolio_id).save(event)
        return projection

    def project(self, *, as_of: date | None = None) -> PortfolioProjection:
        return PortfolioProjector.project(
            self._events,
            market_prices=self._market_prices_for_projection(as_of=as_of),
            as_of=as_of,
            market_data_available=bool(self._market_prices or self._fixed_income_details),
        )

    def register_income(
        self,
        *,
        event_type: FinancialEventType,
        asset: Asset,
        amount: Decimal,
        effective_date: date,
        description: str | None = None,
    ) -> FinancialEvent:
        event = FinancialEvent(
            account_id=self.account_id,
            asset=asset,
            event_type=event_type,
            occurred_at=datetime.now(UTC),
            effective_date=effective_date,
            amount=Money(amount),
            description=description,
        )
        self._events.append(event)
        if self.persistent:
            SqliteFinancialEventRepository(self.portfolio_id).save(event)
        return event

    def register_asset(
        self,
        *,
        ticker: str,
        name: str,
        asset_class: AssetClass,
        country: str = "BR",
        currency_code: str = "BRL",
        sector: str | None = None,
    ) -> Asset:
        normalized_ticker = ticker.strip().upper()
        if normalized_ticker in self._assets:
            return self._assets[normalized_ticker]
        asset = (
            SqliteAssetRepository(self.portfolio_id).get_by_ticker(normalized_ticker)
            if self.persistent
            else None
        )
        shared_asset = asset is not None
        if asset is None:
            asset = self._create_asset(
                normalized_ticker,
                name=name,
                asset_class=asset_class,
                country=country,
                currency_code=currency_code,
                sector=sector,
            )
        self._assets[normalized_ticker] = asset
        if self.persistent:
            repository = SqliteAssetRepository(self.portfolio_id)
            repository.link(asset.id) if shared_asset else repository.save(asset)
        return asset

    def register_fixed_income_asset(
        self,
        *,
        ticker: str,
        name: str,
        instrument_type: FixedIncomeInstrumentType,
        indexer_type: FixedIncomeIndexerType,
        application_date: date,
        principal_amount: Decimal,
        issuer: str | None = None,
        contracted_rate: Decimal | None = None,
        percentage_of_indexer: Decimal | None = None,
        spread: Decimal | None = None,
        maturity_date: date | None = None,
        liquidity_type: str | None = None,
        tax_exempt: bool = False,
    ) -> Asset:
        """Register a fixed-income instrument and its initial principal event.

        The asset master remains generic; the contract data is persisted in its
        dedicated aggregate so valuation never depends on UI-only fields.
        """
        normalized_ticker = ticker.strip().upper()
        if normalized_ticker in self._assets:
            raise ValueError("Já existe um ativo com esse identificador.")
        self._ensure_private_ticker_available(normalized_ticker)
        asset = self._create_asset(
            normalized_ticker,
            name=name,
            asset_class=AssetClass.FIXED_INCOME,
            asset_type=(
                AssetType.SAVINGS_ACCOUNT
                if instrument_type is FixedIncomeInstrumentType.SAVINGS_ACCOUNT
                else AssetType.FIXED_INCOME
            ),
            valuation_method=ValuationMethod.CONTRACT_CURVE,
        )
        details = FixedIncomeDetails(
            asset_id=asset.id,
            instrument_type=instrument_type,
            indexer_type=indexer_type,
            issuer=issuer,
            contracted_rate=contracted_rate,
            percentage_of_indexer=percentage_of_indexer,
            spread=spread,
            application_date=application_date,
            maturity_date=maturity_date,
            principal_amount=principal_amount,
            liquidity_type=liquidity_type,
            tax_exempt=tax_exempt,
        )
        event = FinancialEvent(
            account_id=self.account_id,
            asset=asset,
            event_type=FinancialEventType.BUY,
            occurred_at=datetime.now(UTC),
            effective_date=application_date,
            quantity=Quantity(Decimal("1")),
            unit_price=Money(principal_amount),
            description="Aplicação inicial de renda fixa",
        )
        self._assets[normalized_ticker] = asset
        self._fixed_income_details[asset.id] = details
        self._events.append(event)
        if self.persistent:
            SqliteAssetRepository(self.portfolio_id).save(asset)
            SqliteFixedIncomeDetailsRepository(self.portfolio_id).save(details)
            SqliteFinancialEventRepository(self.portfolio_id).save(event)
        return asset

    def fixed_income_details(self, ticker: str) -> FixedIncomeDetails:
        asset = self._assets.get(ticker.strip().upper())
        if asset is None or asset.id not in self._fixed_income_details:
            raise ValueError("Ativo de renda fixa não encontrado.")
        return self._fixed_income_details[asset.id]

    def register_pension_plan(
        self,
        *,
        institution: str,
        institution_cnpj: str | None = None,
        plan_name: str,
        tax_regime: str,
        start_date: date,
        reported_balance: Decimal,
        reported_balance_date: date,
        ticker: str | None = None,
        name: str | None = None,
        pension_type: str = "OUTRO",
        ownership_origin: str = "PARTICULAR",
        pension_system_type: str = "OPEN",
        product_type: str | None = None,
        closed_plan_modality: str | None = None,
        sponsor_name: str | None = None,
        sponsor_cnpj: str | None = None,
        susep_process_number: str | None = None,
        cnpb: str | None = None,
        participant_balance: Decimal | None = None,
        sponsor_balance: Decimal | None = None,
        employer_match_enabled: bool | None = None,
        employer_match_rate: Decimal | None = None,
        match_limit: Decimal | None = None,
        match_rule_notes: str | None = None,
        vesting_enabled: bool | None = None,
        current_vested_percentage: Decimal | None = None,
        vesting_rule_notes: str | None = None,
        status: str = "ACTIVE",
    ) -> Asset:
        normalized_ticker = (ticker or f"PENSION-{uuid4().hex[:12]}").strip().upper()
        if normalized_ticker in self._assets:
            raise ValueError("Já existe um ativo com esse identificador.")
        self._ensure_private_ticker_available(normalized_ticker)
        asset = self._create_asset(
            normalized_ticker,
            name=name or plan_name,
            asset_class=AssetClass.PENSION,
            asset_type=AssetType.PENSION,
            valuation_method=ValuationMethod.REPORTED_BALANCE,
        )
        details = PensionPlanDetails(
            asset_id=asset.id,
            pension_type=pension_type,
            institution=institution,
            institution_cnpj=institution_cnpj,
            plan_name=plan_name,
            tax_regime=tax_regime,
            start_date=start_date,
            reported_balance=reported_balance,
            reported_balance_date=reported_balance_date,
            ownership_origin=ownership_origin,
            pension_system_type=pension_system_type,
            product_type=product_type,
            closed_plan_modality=closed_plan_modality,
            sponsor_name=sponsor_name,
            sponsor_cnpj=sponsor_cnpj,
            susep_process_number=susep_process_number,
            cnpb=cnpb,
            participant_balance=participant_balance,
            sponsor_balance=sponsor_balance,
            employer_match_enabled=employer_match_enabled,
            employer_match_rate=employer_match_rate,
            match_limit=match_limit,
            match_rule_notes=match_rule_notes,
            vesting_enabled=vesting_enabled,
            current_vested_percentage=current_vested_percentage,
            vesting_rule_notes=vesting_rule_notes,
            status=status,
        )
        self._register_balance_asset(asset, details.reported_balance, details.reported_balance_date)
        self._pension_plan_details[asset.id] = details
        if self.persistent:
            SqlitePensionPlanDetailsRepository(self.portfolio_id).save(details)
        return asset

    def register_real_estate(
        self,
        *,
        ticker: str,
        name: str,
        property_type: str,
        description: str,
        cep: str,
        current_manual_value: Decimal,
        valuation_date: date,
        country: str = "BR",
        city: str | None = None,
        state: str | None = None,
        acquisition_date: date | None = None,
        acquisition_value: Decimal | None = None,
        ownership_percentage: Decimal = Decimal("100"),
    ) -> Asset:
        normalized_ticker = ticker.strip().upper()
        if normalized_ticker in self._assets:
            raise ValueError("Já existe um ativo com esse identificador.")
        self._ensure_private_ticker_available(normalized_ticker)
        asset = self._create_asset(
            normalized_ticker,
            name=name,
            asset_class=AssetClass.REAL_ESTATE,
            asset_type=AssetType.REAL_ESTATE,
            valuation_method=ValuationMethod.MANUAL_ESTIMATE,
        )
        details = RealEstateDetails(
            asset_id=asset.id,
            property_type=property_type,
            description=description,
            cep=cep,
            country=country,
            city=city,
            state=state,
            acquisition_date=acquisition_date,
            acquisition_value=acquisition_value,
            ownership_percentage=ownership_percentage,
            current_manual_value=current_manual_value,
            valuation_date=valuation_date,
        )
        purchase_value = (
            details.acquisition_value * details.ownership_percentage / Decimal("100")
            if details.acquisition_value is not None
            else details.portfolio_value
        )
        purchase_date = details.acquisition_date or details.valuation_date
        self._register_balance_asset(asset, purchase_value, purchase_date)
        if details.portfolio_value != purchase_value or details.valuation_date != purchase_date:
            current_value = MarketPrice(
                asset=asset,
                price=Money(details.portfolio_value),
                effective_date=details.valuation_date,
            )
            self._market_prices.append(current_value)
            self._remember_market_price(current_value)
            if self.persistent:
                SqliteMarketPriceRepository().save(current_value)
        self._real_estate_details[asset.id] = details
        if self.persistent:
            SqliteRealEstateDetailsRepository(self.portfolio_id).save(details)
        return asset

    def _register_balance_asset(self, asset: Asset, value: Decimal, effective_date: date) -> None:
        event = FinancialEvent(
            account_id=self.account_id,
            asset=asset,
            event_type=FinancialEventType.BUY,
            occurred_at=datetime.now(UTC),
            effective_date=effective_date,
            quantity=Quantity(Decimal("1")),
            unit_price=Money(value),
        )
        self._assets[str(asset.ticker)] = asset
        self._events.append(event)
        reference_value = MarketPrice(
            asset=asset, price=Money(value), effective_date=effective_date
        )
        self._market_prices.append(reference_value)
        self._remember_market_price(reference_value)
        if self.persistent:
            SqliteAssetRepository(self.portfolio_id).save(asset)
            SqliteFinancialEventRepository(self.portfolio_id).save(event)
            SqliteMarketPriceRepository().save(reference_value)

    def projection(self, *, as_of: date | None = None) -> PortfolioProjection:
        """Return the portfolio state represented by the registered event stream."""
        return PortfolioProjector.project(
            self._events,
            market_prices=self._market_prices_for_projection(as_of=as_of),
            as_of=as_of,
            market_data_available=bool(self._market_prices or self._fixed_income_details),
        )

    def projections_at(self, effective_dates: tuple[date, ...]) -> tuple[PortfolioProjection, ...]:
        """Build dated portfolio projections with one chronological ledger replay."""
        self._ensure_market_price_index_current()
        dates = tuple(sorted(set(effective_dates)))
        curve_prices = tuple(
            price
            for effective_date in dates
            for price in self._fixed_income_valuation_prices(effective_date)
        )
        return PortfolioProjector.project_timeline(
            self._events,
            (*self._market_prices, *curve_prices),
            dates,
            market_data_available=bool(self._market_prices or self._fixed_income_details),
        )

    @property
    def base_currency(self) -> str:
        return self._base_currency

    def set_base_currency(self, currency: str) -> str:
        normalized = currency.strip().upper()
        if normalized != "BRL":
            raise ValueError("A moeda-base disponível nesta versão é BRL.")
        self._base_currency = normalized
        self._fx_rate_cache.clear()
        if self.persistent:
            SqlitePortfolioConfigurationRepository(self.portfolio_id).save_base_currency(normalized)
        return normalized

    def refresh_fx_rate(
        self,
        provider: FxRateProvider,
        *,
        base_currency: str,
        quote_currency: str,
        effective_date: date,
    ) -> FxRateObservation:
        observation = provider.rate_on(base_currency, quote_currency, effective_date)
        if self.persistent:
            SqliteFxRateRepository().save(observation)
            self._remember_fx_rate(observation)
        return observation

    def import_fx_rate_history(self, observations: tuple[FxRateObservation, ...]) -> int:
        repository = SqliteFxRateRepository()
        repository.save_many(observations)
        for observation in observations:
            self._remember_fx_rate(observation)
        return len(observations)

    def base_currency_valuation(
        self,
        *,
        as_of: date | None = None,
        projection: PortfolioProjection | None = None,
    ) -> BaseCurrencyValuation:
        effective_date = as_of or date.today()
        currencies = {asset.currency.code.upper() for asset in self._assets.values()} - {
            self._base_currency
        }
        rates = (
            tuple(
                rate
                for currency in currencies
                for rate in self._fx_rates(currency, self._base_currency)
                if rate.effective_date <= effective_date
            )
            if self.persistent
            else ()
        )
        return BaseCurrencyValuationProjector.project(
            projection or self.projection(as_of=as_of),
            base_currency=self._base_currency,
            fx_rates=rates,
            as_of=effective_date,
        )

    def _fx_rates(self, base_currency: str, quote_currency: str) -> tuple[FxRateObservation, ...]:
        key = (base_currency.upper(), quote_currency.upper())
        if key not in self._fx_rate_cache:
            self._fx_rate_cache[key] = (
                SqliteFxRateRepository().list(*key) if self.persistent else ()
            )
        return self._fx_rate_cache[key]

    def historical_fx_rates(
        self, base_currencies: Iterable[str], quote_currency: str
    ) -> tuple[FxRateObservation, ...]:
        """Return persisted FX history needed to express costs in portfolio currency."""
        if not self.persistent:
            return ()
        return tuple(
            observation
            for currency in sorted({item.upper() for item in base_currencies})
            if currency.upper() != quote_currency.upper()
            for observation in self._fx_rates(currency, quote_currency)
        )

    def _remember_fx_rate(self, observation: FxRateObservation) -> None:
        key = (observation.base_currency.upper(), observation.quote_currency.upper())
        rates = {item.effective_date: item for item in self._fx_rate_cache.get(key, ())}
        rates[observation.effective_date] = observation
        self._fx_rate_cache[key] = tuple(rates[day] for day in sorted(rates))

    def register_dividend(
        self,
        *,
        ticker: str,
        amount: Decimal,
        effective_date: date = DEFAULT_EFFECTIVE_DATE,
    ) -> PortfolioProjection:
        """Register income received for an asset already known by this session."""
        asset = self._assets.get(ticker.strip().upper())
        if asset is None:
            raise ValueError("Ativo não encontrado na carteira local.")

        event = FinancialEvent(
            account_id=self.account_id,
            asset=asset,
            event_type=FinancialEventType.DIVIDEND,
            occurred_at=datetime.now(UTC),
            effective_date=effective_date,
            amount=Money(amount),
        )
        projection = PortfolioProjector.project(
            [*self._events, event],
            market_prices=self._market_prices_for_projection(as_of=effective_date),
            market_data_available=bool(self._market_prices),
        )
        self._events.append(event)
        if self.persistent:
            SqliteFinancialEventRepository(self.portfolio_id).save(event)
        return projection

    def register_external_flow(
        self,
        *,
        event_type: FinancialEventType,
        amount: Decimal,
        effective_date: date = DEFAULT_EFFECTIVE_DATE,
        capital_flow_type: CapitalFlowType = CapitalFlowType.EXTERNAL_CAPITAL,
    ) -> PortfolioProjection:
        """Register an investor contribution or withdrawal without an asset."""
        if event_type not in (FinancialEventType.DEPOSIT, FinancialEventType.WITHDRAWAL):
            raise ValueError("O fluxo externo deve ser um aporte ou uma retirada.")
        event = FinancialEvent(
            account_id=self.account_id,
            event_type=event_type,
            occurred_at=datetime.now(UTC),
            effective_date=effective_date,
            amount=Money(amount),
            metadata={"capital_flow_type": capital_flow_type.value},
        )
        projection = PortfolioProjector.project(
            [*self._events, event],
            market_prices=self._market_prices_for_projection(as_of=effective_date),
            market_data_available=bool(self._market_prices),
        )
        self._events.append(event)
        if self.persistent:
            SqliteFinancialEventRepository(self.portfolio_id).save(event)
        return projection

    def schedule_recurring_rule(self, rule: RecurringRule) -> None:
        """Persist an instruction only; it never creates a future event early."""
        if rule.asset_id is not None and not any(
            asset.id == rule.asset_id for asset in self._assets.values()
        ):
            raise ValueError("Ativo da recorrência não encontrado na carteira local.")
        self._recurring_rules[rule.id] = rule
        if self.persistent:
            SqliteRecurringRuleRepository(self.portfolio_id).save(rule)

    def execute_recurring_rules(self, *, through: date) -> tuple[UUID, ...]:
        """Execute each due occurrence exactly once by advancing its stored cursor."""
        executed: list[UUID] = []
        for rule in tuple(self._recurring_rules.values()):
            while (
                rule.active
                and rule.next_execution_date <= through
                and (
                    rule.end_execution_date is None
                    or rule.next_execution_date <= rule.end_execution_date
                )
            ):
                if rule.event_type is FinancialEventType.DIVIDEND:
                    asset = next(
                        asset for asset in self._assets.values() if asset.id == rule.asset_id
                    )
                    self.register_dividend(
                        ticker=str(asset.ticker),
                        amount=rule.amount,
                        effective_date=rule.next_execution_date,
                    )
                else:
                    self.register_external_flow(
                        event_type=rule.event_type,
                        amount=rule.amount,
                        effective_date=rule.next_execution_date,
                    )
                rule = rule.advance()
                self._recurring_rules[rule.id] = rule
                if self.persistent:
                    SqliteRecurringRuleRepository(self.portfolio_id).save(rule)
                executed.append(rule.id)
            if (
                rule.active
                and rule.end_execution_date is not None
                and rule.next_execution_date > rule.end_execution_date
            ):
                rule = replace(rule, active=False)
                self._recurring_rules[rule.id] = rule
                if self.persistent:
                    SqliteRecurringRuleRepository(self.portfolio_id).save(rule)
        return tuple(executed)

    def update_recurring_rule(
        self,
        rule_id: UUID,
        *,
        amount: Decimal | None = None,
        frequency: RecurrenceFrequency | None = None,
        end_execution_date: date | None = None,
    ) -> RecurringRule:
        rule = self._recurring_rules.get(rule_id)
        if rule is None:
            raise ValueError("Agendamento não encontrado.")
        updated = RecurringRule(
            id=rule.id,
            event_type=rule.event_type,
            amount=amount if amount is not None else rule.amount,
            asset_id=rule.asset_id,
            frequency=frequency if frequency is not None else rule.frequency,
            next_execution_date=rule.next_execution_date,
            end_execution_date=end_execution_date,
            active=rule.active
            and (end_execution_date is None or rule.next_execution_date <= end_execution_date),
        )
        self._recurring_rules[rule_id] = updated
        if self.persistent:
            SqliteRecurringRuleRepository(self.portfolio_id).save(updated)
        return updated

    def delete_recurring_rule(self, rule_id: UUID) -> None:
        if rule_id not in self._recurring_rules:
            raise ValueError("Agendamento não encontrado.")
        del self._recurring_rules[rule_id]
        if self.persistent:
            SqliteRecurringRuleRepository(self.portfolio_id).delete(rule_id)

    def recurring_rules(self) -> tuple[RecurringRule, ...]:
        return tuple(
            sorted(self._recurring_rules.values(), key=lambda rule: rule.next_execution_date)
        )

    def update_market_price(
        self,
        *,
        ticker: str,
        current_price: Decimal,
        effective_date: date = DEFAULT_EFFECTIVE_DATE,
        provider: str = "manual",
        price_timestamp: datetime | None = None,
        retrieved_at: datetime | None = None,
    ) -> PortfolioProjection:
        """Set an asset's manually informed market price without creating an event."""
        normalized_ticker = ticker.strip().upper()
        asset = self._assets.get(normalized_ticker)
        if asset is None:
            raise ValueError("Ativo não encontrado na carteira local.")

        price = Money(current_price)
        asset.update_current_price(price)
        price = MarketPrice(
            asset=asset,
            price=price,
            effective_date=effective_date,
            provider=provider,
            price_timestamp=price_timestamp,
            registered_at=retrieved_at or datetime.now(UTC),
        )
        self._market_prices.append(price)
        self._remember_market_price(price)
        if self.persistent:
            SqliteMarketPriceRepository().save(self._market_prices[-1])
        return self.projection()

    def import_market_price_history(
        self, *, ticker: str, prices: tuple[MarketPriceObservation, ...]
    ) -> int:
        """Persist a source historical series once; repeated backfills are idempotent."""
        asset = self._assets.get(ticker.strip().upper())
        if asset is None:
            raise ValueError("Ativo não encontrado na carteira local.")
        existing = {(price.asset.id, price.effective_date) for price in self._market_prices}
        imported_prices: list[MarketPrice] = []
        imported = 0
        for observation in prices:
            key = (asset.id, observation.effective_date)
            if key in existing:
                continue
            market_price = MarketPrice(
                asset=asset,
                price=Money(observation.price),
                effective_date=observation.effective_date,
                provider=observation.source,
            )
            self._market_prices.append(market_price)
            imported_prices.append(market_price)
            existing.add(key)
            imported += 1
        if imported_prices:
            self._rebuild_market_price_index()
        if self.persistent and imported_prices:
            SqliteMarketPriceRepository().save_many(tuple(imported_prices))
        latest_quote = max(
            (item for item in self._market_prices if item.asset.id == asset.id),
            key=lambda item: (item.effective_date, item.registered_at),
            default=None,
        )
        if latest_quote is not None:
            asset.update_current_price(latest_quote.price)
        return imported

    def refresh_market_prices(self, provider: MarketDataProvider) -> tuple[int, tuple[str, ...]]:
        updated = 0
        unavailable: list[str] = []
        for ticker in sorted(self._assets):
            try:
                observation = provider.latest_price(ticker)
                self.update_market_price(
                    ticker=ticker,
                    current_price=observation.price,
                    effective_date=observation.effective_date,
                )
                updated += 1
            except (MarketDataUnavailable, ValueError):
                unavailable.append(ticker)
        return updated, tuple(unavailable)

    def refresh_open_market_prices(
        self,
        provider_for: Callable[[Asset], MarketDataProvider],
        *,
        today: date,
        force: bool = False,
    ) -> tuple[int, tuple[str, ...], tuple[str, ...]]:
        """Refresh open positions, optionally querying providers despite today's quote."""
        report = self.refresh_open_market_prices_report(provider_for, today=today, force=force)
        return report["updated"], tuple(report["unavailable"]), tuple(report["skipped"])

    def refresh_open_market_prices_report(
        self,
        provider_for: Callable[[Asset], MarketDataProvider],
        *,
        today: date,
        force: bool = False,
    ) -> dict[str, object]:
        """Refresh provider groups independently, preserving prior quotes on failure."""
        grouped: dict[int, tuple[MarketDataProvider, list[Asset]]] = {}
        skipped: list[str] = []
        for position in self.projection().positions:
            if position.is_empty:
                continue
            asset = position.asset
            ticker = str(asset.ticker)
            if not force and any(
                price.asset.id == asset.id and price.effective_date >= today
                for price in self._market_prices
            ):
                skipped.append(ticker)
                continue
            provider = provider_for(asset)
            if getattr(provider, "supports_quotes", True) is False:
                skipped.append(ticker)
                continue
            key = id(provider)
            if key not in grouped:
                grouped[key] = (provider, [])
            grouped[key][1].append(asset)
        updated = 0
        unavailable: list[str] = []
        providers: list[dict[str, object]] = []
        for provider, assets in grouped.values():
            started = datetime.now(UTC)
            symbols = tuple(sorted({str(asset.ticker) for asset in assets}))
            batch = getattr(provider, "latest_prices", None)
            observations: dict[str, MarketPriceObservation] = {}
            errors: list[dict[str, str]] = []
            warnings: list[dict[str, str]] = []
            if callable(batch):
                try:
                    batch_result = batch(symbols)
                    if isinstance(batch_result, dict):
                        observations = batch_result
                    else:
                        warnings.append(
                            {
                                "stage": "batch_response",
                                "error_type": "InvalidBatchResponse",
                                "message": "O provedor retornou um lote em formato inválido.",
                            }
                        )
                except Exception as error:
                    warnings.append(
                        {
                            "stage": "batch",
                            "error_type": type(error).__name__,
                            "message": str(error)[:500],
                        }
                    )

            # A failed batch or a provider without batch support must not prevent
            # independent symbols from being queried and persisted.
            for ticker in symbols:
                if ticker in observations:
                    continue
                try:
                    observations[ticker] = provider.latest_price(ticker)
                except Exception as error:
                    errors.append(
                        {
                            "asset": ticker,
                            "stage": "single_quote",
                            "error_type": type(error).__name__,
                            "message": str(error)[:500],
                        }
                    )

            resolved = 0
            failed: list[str] = []
            asset_results: list[dict[str, object]] = []
            for asset in assets:
                ticker = str(asset.ticker)
                observation = observations.get(ticker)
                if not isinstance(observation, MarketPriceObservation):
                    if not any(item["asset"] == ticker for item in errors):
                        errors.append(
                            {
                                "asset": ticker,
                                "stage": "response_validation",
                                "error_type": "MissingObservation",
                                "message": "O provedor não retornou uma cotação para este ativo.",
                            }
                        )
                    unavailable.append(ticker)
                    failed.append(ticker)
                    asset_results.append({"asset": ticker, "status": "FAILED"})
                    continue
                if observation.currency_code.upper() != asset.currency.code.upper():
                    errors.append(
                        {
                            "asset": ticker,
                            "stage": "response_validation",
                            "error_type": "CurrencyMismatch",
                            "message": (
                                f"Moeda recebida {observation.currency_code}; "
                                f"esperada {asset.currency.code}."
                            ),
                        }
                    )
                    unavailable.append(ticker)
                    failed.append(ticker)
                    asset_results.append({"asset": ticker, "status": "FAILED"})
                    continue
                if any(
                    price.asset.id == asset.id
                    and price.effective_date == observation.effective_date
                    and price.price.amount == observation.price
                    and price.provider == observation.source
                    for price in self._market_prices
                ):
                    skipped.append(ticker)
                    asset_results.append(
                        {
                            "asset": ticker,
                            "status": "UNCHANGED",
                            "source": observation.source,
                            "price": str(observation.price),
                            "observation_date": observation.effective_date.isoformat(),
                            "provider_attempts": [
                                {"provider": name, "result": result, "reason": reason}
                                for name, result, reason in observation.provider_attempts
                            ],
                        }
                    )
                    continue
                try:
                    self.update_market_price(
                        ticker=ticker,
                        current_price=observation.price,
                        effective_date=observation.effective_date,
                        provider=observation.source,
                        price_timestamp=observation.price_timestamp,
                        retrieved_at=observation.retrieved_at,
                    )
                except Exception as error:
                    errors.append(
                        {
                            "asset": ticker,
                            "stage": "persist_quote",
                            "error_type": type(error).__name__,
                            "message": str(error)[:500],
                        }
                    )
                    unavailable.append(ticker)
                    failed.append(ticker)
                    continue
                updated += 1
                resolved += 1
                asset_results.append(
                    {
                        "asset": ticker,
                        "status": "SUCCESS",
                        "source": observation.source,
                        "price": str(observation.price),
                        "observation_date": observation.effective_date.isoformat(),
                        "provider_attempts": [
                            {"provider": name, "result": result, "reason": reason}
                            for name, result, reason in observation.provider_attempts
                        ],
                    }
                )

            provider_status = "SUCCESS"
            if failed:
                provider_status = "PARTIAL" if resolved or skipped else "FAILED"
            elif warnings:
                provider_status = "DEGRADED"
            providers.append(
                {
                    "provider": getattr(provider, "source", type(provider).__name__),
                    "status": provider_status,
                    "requested_assets": list(symbols),
                    "resolved_assets": resolved,
                    "failed_assets": failed,
                    "errors": errors,
                    "warnings": warnings,
                    "asset_results": asset_results,
                    "duration_seconds": (datetime.now(UTC) - started).total_seconds(),
                }
            )
        return {
            "updated": updated,
            "unavailable": sorted(unavailable),
            "skipped": sorted(skipped),
            "providers": providers,
        }

    def open_foreign_currencies(self) -> tuple[str, ...]:
        """Currencies that require base-currency FX for open positions."""
        return tuple(
            sorted(
                {
                    position.asset.currency.code.upper()
                    for position in self.projection().positions
                    if not position.is_empty
                    and position.asset.currency.code.upper() != self._base_currency
                }
            )
        )

    def has_benchmark_data_for(self, name: str, effective_date: date) -> bool:
        normalized = name.upper()
        if normalized == "CDI":
            return any(
                rate.name.upper() == normalized and rate.effective_date >= effective_date
                for rate in self._benchmark_rates
            )
        return any(
            observation.effective_date >= effective_date
            for observation in self._benchmark_observations.get(normalized, ())
        )

    def has_fx_rate_for(self, base_currency: str, effective_date: date) -> bool:
        if not self.persistent:
            return False
        rate = SqliteFxRateRepository().latest_on_or_before(
            base_currency, self._base_currency, effective_date
        )
        return (
            rate is not None
            and (effective_date - rate.effective_date).days <= MAX_FX_STALE_AGE_DAYS
        )

    def history(self) -> tuple[FinancialEvent, ...]:
        """Return the events in the order they were entered into the dashboard."""
        return tuple(self._events)

    def delete_event(self, event_id: str) -> None:
        """Remove one mistaken operation and rebuild all derived projections."""
        remaining = [event for event in self._events if str(event.id) != event_id]
        if len(remaining) == len(self._events):
            raise ValueError("Lançamento não encontrado.")
        if self.persistent and not SqliteFinancialEventRepository(self.portfolio_id).delete(
            event_id
        ):
            raise ValueError("Lançamento não encontrado.")
        self._events = remaining

    def portfolio_history(self) -> PortfolioHistory:
        """Return derived snapshots at every relevant event or market-price date."""
        return PortfolioProjector.history(self._events, self._market_prices)

    def _market_prices_for_valuation(self, *, as_of: date | None) -> list[MarketPrice]:
        """Add non-persisted contract-curve values to listed-market prices.

        A derived fixed-income value is deliberately not written as a market
        quote: it is reproducible from its contract and dated reference series.
        """
        effective_date = as_of or date.today()
        prices = list(self._market_prices)
        prices.extend(self._fixed_income_valuation_prices(effective_date))
        return prices

    def _market_prices_for_projection(
        self, *, as_of: date | None, include_fixed_income: bool = True
    ) -> list[MarketPrice]:
        """Supply only the as-of quote per asset needed by a portfolio projection."""
        self._ensure_market_price_index_current()
        effective_date = as_of or date.today()
        prices: list[MarketPrice] = []
        for quotes in self._market_prices_by_asset.values():
            index = (
                len(quotes)
                if as_of is None
                else bisect_right(quotes, effective_date, key=lambda item: item.effective_date)
            )
            if index:
                prices.append(quotes[index - 1])
        if include_fixed_income:
            prices.extend(self._fixed_income_valuation_prices(effective_date))
        return prices

    def _fixed_income_valuation_prices(self, effective_date: date) -> list[MarketPrice]:
        prices: list[MarketPrice] = []
        ipca_rates = tuple(
            (observation.effective_date, observation.value)
            for observation in self._benchmark_observations.get("IPCA", ())
        )
        tr_rates = tuple(
            (observation.effective_date, observation.value)
            for observation in self._benchmark_observations.get("TR", ())
        )
        selic_targets = tuple(
            (observation.effective_date, observation.value)
            for observation in self._benchmark_observations.get("SELIC_TARGET", ())
        )
        for asset_id, details in self._fixed_income_details.items():
            asset = next((item for item in self._assets.values() if item.id == asset_id), None)
            if asset is None:
                continue
            valuation = FixedIncomeValuationEngine.value(
                details,
                as_of=effective_date,
                cdi_rates=tuple(self._benchmark_rates),
                ipca_rates=ipca_rates,
                tr_rates=tr_rates,
                selic_targets=selic_targets,
            )
            # A contract that starts after the requested historical projection
            # date has no market value on that date.  Do not materialize a
            # zero-valued MarketPrice: the value object correctly rejects
            # non-positive quotes, and doing so must not block an unrelated
            # trade in the same portfolio.
            if valuation.gross_value is not None and valuation.gross_value > 0:
                prices.append(
                    MarketPrice(
                        asset=asset,
                        price=Money(valuation.gross_value),
                        effective_date=effective_date,
                    )
                )
        return prices

    def _rebuild_market_price_index(self) -> None:
        grouped: dict[UUID, list[MarketPrice]] = {}
        for price in self._market_prices:
            grouped.setdefault(price.asset.id, []).append(price)
        self._market_prices_by_asset = {
            asset_id: tuple(
                sorted(quotes, key=lambda item: (item.effective_date, item.registered_at))
            )
            for asset_id, quotes in grouped.items()
        }
        self._market_prices_indexed_source = self._market_prices
        self._market_prices_indexed_length = len(self._market_prices)

    def _ensure_market_price_index_current(self) -> None:
        """Rebuild the derived index if callers replaced or resized its source list."""
        if (
            self._market_prices_indexed_source is not self._market_prices
            or self._market_prices_indexed_length != len(self._market_prices)
        ):
            self._rebuild_market_price_index()

    def _remember_market_price(self, price: MarketPrice) -> None:
        if (
            self._market_prices_indexed_source is not self._market_prices
            or self._market_prices_indexed_length != len(self._market_prices) - 1
        ):
            # The source list may have been replaced or edited before this append.
            # It already contains `price`, so rebuilding is sufficient.
            self._rebuild_market_price_index()
            return
        quotes = (*self._market_prices_by_asset.get(price.asset.id, ()), price)
        self._market_prices_by_asset[price.asset.id] = tuple(
            sorted(quotes, key=lambda item: (item.effective_date, item.registered_at))
        )
        self._market_prices_indexed_length = len(self._market_prices)

    def performance(
        self,
        *,
        start_date: date,
        end_date: date,
        asset_class: AssetClass | None = None,
    ) -> PerformanceProjection:
        """Return TWR and XIRR for the whole portfolio or one asset class."""
        valuation_dates = {start_date, end_date}
        valuation_dates.update(
            event.effective_date
            for event in self._events
            if start_date <= event.effective_date <= end_date
        )
        valuation_dates.update(
            rate.effective_date
            for rate in self._benchmark_rates
            if start_date <= rate.effective_date <= end_date
        )
        for name in ("IPCA", "TR", "SELIC_TARGET"):
            valuation_dates.update(
                item.effective_date
                for item in self._benchmark_observations.get(name, ())
                if start_date <= item.effective_date <= end_date
            )
        contract_curve_assets = {
            asset_id
            for asset_id, details in self._fixed_income_details.items()
            if (
                asset := next((item for item in self._assets.values() if item.id == asset_id), None)
            )
            is not None
            and asset.valuation_method is ValuationMethod.CONTRACT_CURVE
        }
        curve_prices = [
            price for price in self._market_prices if price.asset.id in contract_curve_assets
        ]
        curve_prices.extend(
            price
            for effective_date in sorted(valuation_dates)
            for price in self._fixed_income_valuation_prices(effective_date)
            if price.asset.id in contract_curve_assets
        )
        events: tuple[FinancialEvent, ...] = tuple(self._events)
        prices: tuple[MarketPrice, ...] = (*self._market_prices, *curve_prices)
        if asset_class is not None:
            unallocated_flows = tuple(
                event
                for event in events
                if event.event_type in {FinancialEventType.DEPOSIT, FinancialEventType.WITHDRAWAL}
                and event.capital_flow_type is not CapitalFlowType.INTERNAL_TRANSFER
                and start_date <= event.effective_date <= end_date
            )
            if unallocated_flows:
                contributions = sum(
                    (
                        event.total_amount
                        for event in unallocated_flows
                        if event.event_type is FinancialEventType.DEPOSIT
                    ),
                    Money.zero(),
                )
                withdrawals = sum(
                    (
                        event.total_amount
                        for event in unallocated_flows
                        if event.event_type is FinancialEventType.WITHDRAWAL
                    ),
                    Money.zero(),
                )
                return PerformanceProjection(
                    start_date=start_date,
                    end_date=end_date,
                    beginning_equity=None,
                    ending_equity=None,
                    total_contributions=contributions,
                    total_withdrawals=withdrawals,
                    twr=None,
                    xirr=None,
                    unavailable_reason=(
                        "Há aportes ou retiradas sem classe associada; o TWR por classe "
                        "não pode atribuí-los com segurança."
                    ),
                    performance_status="INSUFFICIENT_DATA",
                )
            asset_ids = {
                asset.id for asset in self._assets.values() if asset.asset_class is asset_class
            }
            events = tuple(event for event in events if event.asset and event.asset.id in asset_ids)
            prices = tuple(price for price in prices if price.asset.id in asset_ids)
        return PerformanceProjector.project(
            events,
            prices,
            start_date=start_date,
            end_date=end_date,
            fx_rates=tuple(
                rate
                for currency in {asset.currency.code.upper() for asset in self._assets.values()}
                - {self._base_currency}
                for rate in (self._fx_rates(currency, self._base_currency))
                if rate.effective_date <= end_date
            ),
            base_currency=self._base_currency,
        )

    def benchmark_comparison(
        self, *, name: str, start_date: date, end_date: date
    ) -> BenchmarkComparisonProjection:
        performance = self.performance(start_date=start_date, end_date=end_date)
        return BenchmarkComparisonProjector.project(
            portfolio_twr=performance.twr,
            rates=tuple(self._benchmark_rates),
            name=name,
            start_date=start_date,
            end_date=end_date,
        )

    def register_benchmark_rate(
        self, *, name: str, return_percentage: Decimal, effective_date: date
    ) -> None:
        """Register a manual dated benchmark return, such as CDI daily return."""
        self._benchmark_rates.append(
            BenchmarkRate(
                name=name,
                return_percentage=return_percentage,
                effective_date=effective_date,
            )
        )
        if self.persistent:
            SqliteBenchmarkRateRepository().save(self._benchmark_rates[-1])

    def refresh_benchmark(
        self, provider: BenchmarkDataProvider, *, name: str, start_date: date, end_date: date
    ) -> int:
        observations = provider.observations(name, start_date=start_date, end_date=end_date)
        if name.upper() != "CDI":
            normalized_name = name.upper()
            if self.persistent:
                repository = SqliteBenchmarkObservationRepository()
                for observation in observations:
                    repository.save(observation)
            current = {
                item.effective_date: item
                for item in self._benchmark_observations.get(normalized_name, ())
            }
            current.update((item.effective_date, item) for item in observations)
            self._benchmark_observations[normalized_name] = [
                current[key] for key in sorted(current)
            ]
            return len(observations)
        for observation in observations:
            self._benchmark_rates = [
                rate
                for rate in self._benchmark_rates
                if (rate.name, rate.effective_date)
                != (observation.benchmark, observation.effective_date)
            ]
            self.register_benchmark_rate(
                name=observation.benchmark,
                return_percentage=observation.value,
                effective_date=observation.effective_date,
            )
        return len(observations)

    def benchmark_observations(self, name: str) -> tuple[BenchmarkObservation, ...]:
        """Return persisted non-CDI observations in chronological order."""
        return tuple(self._benchmark_observations.get(name.upper(), ()))

    def risk(self, *, start_date: date, end_date: date) -> RiskProjection:
        """Return risk metrics derived from the portfolio's dated return series."""
        return RiskProjector.project(
            self._events,
            self._market_prices,
            self._benchmark_rates,
            start_date=start_date,
            end_date=end_date,
        )

    def risk_contribution(self, *, as_of: date | None = None) -> RiskContributionProjection:
        cutoff = as_of or date.max
        prices: dict[str, dict[date, Decimal]] = {}
        for point in self._market_prices:
            if point.effective_date <= cutoff:
                prices.setdefault(str(point.asset.ticker), {})[point.effective_date] = (
                    point.price.amount
                )
        return RiskContributionProjector.project(self.allocation(as_of=as_of), prices)

    def allocation(self, *, as_of: date | None = None) -> AllocationProjection:
        """Return point-in-time allocation and per-asset result contribution."""
        return AllocationProjector.project(self.projection(as_of=as_of))

    def class_allocation(self, *, as_of: date | None = None) -> ClassAllocationProjection:
        return ClassAllocationProjector.project(self.allocation(as_of=as_of))

    def diversification(self, *, as_of: date | None = None) -> DiversificationProjection:
        return DiversificationProjector.project(self.allocation(as_of=as_of))

    def intelligence(self, *, as_of: date | None = None) -> PortfolioIntelligence:
        as_of = min(as_of or date.today(), date.today())
        comparison_date = as_of - timedelta(days=90)
        allocation = self._finding_allocation(as_of)
        comparison_allocation = self._finding_allocation(comparison_date)
        analysis = (
            AllocationAnalysisProjector.project(allocation, self._allocation_policy)
            if self._allocation_policy
            else None
        )
        comparison_analysis = (
            AllocationAnalysisProjector.project(comparison_allocation, self._allocation_policy)
            if self._allocation_policy
            else None
        )
        prices: dict[str, dict[date, Decimal]] = {}
        for point in self._market_prices:
            if point.effective_date <= as_of:
                prices.setdefault(str(point.asset.ticker), {})[point.effective_date] = (
                    point.price.amount
                )
        return PortfolioDiagnosticEngine.analyze(
            allocation=allocation,
            diversification=DiversificationProjector.project(allocation),
            risk=RiskContributionProjector.project(allocation, prices),
            allocation_analysis=analysis,
            comparison_allocation=comparison_allocation,
            comparison_analysis=comparison_analysis,
            as_of=as_of,
        )

    def _finding_allocation(self, as_of: date) -> AllocationProjection:
        """Use existing base-currency valuation for comparable invested-asset weights."""
        portfolio = self.projection(as_of=as_of)
        valuation = self.base_currency_valuation(as_of=as_of)
        values = {item.ticker: item.market_value_base for item in valuation.positions}
        dated_assets = {
            point.asset.id
            for point in self._market_prices_for_projection(as_of=as_of)
            if point.effective_date <= as_of
        }
        positions = []
        for position in portfolio.positions:
            value = values.get(str(position.asset.ticker))
            price = (
                Money(value / position.quantity.value)
                if value is not None and not position.is_empty and position.asset.id in dated_assets
                else None
            )
            positions.append(replace(position, current_price=price))
        return AllocationProjector.project(replace(portfolio, positions=tuple(positions)))

    def set_allocation_policy(self, policy: AllocationPolicy) -> None:
        self._allocation_policy = policy
        if self.persistent:
            SqliteAllocationPolicyRepository(self.portfolio_id).save(policy)

    def set_asset_allocation_policy(self, policy: AssetAllocationPolicy) -> None:
        active_assets = tuple(
            position.asset for position in self.projection().positions if not position.is_empty
        )
        target_tickers = {ticker for targets in policy.targets.values() for ticker in targets}
        policy.validate_assets(
            active_assets
            + tuple(asset for ticker, asset in self._assets.items() if ticker in target_tickers)
        )
        current_targets = (
            self._asset_allocation_policy.targets if self._asset_allocation_policy else {}
        )
        merged_targets = {**current_targets, **policy.targets}
        self._asset_allocation_policy = AssetAllocationPolicy(targets=merged_targets)
        if self.persistent:
            SqliteAssetAllocationPolicyRepository(self.portfolio_id).save(
                self._asset_allocation_policy
            )

    @property
    def allocation_policy(self) -> AllocationPolicy | None:
        """Current class policy, exposed for read-model composition only."""
        return self._allocation_policy

    @property
    def asset_allocation_policy(self) -> AssetAllocationPolicy | None:
        """Current intra-class asset policy, exposed for read-model composition only."""
        return self._asset_allocation_policy

    def allocation_analysis(self, *, as_of: date | None = None) -> PortfolioAllocationAnalysis:
        if self._allocation_policy is None:
            raise ValueError("Defina uma política de alocação-alvo primeiro.")
        return AllocationAnalysisProjector.project(
            self._finding_allocation(as_of or date.today()), self._allocation_policy
        )

    def rebalancing(self, *, as_of: date | None = None) -> RebalancingProjection:
        return RebalancingProjection.from_analysis(self.allocation_analysis(as_of=as_of))

    def hypothetical_contribution(
        self,
        *,
        amount: Decimal,
        as_of: date | None = None,
        allocation_mode: str = "LEGACY_BEFORE_DEFICIT",
    ) -> HypotheticalPortfolioProjection:
        """Build a pure contribution scenario from the official base-currency valuation."""
        if self._allocation_policy is None:
            raise ValueError("Defina uma política de alocação-alvo primeiro.")
        effective_date = as_of or date.today()
        portfolio = self.projection(as_of=effective_date)
        valuation = self.base_currency_valuation(as_of=effective_date)
        assets = {str(position.asset.ticker): position.asset for position in portfolio.positions}
        values: dict[AssetClass, Decimal] = {}
        missing_fx = False
        for item in valuation.positions:
            asset = assets[item.ticker]
            if item.market_value_base is None:
                missing_fx = missing_fx or item.native_currency != valuation.base_currency
                continue
            values[asset.asset_class] = (
                values.get(asset.asset_class, Decimal("0")) + item.market_value_base
            )
        issues: list[str] = []
        if missing_fx:
            issues.append("MISSING_FX")
        if not valuation.complete:
            issues.append("INCOMPLETE_VALUATION")
        result = HypotheticalPortfolioProjector.project_contribution(
            as_of=effective_date,
            base_currency=valuation.base_currency,
            class_values=values,
            policy=self._allocation_policy,
            contribution=amount,
            valuation_complete=valuation.complete,
            valuation_issues=tuple(issues),
            allocation_mode=allocation_mode,
        )
        if allocation_mode != "STRATEGY_GUIDED" or result.status != "COMPLETE":
            return result
        details = self._strategy_guided_asset_details(
            result=result,
            portfolio=portfolio,
            base_values={item.ticker: item.market_value_base for item in valuation.positions},
        )
        return replace(result, scenario=replace(result.scenario, class_details=details))

    def _strategy_guided_asset_details(
        self,
        *,
        result: HypotheticalPortfolioProjection,
        portfolio: PortfolioProjection,
        base_values: dict[str, Decimal | None],
    ) -> tuple[SimulationClassContribution, ...]:
        open_by_class: dict[AssetClass, set[str]] = {}
        for position in portfolio.positions:
            if not position.is_empty:
                open_by_class.setdefault(position.asset.asset_class, set()).add(
                    str(position.asset.ticker)
                )
        details = []
        policy_targets = (
            self._asset_allocation_policy.targets if self._asset_allocation_policy else {}
        )
        for asset_class, class_amount in result.scenario.class_allocations:
            targets = policy_targets.get(asset_class)
            if targets is None:
                details.append(
                    SimulationClassContribution(
                        asset_class=asset_class,
                        amount=class_amount,
                        asset_distribution_status="NEEDS_USER_DISTRIBUTION",
                        asset_distributed_amount=Decimal("0"),
                        undistributed_within_class=class_amount,
                        asset_composition_distance_before=None,
                        asset_composition_distance_after=None,
                        asset_composition_distance_change=None,
                        asset_allocations=(),
                    )
                )
                continue
            eligible = open_by_class.get(asset_class, set()) | set(targets)
            assets = {ticker: self._assets.get(ticker) for ticker in eligible}
            valid = (
                set(targets) == eligible
                and all(
                    asset is not None and asset.asset_class is asset_class
                    for asset in assets.values()
                )
                and abs(sum(targets.values(), Decimal("0")) - Decimal("1")) <= Decimal("0.000001")
            )
            current_values = {ticker: base_values.get(ticker, Decimal("0")) for ticker in eligible}
            if not valid or any(value is None for value in current_values.values()):
                details.append(
                    SimulationClassContribution(
                        asset_class=asset_class,
                        amount=class_amount,
                        asset_distribution_status="INCOMPLETE_OR_INVALID_POLICY",
                        asset_distributed_amount=Decimal("0"),
                        undistributed_within_class=class_amount,
                        asset_composition_distance_before=None,
                        asset_composition_distance_after=None,
                        asset_composition_distance_change=None,
                        asset_allocations=(),
                    )
                )
                continue
            resolved_assets = {
                ticker: asset for ticker, asset in assets.items() if asset is not None
            }
            values = {
                ticker: value for ticker, value in current_values.items() if value is not None
            }
            allocation = ContributionTargetAllocator.allocate(
                values, targets, class_amount, key=lambda ticker: ticker
            )
            after_values = {
                ticker: value + allocation.allocations.get(ticker, Decimal("0"))
                for ticker, value in values.items()
            }
            before_total = sum(values.values(), Decimal("0"))
            after_total = sum(after_values.values(), Decimal("0"))
            before_distance = ContributionTargetAllocator.distance(values, targets)
            after_distance = ContributionTargetAllocator.distance(after_values, targets)
            asset_rows = tuple(
                SimulationAssetContribution(
                    asset_id=str(resolved_assets[ticker].id),
                    asset_label=resolved_assets[ticker].name,
                    amount=allocation.allocations.get(ticker, Decimal("0")),
                    value_before=values[ticker],
                    value_after=after_values[ticker],
                    weight_before_in_class=(
                        values[ticker] / before_total if before_total else Decimal("0")
                    ),
                    weight_after_in_class=(
                        after_values[ticker] / after_total if after_total else Decimal("0")
                    ),
                    target_weight_in_class=targets[ticker],
                    gap_before_pp=(values[ticker] / before_total if before_total else Decimal("0"))
                    - targets[ticker],
                    gap_after_pp=(
                        after_values[ticker] / after_total if after_total else Decimal("0")
                    )
                    - targets[ticker],
                    reason_code=(
                        "BELOW_TARGET_AFTER_CONTRIBUTION"
                        if allocation.allocations.get(ticker, Decimal("0")) > 0
                        else "ZERO_TARGET_NO_CONTRIBUTION"
                        if targets[ticker] == 0
                        else "ABOVE_TARGET_NO_CONTRIBUTION"
                    ),
                )
                for ticker in sorted(eligible)
                if (
                    values[ticker] != Decimal("0")
                    or targets[ticker] != Decimal("0")
                    or allocation.allocations.get(ticker, Decimal("0")) != Decimal("0")
                )
            )
            distributed = sum(allocation.allocations.values(), Decimal("0"))
            details.append(
                SimulationClassContribution(
                    asset_class=asset_class,
                    amount=class_amount,
                    asset_distribution_status="DISTRIBUTED_BY_STRATEGY",
                    asset_distributed_amount=distributed,
                    undistributed_within_class=class_amount - distributed,
                    asset_composition_distance_before=before_distance,
                    asset_composition_distance_after=after_distance,
                    asset_composition_distance_change=(
                        after_distance - before_distance
                        if before_distance is not None and after_distance is not None
                        else None
                    ),
                    asset_allocations=asset_rows,
                )
            )
        return tuple(details)

    def asset_rebalancing(
        self, *, asset_class: AssetClass, amount: Decimal, strategy: AssetAllocationStrategy
    ) -> tuple[tuple[str, Money], ...]:
        return AssetRebalancingProjector.distribute(
            self.allocation(), asset_class, Money(amount), strategy, self._asset_allocation_policy
        )

    def update_asset_class(self, *, ticker: str, asset_class: AssetClass) -> None:
        asset = self._assets.get(ticker.strip().upper())
        if asset is None:
            raise ValueError("Ativo não encontrado na carteira local.")
        self._reclassify_market_traded_asset(asset, asset_class)

    def _reclassify_market_traded_asset(self, asset: Asset, asset_class: AssetClass) -> None:
        if asset.asset_class is asset_class:
            return
        brazilian_listed_classes = {
            AssetClass.BRAZILIAN_STOCK,
            AssetClass.BRAZILIAN_ETF,
            AssetClass.FII,
        }
        international_listed_classes = {
            AssetClass.INTERNATIONAL,
            AssetClass.INTERNATIONAL_ETF,
            AssetClass.US_REIT,
        }
        allowed = {asset.asset_class, asset_class} <= brazilian_listed_classes or {
            asset.asset_class,
            asset_class,
        } <= international_listed_classes
        if not allowed:
            raise ValueError(
                "A reclassificação só é permitida entre classes negociadas do mesmo mercado."
            )
        asset.update_asset_class(asset_class)
        if self.persistent:
            SqliteAssetRepository(self.portfolio_id).save(asset)

    def clear(self) -> None:
        """Clear the local session without persisting any data."""
        self._assets.clear()
        self._events.clear()
        self._market_prices.clear()
        self._market_prices_by_asset.clear()
        self._fx_rate_cache.clear()
        self._benchmark_rates.clear()
        self._benchmark_observations.clear()
        self._fixed_income_details.clear()
        self._pension_plan_details.clear()
        self._real_estate_details.clear()
        self._recurring_rules.clear()
        self._allocation_policy = None
        self._asset_allocation_policy = None
        self._base_currency = "BRL"
        if self.persistent:
            SqlitePortfolioDataRepository(self.portfolio_id).clear()

    @staticmethod
    def _create_asset(
        ticker: str,
        *,
        name: str,
        asset_class: AssetClass,
        country: str = "BR",
        currency_code: str = "BRL",
        sector: str | None = None,
        asset_type: AssetType | None = None,
        valuation_method: ValuationMethod = ValuationMethod.MARKET_PRICE,
    ) -> Asset:
        return Asset(
            ticker=Ticker(ticker),
            name=name,
            asset_type=asset_type
            or {
                AssetClass.BRAZILIAN_ETF: AssetType.ETF,
                AssetClass.INTERNATIONAL_ETF: AssetType.ETF,
                AssetClass.FII: AssetType.FII,
                AssetClass.US_REIT: AssetType.REIT,
                AssetClass.CRYPTO: AssetType.CRYPTO,
            }.get(asset_class, AssetType.STOCK),
            asset_class=asset_class,
            valuation_method=valuation_method,
            country=country,
            sector=sector,
            currency=Currency(
                code=currency_code,
                name=currency_code,
                symbol=currency_code,
                decimal_places=2,
            ),
            institution=Institution(name="Cadastro local"),
        )

    def _ensure_private_ticker_available(self, ticker: str) -> None:
        if not self.persistent:
            return
        existing = SqliteAssetRepository(self.portfolio_id).get_by_ticker(ticker)
        if existing is not None:
            raise ValueError("Já existe um ativo com esse identificador nesta carteira.")
