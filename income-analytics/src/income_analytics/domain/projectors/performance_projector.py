"""Temporal performance calculations built on top of portfolio projections."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal
from math import isfinite

from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.market_price import MarketPrice
from income_analytics.domain.projectors.portfolio_projector import PortfolioProjector
from income_analytics.domain.read_models.performance_projection import (
    PerformancePeriod,
    PerformanceProjection,
)
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection
from income_analytics.domain.value_objects.money import Money


class PerformanceProjector:
    """Calculate cumulative TWR and annualized XIRR from dated portfolio data.

    Each external flow closes the previous subperiod at the end of the prior
    date and opens the next one at the end of the flow date. This neutralizes
    deposits and withdrawals using the existing as-of valuation mechanism.
    """

    @classmethod
    def project(
        cls,
        events: Iterable[FinancialEvent],
        market_prices: Iterable[MarketPrice],
        *,
        start_date: date,
        end_date: date,
    ) -> PerformanceProjection:
        if end_date < start_date:
            raise ValueError("A data final deve ser posterior à data inicial.")
        event_stream, price_stream = tuple(events), tuple(market_prices)
        interval_events = tuple(
            event for event in event_stream if start_date <= event.effective_date <= end_date
        )
        flows = tuple(
            event
            for event in interval_events
            if event.event_type in (FinancialEventType.DEPOSIT, FinancialEventType.WITHDRAWAL)
        )
        contributions = sum(
            (
                event.total_amount
                for event in flows
                if event.event_type is FinancialEventType.DEPOSIT
            ),
            Money.zero(),
        )
        withdrawals = sum(
            (
                event.total_amount
                for event in flows
                if event.event_type is FinancialEventType.WITHDRAWAL
            ),
            Money.zero(),
        )
        beginning = cls._equity(event_stream, price_stream, start_date)
        ending = cls._equity(event_stream, price_stream, end_date)
        if beginning is None or ending is None:
            return PerformanceProjection(
                start_date=start_date,
                end_date=end_date,
                beginning_equity=beginning,
                ending_equity=ending,
                total_contributions=contributions,
                total_withdrawals=withdrawals,
                twr=None,
                xirr=None,
                unavailable_reason="Cotações insuficientes para avaliar o patrimônio no período.",
            )
        twr, periods = cls._twr(event_stream, price_stream, start_date, end_date, flows)
        return PerformanceProjection(
            start_date=start_date,
            end_date=end_date,
            beginning_equity=beginning,
            ending_equity=ending,
            total_contributions=contributions,
            total_withdrawals=withdrawals,
            twr=twr,
            xirr=cls._xirr(flows, ending, end_date),
            periods=periods,
            unavailable_reason=None
            if twr is not None
            else "Patrimônio inicial nulo ou dados insuficientes.",
        )

    @classmethod
    def _twr(
        cls,
        events: tuple[FinancialEvent, ...],
        prices: tuple[MarketPrice, ...],
        start_date: date,
        end_date: date,
        flows: tuple[FinancialEvent, ...],
    ) -> tuple[Decimal | None, tuple[PerformancePeriod, ...]]:
        factor = Decimal("1")
        periods: list[PerformancePeriod] = []
        period_start = start_date
        opening = cls._equity(events, prices, start_date)
        for flow_date in sorted({flow.effective_date for flow in flows}):
            before_date = flow_date - timedelta(days=1)
            if before_date >= period_start:
                closing = cls._equity(events, prices, before_date)
                if opening is None or closing is None or opening.is_zero:
                    return None, tuple(periods)
                result = closing.amount / opening.amount - Decimal("1")
                periods.append(
                    PerformancePeriod(
                        start_date=period_start, end_date=before_date, return_percentage=result
                    )
                )
                factor *= Decimal("1") + result
            opening, period_start = cls._equity(events, prices, flow_date), flow_date
        ending = cls._equity(events, prices, end_date)
        if opening is None or ending is None or opening.is_zero:
            return None, tuple(periods)
        result = ending.amount / opening.amount - Decimal("1")
        periods.append(
            PerformancePeriod(start_date=period_start, end_date=end_date, return_percentage=result)
        )
        return factor * (Decimal("1") + result) - Decimal("1"), tuple(periods)

    @staticmethod
    def _equity(
        events: tuple[FinancialEvent, ...], prices: tuple[MarketPrice, ...], as_of: date
    ) -> Money | None:
        portfolio: PortfolioProjection = PortfolioProjector.project_as_of(events, prices, as_of)
        return portfolio.portfolio_equity if portfolio.has_complete_market_data else None

    @staticmethod
    def _xirr(
        flows: tuple[FinancialEvent, ...], ending_equity: Money, end_date: date
    ) -> Decimal | None:
        cashflows = [
            (
                event.effective_date,
                -float(event.total_amount.amount)
                if event.event_type is FinancialEventType.DEPOSIT
                else float(event.total_amount.amount),
            )
            for event in flows
        ]
        cashflows.append((end_date, float(ending_equity.amount)))
        if not any(value < 0 for _, value in cashflows) or not any(
            value > 0 for _, value in cashflows
        ):
            return None
        origin = min(flow_date for flow_date, _ in cashflows)

        def npv(rate: float) -> float:
            return float(
                sum(
                    value / (1.0 + rate) ** ((flow_date - origin).days / 365.0)
                    for flow_date, value in cashflows
                )
            )

        low, high = -0.999999, 1.0
        low_value, high_value = npv(low), npv(high)
        while low_value * high_value > 0 and high < 1_000_000:
            high, high_value = high * 2, npv(high * 2)
        if low_value * high_value > 0:
            return None
        for _ in range(200):
            middle = (low + high) / 2
            value = npv(middle)
            if not isfinite(value):
                return None
            if abs(value) < 1e-9:
                return Decimal(str(middle))
            if low_value * value <= 0:
                high, high_value = middle, value
            else:
                low, low_value = middle, value
        return Decimal(str((low + high) / 2))
