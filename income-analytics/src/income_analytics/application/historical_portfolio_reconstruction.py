"""Read-only economic as-of valuation from persisted portfolio sources."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from income_analytics.application.base_currency_valuation import BaseCurrencyValuation
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.market_price import MarketPrice
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection


@dataclass(frozen=True, slots=True)
class HistoricalPositionCoverage:
    ticker: str
    asset_class: str
    status: str
    issue: str | None


@dataclass(frozen=True, slots=True)
class PortfolioAsOfResult:
    as_of_date: date
    valued_wealth: Decimal | None
    coverage_status: str
    valued_positions: int
    unvalued_positions: int
    positions: tuple[HistoricalPositionCoverage, ...]
    issues: tuple[str, ...]


class HistoricalPortfolioReconstructionService:
    """Expose partial valuation honestly while reusing the portfolio projector."""

    def __init__(
        self,
        *,
        events: Iterable[FinancialEvent],
        market_prices: Iterable[MarketPrice],
        portfolio_at: Callable[[date], PortfolioProjection],
        valuation_at: Callable[[date], BaseCurrencyValuation],
        valuation_for_portfolio: (
            Callable[[date, PortfolioProjection], BaseCurrencyValuation] | None
        ) = None,
        portfolio_series: (
            Callable[[tuple[date, ...]], tuple[PortfolioProjection, ...]] | None
        ) = None,
    ) -> None:
        self._events = tuple(events)
        self._market_prices = tuple(market_prices)
        self._portfolio_at = portfolio_at
        self._valuation_at = valuation_at
        self._valuation_for_portfolio = valuation_for_portfolio
        self._portfolio_series = portfolio_series

    def portfolio_as_of(
        self, as_of_date: date, *, portfolio: PortfolioProjection | None = None
    ) -> PortfolioAsOfResult:
        portfolio = portfolio if portfolio is not None else self._portfolio_at(as_of_date)
        valuation = (
            self._valuation_for_portfolio(as_of_date, portfolio)
            if self._valuation_for_portfolio is not None
            else self._valuation_at(as_of_date)
        )
        base_values = {
            position.ticker: position.market_value_base for position in valuation.positions
        }
        positions: list[HistoricalPositionCoverage] = []
        valued = 0
        unvalued = 0
        known_value = Decimal("0")
        for position in portfolio.positions:
            if position.is_empty:
                continue
            ticker = str(position.asset.ticker)
            if position.current_price is None:
                positions.append(
                    HistoricalPositionCoverage(
                        ticker=ticker,
                        asset_class=position.asset.asset_class.value,
                        status="UNVALUED",
                        issue="MISSING_HISTORICAL_PRICE",
                    )
                )
                unvalued += 1
                continue
            value = base_values.get(ticker)
            if value is None:
                positions.append(
                    HistoricalPositionCoverage(
                        ticker=ticker,
                        asset_class=position.asset.asset_class.value,
                        status="UNVALUED",
                        issue="MISSING_HISTORICAL_FX",
                    )
                )
                unvalued += 1
                continue
            positions.append(
                HistoricalPositionCoverage(
                    ticker=ticker,
                    asset_class=position.asset.asset_class.value,
                    status="VALUED",
                    issue=None,
                )
            )
            valued += 1
            known_value += value
        status = "COMPLETE" if not unvalued else "PARTIAL" if valued else "INSUFFICIENT"
        issues = tuple(sorted({item.issue for item in positions if item.issue is not None}))
        return PortfolioAsOfResult(
            as_of_date=as_of_date,
            valued_wealth=known_value if valued else None,
            coverage_status=status,
            valued_positions=valued,
            unvalued_positions=unvalued,
            positions=tuple(positions),
            issues=issues,
        )

    def evolution_dates(self, *, start_date: date, end_date: date) -> tuple[date, ...]:
        relevant = {start_date, end_date}
        relevant.update(
            event.effective_date
            for event in self._events
            if start_date <= event.effective_date <= end_date
        )
        relevant.update(
            price.effective_date
            for price in self._market_prices
            if start_date <= price.effective_date <= end_date
        )
        return tuple(sorted(relevant))

    def wealth_series(self, *, start_date: date, end_date: date) -> tuple[PortfolioAsOfResult, ...]:
        results: list[PortfolioAsOfResult] = []
        previous_statuses: dict[str, str] = {}
        dates = self.evolution_dates(start_date=start_date, end_date=end_date)
        portfolios = (
            self._portfolio_series(dates)
            if self._portfolio_series is not None
            else tuple(self._portfolio_at(point) for point in dates)
        )
        for point, portfolio in zip(dates, portfolios, strict=True):
            result = self.portfolio_as_of(point, portfolio=portfolio)
            statuses = {item.ticker: item.status for item in result.positions}
            coverage_changed = any(
                previous_statuses.get(ticker) not in {None, status}
                for ticker, status in statuses.items()
            )
            if coverage_changed:
                result = replace(result, issues=tuple(sorted((*result.issues, "COVERAGE_CHANGE"))))
            previous_statuses = statuses
            results.append(result)
        return tuple(results)
