"""In-memory portfolio session used by the local MVP interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

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
from income_analytics.domain.market_price import MarketPrice
from income_analytics.domain.projectors.allocation_analysis_projector import (
    AllocationAnalysisProjector,
)
from income_analytics.domain.projectors.allocation_projector import AllocationProjector
from income_analytics.domain.projectors.asset_rebalancing_projector import (
    AssetAllocationStrategy,
    AssetRebalancingProjector,
)
from income_analytics.domain.projectors.class_allocation_projector import ClassAllocationProjector
from income_analytics.domain.projectors.diversification_projector import DiversificationProjector
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
from income_analytics.domain.read_models.class_allocation_projection import (
    ClassAllocationProjection,
)
from income_analytics.domain.read_models.diversification_projection import DiversificationProjection
from income_analytics.domain.read_models.performance_projection import PerformanceProjection
from income_analytics.domain.read_models.portfolio_history import PortfolioHistory
from income_analytics.domain.read_models.portfolio_intelligence import PortfolioIntelligence
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection
from income_analytics.domain.read_models.rebalancing_projection import RebalancingProjection
from income_analytics.domain.read_models.risk_contribution_projection import (
    RiskContributionProjection,
)
from income_analytics.domain.read_models.risk_projection import RiskProjection
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from income_analytics.domain.value_objects.ticker import Ticker
from income_analytics.infrastructure.sqlite_repositories import (
    SqliteAllocationPolicyRepository,
    SqliteAssetAllocationPolicyRepository,
    SqliteAssetRepository,
    SqliteBenchmarkRateRepository,
    SqliteFinancialEventRepository,
    SqliteMarketPriceRepository,
)

DEFAULT_EFFECTIVE_DATE = date(2026, 1, 1)


@dataclass(slots=True)
class PortfolioSession:
    """Keeps a local, non-persistent event stream for the dashboard."""

    account_id: UUID = field(default_factory=uuid4)
    persistent: bool = False
    _assets: dict[str, Asset] = field(default_factory=dict, init=False)
    _events: list[FinancialEvent] = field(default_factory=list, init=False)
    _market_prices: list[MarketPrice] = field(default_factory=list, init=False)
    _benchmark_rates: list[BenchmarkRate] = field(default_factory=list, init=False)
    _allocation_policy: AllocationPolicy | None = field(default=None, init=False)
    _asset_allocation_policy: AssetAllocationPolicy | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.persistent:
            self._assets = {str(asset.ticker): asset for asset in SqliteAssetRepository().list()}
            self._events = list(SqliteFinancialEventRepository().list())
            self._market_prices = list(SqliteMarketPriceRepository().list())
            self._benchmark_rates = list(SqliteBenchmarkRateRepository().list())
            self._allocation_policy = SqliteAllocationPolicyRepository().get()
            self._asset_allocation_policy = SqliteAssetAllocationPolicyRepository().get()

    def register_trade(
        self,
        *,
        event_type: FinancialEventType,
        ticker: str,
        asset_class: AssetClass = AssetClass.OTHER,
        country: str = "BR",
        currency_code: str = "BRL",
        sector: str | None = None,
        quantity: Decimal,
        unit_price: Decimal,
        effective_date: date = DEFAULT_EFFECTIVE_DATE,
    ) -> PortfolioProjection:
        """Register a trade only when it can be applied to the current portfolio."""
        normalized_ticker = ticker.strip().upper()
        asset = self._assets.get(normalized_ticker)
        if asset is None:
            asset = self._create_asset(
                normalized_ticker,
                name=normalized_ticker,
                asset_class=asset_class,
                country=country,
                currency_code=currency_code,
                sector=sector,
            )
            self._assets[normalized_ticker] = asset
            if self.persistent:
                SqliteAssetRepository().save(asset)

        event = FinancialEvent(
            account_id=self.account_id,
            asset=asset,
            event_type=event_type,
            occurred_at=datetime.now(UTC),
            effective_date=effective_date,
            quantity=Quantity(quantity),
            unit_price=Money(unit_price),
        )

        candidate_events = [*self._events, event]
        projection = PortfolioProjector.project(
            candidate_events,
            market_prices=self._market_prices,
        )
        self._events.append(event)
        if self.persistent:
            SqliteFinancialEventRepository().save(event)
        return projection

    def projection(self, *, as_of: date | None = None) -> PortfolioProjection:
        """Return the portfolio state represented by the registered event stream."""
        return PortfolioProjector.project(
            self._events,
            market_prices=self._market_prices,
            as_of=as_of,
        )

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
            market_prices=self._market_prices,
        )
        self._events.append(event)
        if self.persistent:
            SqliteFinancialEventRepository().save(event)
        return projection

    def register_external_flow(
        self,
        *,
        event_type: FinancialEventType,
        amount: Decimal,
        effective_date: date = DEFAULT_EFFECTIVE_DATE,
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
        )
        projection = PortfolioProjector.project(
            [*self._events, event], market_prices=self._market_prices
        )
        self._events.append(event)
        if self.persistent:
            SqliteFinancialEventRepository().save(event)
        return projection

    def update_market_price(
        self,
        *,
        ticker: str,
        current_price: Decimal,
        effective_date: date = DEFAULT_EFFECTIVE_DATE,
    ) -> PortfolioProjection:
        """Set an asset's manually informed market price without creating an event."""
        normalized_ticker = ticker.strip().upper()
        asset = self._assets.get(normalized_ticker)
        if asset is None:
            raise ValueError("Ativo não encontrado na carteira local.")

        price = Money(current_price)
        asset.update_current_price(price)
        self._market_prices.append(
            MarketPrice(
                asset=asset,
                price=price,
                effective_date=effective_date,
            )
        )
        if self.persistent:
            SqliteMarketPriceRepository().save(self._market_prices[-1])
        return self.projection()

    def history(self) -> tuple[FinancialEvent, ...]:
        """Return the events in the order they were entered into the dashboard."""
        return tuple(self._events)

    def portfolio_history(self) -> PortfolioHistory:
        """Return derived snapshots at every relevant event or market-price date."""
        return PortfolioProjector.history(self._events, self._market_prices)

    def performance(self, *, start_date: date, end_date: date) -> PerformanceProjection:
        """Return TWR and XIRR calculated from this session's dated streams."""
        return PerformanceProjector.project(
            self._events,
            self._market_prices,
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
        allocation = self.allocation(as_of=as_of)
        analysis = self.allocation_analysis(as_of=as_of) if self._allocation_policy else None
        return PortfolioDiagnosticEngine.analyze(
            allocation=allocation,
            diversification=DiversificationProjector.project(allocation),
            risk=self.risk_contribution(as_of=as_of),
            allocation_analysis=analysis,
            as_of=as_of,
        )

    def set_allocation_policy(self, policy: AllocationPolicy) -> None:
        self._allocation_policy = policy
        if self.persistent:
            SqliteAllocationPolicyRepository().save(policy)

    def set_asset_allocation_policy(self, policy: AssetAllocationPolicy) -> None:
        policy.validate_assets(tuple(self._assets.values()))
        self._asset_allocation_policy = policy
        if self.persistent:
            SqliteAssetAllocationPolicyRepository().save(policy)

    def allocation_analysis(self, *, as_of: date | None = None) -> PortfolioAllocationAnalysis:
        if self._allocation_policy is None:
            raise ValueError("Defina uma política de alocação-alvo primeiro.")
        return AllocationAnalysisProjector.project(
            self.allocation(as_of=as_of), self._allocation_policy
        )

    def rebalancing(self, *, as_of: date | None = None) -> RebalancingProjection:
        return RebalancingProjection.from_analysis(self.allocation_analysis(as_of=as_of))

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
        raise ValueError("A classe é definida apenas na criação do ativo.")

    def clear(self) -> None:
        """Clear the local session without persisting any data."""
        self._assets.clear()
        self._events.clear()
        self._market_prices.clear()
        self._benchmark_rates.clear()

    @staticmethod
    def _create_asset(
        ticker: str,
        *,
        name: str,
        asset_class: AssetClass,
        country: str = "BR",
        currency_code: str = "BRL",
        sector: str | None = None,
    ) -> Asset:
        return Asset(
            ticker=Ticker(ticker),
            name=name,
            asset_type=AssetType.STOCK,
            asset_class=asset_class,
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
