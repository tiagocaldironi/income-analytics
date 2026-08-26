"""Risk metrics derived from the existing dated portfolio projection stream."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from math import sqrt

from income_analytics.domain.benchmark_rate import BenchmarkRate
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.market_price import MarketPrice
from income_analytics.domain.projectors.portfolio_projector import PortfolioProjector
from income_analytics.domain.read_models.risk_projection import (
    DrawdownPoint,
    PortfolioReturn,
    RiskProjection,
)
from income_analytics.domain.value_objects.money import Money

TRADING_PERIODS_PER_YEAR = 252


class RiskProjector:
    """Derive daily-observation risk measures without treating external flows as return."""

    @classmethod
    def project(
        cls,
        events: Iterable[FinancialEvent],
        market_prices: Iterable[MarketPrice],
        benchmark_rates: Iterable[BenchmarkRate],
        *,
        start_date: date,
        end_date: date,
    ) -> RiskProjection:
        if end_date < start_date:
            raise ValueError("A data final deve ser posterior à data inicial.")
        event_stream, price_stream = tuple(events), tuple(market_prices)
        returns = cls._returns(event_stream, price_stream, start_date, end_date)
        drawdowns, maximum, peak, trough, recovery = cls._drawdowns(returns, start_date)
        periodic_volatility = cls._sample_standard_deviation(
            tuple(point.return_percentage for point in returns)
        )
        annualized_volatility = (
            None
            if periodic_volatility is None
            else Decimal(str(float(periodic_volatility) * sqrt(TRADING_PERIODS_PER_YEAR)))
        )
        sharpe, reason = cls._sharpe(returns, benchmark_rates, periodic_volatility)
        return RiskProjection(
            start_date=start_date,
            end_date=end_date,
            frequency="DAILY_OBSERVATIONS",
            returns=returns,
            drawdown_series=drawdowns,
            periodic_volatility=periodic_volatility,
            annualized_volatility=annualized_volatility,
            maximum_drawdown=maximum,
            peak_date=peak,
            trough_date=trough,
            recovery_date=recovery,
            sharpe_ratio=sharpe,
            sharpe_unavailable_reason=reason,
        )

    @classmethod
    def _returns(
        cls,
        events: tuple[FinancialEvent, ...],
        prices: tuple[MarketPrice, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[PortfolioReturn, ...]:
        dates = sorted(
            {start_date, end_date}
            | {
                event.effective_date
                for event in events
                if start_date <= event.effective_date <= end_date
            }
            | {
                price.effective_date
                for price in prices
                if start_date <= price.effective_date <= end_date
            }
        )
        previous = cls._equity(events, prices, start_date)
        if previous is None:
            return ()
        points: list[PortfolioReturn] = []
        for effective_date in dates:
            if effective_date == start_date:
                continue
            current = cls._equity(events, prices, effective_date)
            if current is None or previous.is_zero:
                return ()
            external_flow = cls._external_flow(events, effective_date)
            period_return = (current.amount - external_flow.amount) / previous.amount - Decimal("1")
            points.append(
                PortfolioReturn(
                    effective_date=effective_date,
                    return_percentage=period_return,
                )
            )
            previous = current
        return tuple(points)

    @staticmethod
    def _equity(
        events: tuple[FinancialEvent, ...], prices: tuple[MarketPrice, ...], as_of: date
    ) -> Money | None:
        portfolio = PortfolioProjector.project_as_of(events, prices, as_of)
        return portfolio.portfolio_equity if portfolio.has_complete_market_data else None

    @staticmethod
    def _external_flow(events: tuple[FinancialEvent, ...], effective_date: date) -> Money:
        total = Money.zero()
        for event in events:
            if event.effective_date != effective_date:
                continue
            if event.event_type is FinancialEventType.DEPOSIT:
                total += event.total_amount
            elif event.event_type is FinancialEventType.WITHDRAWAL:
                total -= event.total_amount
        return total

    @staticmethod
    def _sample_standard_deviation(values: tuple[Decimal, ...]) -> Decimal | None:
        if len(values) < 2:
            return None
        mean = sum(values, Decimal("0")) / Decimal(len(values))
        variance = sum((value - mean) ** 2 for value in values) / Decimal(len(values) - 1)
        return Decimal(str(sqrt(float(variance))))

    @staticmethod
    def _drawdowns(
        returns: tuple[PortfolioReturn, ...], start_date: date
    ) -> tuple[tuple[DrawdownPoint, ...], Decimal | None, date | None, date | None, date | None]:
        wealth = Decimal("100")
        peak_wealth, peak_date = wealth, start_date
        maximum, maximum_peak, trough_date = Decimal("0"), start_date, start_date
        recovered: date | None = None
        points = [DrawdownPoint(effective_date=start_date, drawdown=Decimal("0"))]
        for point in returns:
            wealth *= Decimal("1") + point.return_percentage
            if wealth >= peak_wealth:
                if maximum < 0 and recovered is None and wealth >= peak_wealth:
                    recovered = point.effective_date
                if wealth > peak_wealth:
                    peak_wealth, peak_date = wealth, point.effective_date
            drawdown = wealth / peak_wealth - Decimal("1")
            points.append(DrawdownPoint(effective_date=point.effective_date, drawdown=drawdown))
            if drawdown < maximum:
                maximum, maximum_peak, trough_date = drawdown, peak_date, point.effective_date
                recovered = None
        return tuple(points), maximum, maximum_peak, trough_date, recovered

    @classmethod
    def _sharpe(
        cls,
        returns: tuple[PortfolioReturn, ...],
        benchmark_rates: Iterable[BenchmarkRate],
        volatility: Decimal | None,
    ) -> tuple[Decimal | None, str | None]:
        if volatility is None:
            return None, "São necessários ao menos dois retornos para calcular o Sharpe."
        if volatility == Decimal("0"):
            return None, "Sharpe indisponível quando a volatilidade é zero."
        cdi_by_date = {
            rate.effective_date: rate.return_percentage
            for rate in benchmark_rates
            if rate.name.upper() == "CDI"
        }
        if any(point.effective_date not in cdi_by_date for point in returns):
            return None, "Série CDI insuficiente para o período selecionado."
        excess = tuple(
            point.return_percentage - cdi_by_date[point.effective_date] for point in returns
        )
        mean_excess = sum(excess, Decimal("0")) / Decimal(len(excess))
        return Decimal(str(float(mean_excess / volatility) * sqrt(TRADING_PERIODS_PER_YEAR))), None
