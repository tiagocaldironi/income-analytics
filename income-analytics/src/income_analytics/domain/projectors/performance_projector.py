"""Temporal performance calculations built on top of portfolio projections."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal
from itertools import groupby
from math import isfinite
from uuid import UUID

from income_analytics.application.base_currency_valuation import MAX_FX_STALE_AGE_DAYS
from income_analytics.application.fx_data import FxRateObservation
from income_analytics.application.performance_coverage import GOOD_COVERAGE, MINIMUM_COVERAGE
from income_analytics.domain.effects.cash_effect import CashEffect
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.capital_flow_type import CapitalFlowType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.market_price import MarketPrice
from income_analytics.domain.projectors.portfolio_projector import PortfolioProjector
from income_analytics.domain.read_models.performance_projection import (
    PerformancePeriod,
    PerformanceProjection,
)
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection
from income_analytics.domain.services.financial_effect_factory import FinancialEffectFactory
from income_analytics.domain.value_objects.money import Money


class PerformanceProjector:
    # Carry the last official close across weekends/short holidays, then mark
    # the valuation missing instead of treating an old quote as current.
    MAX_STALE_PRICE_AGE_DAYS = 7

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
        fx_rates: Iterable[FxRateObservation] = (),
        base_currency: str = "BRL",
    ) -> PerformanceProjection:
        if end_date < start_date:
            raise ValueError("A data final deve ser posterior à data inicial.")
        event_stream, price_stream = tuple(events), tuple(market_prices)
        rate_stream = tuple(fx_rates)
        price_index = cls._price_index(price_stream)
        fx_index = cls._fx_index(rate_stream)
        funding_ledger = cls._implicit_funding_ledger(event_stream, end_date)
        interval_events = tuple(
            event for event in event_stream if start_date <= event.effective_date <= end_date
        )
        flows = tuple(
            event
            for event in interval_events
            if event.event_type in (FinancialEventType.DEPOSIT, FinancialEventType.WITHDRAWAL)
        )
        investor_flows = tuple(
            event
            for event in flows
            if event.capital_flow_type is not CapitalFlowType.INTERNAL_TRANSFER
        )
        contributions = sum(
            (
                event.total_amount
                for event in investor_flows
                if event.event_type is FinancialEventType.DEPOSIT
            ),
            Money.zero(),
        )
        withdrawals = sum(
            (
                event.total_amount
                for event in investor_flows
                if event.event_type is FinancialEventType.WITHDRAWAL
            ),
            Money.zero(),
        )
        implicit_funding_dates = cls._implicit_funding_dates(event_stream, end_date)
        twr_flow_dates = {flow.effective_date for flow in flows} | implicit_funding_dates
        valuation_dates = cls._coverage_dates(start_date, end_date, price_stream)
        valuation_dates.update((start_date, end_date))
        period_start = start_date
        for flow_date in sorted(item for item in twr_flow_dates if start_date <= item <= end_date):
            before_date = flow_date - timedelta(days=1)
            if before_date >= period_start:
                valuation_dates.add(before_date)
            valuation_dates.add(flow_date)
            period_start = flow_date
        portfolio_series = dict(
            zip(
                sorted(valuation_dates),
                PortfolioProjector.project_timeline(
                    event_stream,
                    price_stream,
                    valuation_dates,
                    allow_asset_price_fallback=False,
                    market_data_available=bool(price_stream),
                    max_price_age_days=cls.MAX_STALE_PRICE_AGE_DAYS,
                ),
                strict=True,
            )
        )
        beginning = cls._equity_from_projection(
            event_stream,
            portfolio_series[start_date],
            start_date,
            rate_stream,
            base_currency,
            fx_index=fx_index,
            funding_ledger=funding_ledger,
        )
        ending = cls._equity_from_projection(
            event_stream,
            portfolio_series[end_date],
            end_date,
            rate_stream,
            base_currency,
            fx_index=fx_index,
            funding_ledger=funding_ledger,
        )
        coverage_ratio, missing_assets, missing_value, missing_periods = cls._coverage(
            event_stream,
            price_stream,
            start_date,
            end_date,
            rate_stream,
            base_currency,
            fx_index=fx_index,
            portfolio_series=portfolio_series,
        )
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
                performance_status="INSUFFICIENT_DATA",
                coverage_ratio=coverage_ratio,
                missing_assets=missing_assets,
                missing_value=missing_value,
                missing_periods=missing_periods,
            )
        twr, periods = cls._twr(
            event_stream,
            price_stream,
            start_date,
            end_date,
            flows,
            rate_stream,
            base_currency,
            price_index,
            fx_index=fx_index,
            funding_ledger=funding_ledger,
            portfolio_series=portfolio_series,
            implicit_funding_dates=implicit_funding_dates,
        )
        insufficient = coverage_ratio is not None and coverage_ratio < MINIMUM_COVERAGE
        if insufficient:
            twr = None
        performance_status = (
            "INSUFFICIENT_DATA"
            if insufficient or twr is None
            else "PARTIAL"
            if coverage_ratio is not None and coverage_ratio < GOOD_COVERAGE
            else "AVAILABLE"
        )
        if insufficient:
            coverage_date = missing_periods[0].isoformat() if missing_periods else None
            coverage_detail = f" na data {coverage_date}" if coverage_date else " no período"
            asset_detail = (
                f"; sem cotação recente para {len(missing_assets)} ativo(s)"
                if missing_assets
                else ""
            )
            unavailable_reason = (
                f"Cobertura de valuation de {coverage_ratio * 100:.2f}%{coverage_detail}"
                f"{asset_detail}. Sem valuation de abertura confiável, "
                "não é possível calcular a rentabilidade da carteira neste período."
            )
        elif twr is not None:
            unavailable_reason = None
        else:
            unavailable_reason = "Patrimônio inicial nulo ou dados insuficientes."
        return PerformanceProjection(
            start_date=start_date,
            end_date=end_date,
            beginning_equity=beginning,
            ending_equity=ending,
            total_contributions=contributions,
            total_withdrawals=withdrawals,
            twr=twr,
            xirr=None if insufficient else cls._xirr(investor_flows, ending, end_date),
            periods=periods,
            unavailable_reason=unavailable_reason,
            coverage_ratio=coverage_ratio,
            performance_status=performance_status,
            missing_assets=missing_assets,
            missing_value=missing_value,
            missing_periods=missing_periods,
        )

    @classmethod
    def _twr(
        cls,
        events: tuple[FinancialEvent, ...],
        prices: tuple[MarketPrice, ...],
        start_date: date,
        end_date: date,
        flows: tuple[FinancialEvent, ...],
        fx_rates: tuple[FxRateObservation, ...] = (),
        base_currency: str = "BRL",
        price_index: dict[UUID, tuple[MarketPrice, ...]] | None = None,
        *,
        fx_index: dict[tuple[str, str], tuple[FxRateObservation, ...]] | None = None,
        funding_ledger: tuple[tuple[date, str, Decimal], ...] | None = None,
        portfolio_series: dict[date, PortfolioProjection] | None = None,
        implicit_funding_dates: set[date] | None = None,
    ) -> tuple[Decimal | None, tuple[PerformancePeriod, ...]]:
        factor = Decimal("1")
        periods: list[PerformancePeriod] = []
        period_start = start_date
        if funding_ledger is None:
            funding_ledger = cls._implicit_funding_ledger(events, end_date)
        implicit_dates = (
            implicit_funding_dates
            if implicit_funding_dates is not None
            else cls._implicit_funding_dates(events, end_date)
        )
        flow_dates = {flow.effective_date for flow in flows} | implicit_dates
        ordered_flow_dates = sorted(
            flow_date for flow_date in flow_dates if start_date <= flow_date <= end_date
        )
        if portfolio_series is None:
            valuation_dates = {start_date, end_date}
            period_start = start_date
            for flow_date in ordered_flow_dates:
                before_date = flow_date - timedelta(days=1)
                if before_date >= period_start:
                    valuation_dates.add(before_date)
                valuation_dates.add(flow_date)
                period_start = flow_date
            portfolio_series = dict(
                zip(
                    sorted(valuation_dates),
                    PortfolioProjector.project_timeline(
                        events,
                        prices,
                        valuation_dates,
                        allow_asset_price_fallback=False,
                        market_data_available=bool(prices),
                        max_price_age_days=cls.MAX_STALE_PRICE_AGE_DAYS,
                    ),
                    strict=True,
                )
            )
        opening = cls._equity_from_projection(
            events,
            portfolio_series[start_date],
            start_date,
            fx_rates,
            base_currency,
            fx_index=fx_index,
            funding_ledger=funding_ledger,
        )
        period_start = start_date
        for flow_date in ordered_flow_dates:
            before_date = flow_date - timedelta(days=1)
            if before_date >= period_start:
                closing = cls._equity_from_projection(
                    events,
                    portfolio_series[before_date],
                    before_date,
                    fx_rates,
                    base_currency,
                    fx_index=fx_index,
                    funding_ledger=funding_ledger,
                )
                if opening is None or closing is None or opening.is_zero:
                    return None, tuple(periods)
                result = closing.amount / opening.amount - Decimal("1")
                periods.append(
                    PerformancePeriod(
                        start_date=period_start, end_date=before_date, return_percentage=result
                    )
                )
                factor *= Decimal("1") + result
            opening, period_start = (
                cls._equity_from_projection(
                    events,
                    portfolio_series[flow_date],
                    flow_date,
                    fx_rates,
                    base_currency,
                    fx_index=fx_index,
                    funding_ledger=funding_ledger,
                ),
                flow_date,
            )
        ending = cls._equity_from_projection(
            events,
            portfolio_series[end_date],
            end_date,
            fx_rates,
            base_currency,
            fx_index=fx_index,
            funding_ledger=funding_ledger,
        )
        if opening is None or ending is None or opening.is_zero:
            return None, tuple(periods)
        result = ending.amount / opening.amount - Decimal("1")
        periods.append(
            PerformancePeriod(start_date=period_start, end_date=end_date, return_percentage=result)
        )
        return factor * (Decimal("1") + result) - Decimal("1"), tuple(periods)

    @staticmethod
    def _coverage_dates(
        start_date: date, end_date: date, prices: tuple[MarketPrice, ...]
    ) -> set[date]:
        dates = {start_date, end_date}
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:
                dates.add(current_date)
            current_date += timedelta(days=1)
        dates.update(
            price.effective_date
            for price in prices
            if start_date <= price.effective_date <= end_date
        )
        return dates

    @classmethod
    def _coverage(
        cls,
        events: tuple[FinancialEvent, ...],
        prices: tuple[MarketPrice, ...],
        start_date: date,
        end_date: date,
        fx_rates: tuple[FxRateObservation, ...] = (),
        base_currency: str = "BRL",
        *,
        fx_index: dict[tuple[str, str], tuple[FxRateObservation, ...]] | None = None,
        portfolio_series: dict[date, PortfolioProjection] | None = None,
    ) -> tuple[Decimal | None, tuple[str, ...], Money, tuple[date, ...]]:
        # Assess every weekday, not only days on which some provider returned
        # a quote. Otherwise a synchronized gap between sparse imports can be
        # invisible to coverage and make stale marks look complete.
        dates = cls._coverage_dates(start_date, end_date, prices)
        if portfolio_series is None:
            portfolio_series = dict(
                zip(
                    sorted(dates),
                    PortfolioProjector.project_timeline(
                        events,
                        prices,
                        dates,
                        allow_asset_price_fallback=False,
                        market_data_available=bool(prices),
                        max_price_age_days=cls.MAX_STALE_PRICE_AGE_DAYS,
                    ),
                    strict=True,
                )
            )
        worst_ratio: Decimal | None = None
        worst_missing = Money.zero()
        missing_assets: set[str] = set()
        missing_periods: list[date] = []
        for as_of in sorted(dates):
            portfolio = portfolio_series[as_of]
            positive_cash = Decimal("0")
            cash_values = portfolio.cash_by_currency or ((base_currency, portfolio.cash),)
            for currency, balance in cash_values:
                rate = cls._fx_rate(fx_rates, currency, base_currency, as_of, fx_index)
                if currency.upper() == base_currency.upper():
                    positive_cash += max(balance.amount, Decimal("0"))
                elif rate is not None:
                    positive_cash += max(balance.amount * rate, Decimal("0"))
            covered = positive_cash
            expected = positive_cash
            missing_at_date = Money.zero()
            missing_tickers: set[str] = set()
            for position in portfolio.positions:
                if position.is_empty:
                    continue
                rate = cls._fx_rate(
                    fx_rates, position.asset.currency.code, base_currency, as_of, fx_index
                )
                fx_valid = (
                    position.asset.currency.code.upper() == base_currency.upper()
                    or rate is not None
                )
                if position.current_price is None or not fx_valid:
                    estimate = max(position.cost.amount, Decimal("0")) * (rate or Decimal("1"))
                    missing_at_date += Money(estimate)
                    expected += estimate
                    missing_tickers.add(str(position.asset.ticker))
                else:
                    value = position.market_value.amount * (rate or Decimal("1"))
                    covered += value
                    expected += value
            ratio = (
                max(Decimal("0"), min(Decimal("1"), covered / expected)) if expected > 0 else None
            )
            if ratio is not None and (worst_ratio is None or ratio < worst_ratio):
                worst_ratio, worst_missing = ratio, missing_at_date
                missing_assets = missing_tickers
                missing_periods = [as_of] if missing_tickers else []
            elif ratio is not None and ratio == worst_ratio and missing_tickers:
                missing_assets.update(missing_tickers)
                missing_periods.append(as_of)
        return (
            worst_ratio,
            tuple(sorted(missing_assets)),
            worst_missing,
            tuple(sorted(set(missing_periods))),
        )

    @classmethod
    def _fresh_prices(cls, prices: tuple[MarketPrice, ...], as_of: date) -> tuple[MarketPrice, ...]:
        """Keep the latest quote per asset only when it is recent enough."""
        latest: dict[object, MarketPrice] = {}
        for price in prices:
            if price.effective_date > as_of:
                continue
            previous = latest.get(price.asset.id)
            if previous is None or (price.effective_date, price.registered_at) > (
                previous.effective_date,
                previous.registered_at,
            ):
                latest[price.asset.id] = price
        return tuple(
            price
            for price in latest.values()
            if (as_of - price.effective_date).days <= cls.MAX_STALE_PRICE_AGE_DAYS
        )

    @staticmethod
    def _price_index(prices: tuple[MarketPrice, ...]) -> dict[UUID, tuple[MarketPrice, ...]]:
        grouped: dict[UUID, list[MarketPrice]] = {}
        for price in prices:
            grouped.setdefault(price.asset.id, []).append(price)
        return {
            asset_id: tuple(
                sorted(quotes, key=lambda item: (item.effective_date, item.registered_at))
            )
            for asset_id, quotes in grouped.items()
        }

    @classmethod
    def _fresh_prices_from_index(
        cls, price_index: dict[UUID, tuple[MarketPrice, ...]], as_of: date
    ) -> tuple[MarketPrice, ...]:
        latest: list[MarketPrice] = []
        for quotes in price_index.values():
            end = bisect_right(quotes, as_of, key=lambda item: item.effective_date)
            if not end:
                continue
            quote_date = quotes[end - 1].effective_date
            latest_registered_at = quotes[end - 1].registered_at
            first_equal = end - 1
            while first_equal and (
                quotes[first_equal - 1].effective_date,
                quotes[first_equal - 1].registered_at,
            ) == (quote_date, latest_registered_at):
                first_equal -= 1
            quote = quotes[first_equal]
            if (as_of - quote.effective_date).days <= cls.MAX_STALE_PRICE_AGE_DAYS:
                latest.append(quote)
        return tuple(latest)

    @classmethod
    def _equity(
        cls,
        events: tuple[FinancialEvent, ...],
        prices: tuple[MarketPrice, ...],
        as_of: date,
        fx_rates: tuple[FxRateObservation, ...] = (),
        base_currency: str = "BRL",
        price_index: dict[UUID, tuple[MarketPrice, ...]] | None = None,
        *,
        fx_index: dict[tuple[str, str], tuple[FxRateObservation, ...]] | None = None,
        funding_ledger: tuple[tuple[date, str, Decimal], ...] | None = None,
    ) -> Money | None:
        portfolio: PortfolioProjection = PortfolioProjector.project_as_of(
            events,
            (
                cls._fresh_prices_from_index(price_index, as_of)
                if price_index is not None
                else cls._fresh_prices(prices, as_of)
            ),
            as_of,
            allow_asset_price_fallback=False,
        )
        return cls._equity_from_projection(
            events,
            portfolio,
            as_of,
            fx_rates,
            base_currency,
            fx_index=fx_index,
            funding_ledger=funding_ledger,
        )

    @classmethod
    def _equity_from_projection(
        cls,
        events: tuple[FinancialEvent, ...],
        portfolio: PortfolioProjection,
        as_of: date,
        fx_rates: tuple[FxRateObservation, ...],
        base_currency: str,
        *,
        fx_index: dict[tuple[str, str], tuple[FxRateObservation, ...]] | None = None,
        funding_ledger: tuple[tuple[date, str, Decimal], ...] | None = None,
    ) -> Money | None:
        # A purchase may predate the user's cash ledger. The required funding
        # is normalized into equity and its date becomes a TWR boundary, so it
        # is treated as capital rather than as investment performance.
        equity = Decimal("0")
        for position in portfolio.positions:
            if position.is_empty:
                continue
            rate = cls._fx_rate(
                fx_rates, position.asset.currency.code, base_currency, as_of, fx_index
            )
            if position.asset.currency.code.upper() != base_currency.upper() and rate is None:
                return None
            equity += position.market_value.amount * (rate or Decimal("1"))
        cash = portfolio.cash_by_currency or ((base_currency, portfolio.cash),)
        for currency, balance in cash:
            rate = cls._fx_rate(fx_rates, currency, base_currency, as_of, fx_index)
            if currency.upper() != base_currency.upper() and rate is None:
                return None
            equity += balance.amount * (rate or Decimal("1"))
        implicit = cls._implicit_capital_base(
            events,
            as_of,
            fx_rates,
            base_currency,
            fx_index=fx_index,
            funding_ledger=funding_ledger,
        )
        return None if implicit is None else Money(equity + implicit)

    @classmethod
    def _implicit_capital_base(
        cls,
        events: tuple[FinancialEvent, ...],
        as_of: date,
        fx_rates: tuple[FxRateObservation, ...],
        base_currency: str,
        *,
        fx_index: dict[tuple[str, str], tuple[FxRateObservation, ...]] | None = None,
        funding_ledger: tuple[tuple[date, str, Decimal], ...] | None = None,
    ) -> Decimal | None:
        if funding_ledger is not None:
            funding_by_currency: dict[str, Decimal] = {}
            for funding_date, currency, amount in funding_ledger:
                if funding_date <= as_of:
                    funding_by_currency[currency] = (
                        funding_by_currency.get(currency, Decimal("0")) + amount
                    )
            total = Decimal("0")
            for currency, amount in funding_by_currency.items():
                rate = cls._fx_rate(fx_rates, currency, base_currency, as_of, fx_index)
                if rate is None:
                    return None
                total += amount * rate
            return total
        cash: dict[str, Decimal] = {}
        funding_by_currency: dict[str, Decimal] = {}
        ordered = sorted(
            (event for event in events if event.effective_date <= as_of),
            key=lambda item: (item.effective_date, item.registered_at),
        )
        for effective_date, day_events in groupby(ordered, key=lambda item: item.effective_date):
            day_events = tuple(day_events)
            day_effects: dict[str, Decimal] = {}
            has_purchase: set[str] = set()
            for event in day_events:
                for effect in FinancialEffectFactory.from_event(event):
                    if isinstance(effect, CashEffect):
                        currency = effect.currency_code.upper()
                        day_effects[currency] = (
                            day_effects.get(currency, Decimal("0")) + effect.amount.amount
                        )
                        if event.event_type is FinancialEventType.BUY:
                            has_purchase.add(currency)
            for currency in set(cash) | set(day_effects):
                before = cash.get(currency, Decimal("0"))
                after = before + day_effects.get(currency, Decimal("0"))
                if currency in has_purchase and after < 0:
                    deficit_before = min(before, Decimal("0"))
                    needed = max(Decimal("0"), -(after - deficit_before))
                    funding_by_currency[currency] = (
                        funding_by_currency.get(currency, Decimal("0")) + needed
                    )
                cash[currency] = after
        total = Decimal("0")
        for currency, amount in funding_by_currency.items():
            rate = cls._fx_rate(fx_rates, currency, base_currency, as_of, fx_index)
            if rate is None:
                return None
            total += amount * rate
        return total

    @staticmethod
    def _fx_index(
        rates: tuple[FxRateObservation, ...],
    ) -> dict[tuple[str, str], tuple[FxRateObservation, ...]]:
        grouped: dict[tuple[str, str], list[FxRateObservation]] = {}
        for rate in rates:
            key = (rate.base_currency.upper(), rate.quote_currency.upper())
            grouped.setdefault(key, []).append(rate)
        return {
            key: tuple(sorted(observations, key=lambda item: item.effective_date))
            for key, observations in grouped.items()
        }

    @classmethod
    def _implicit_funding_ledger(
        cls, events: tuple[FinancialEvent, ...], end_date: date
    ) -> tuple[tuple[date, str, Decimal], ...]:
        """Replay dated cash effects once and retain per-currency funding deltas."""
        cash: dict[str, Decimal] = {}
        ledger: list[tuple[date, str, Decimal]] = []
        ordered = sorted(
            (event for event in events if event.effective_date <= end_date),
            key=lambda event: (event.effective_date, event.registered_at),
        )
        for effective_date, day_events in groupby(ordered, key=lambda item: item.effective_date):
            day_effects: dict[str, Decimal] = {}
            has_purchase: set[str] = set()
            for event in day_events:
                for effect in FinancialEffectFactory.from_event(event):
                    if isinstance(effect, CashEffect):
                        currency = effect.currency_code.upper()
                        day_effects[currency] = (
                            day_effects.get(currency, Decimal("0")) + effect.amount.amount
                        )
                        if event.event_type is FinancialEventType.BUY:
                            has_purchase.add(currency)
            for currency in set(cash) | set(day_effects):
                before = cash.get(currency, Decimal("0"))
                after = before + day_effects.get(currency, Decimal("0"))
                if currency in has_purchase and after < 0:
                    prior_deficit = min(before, Decimal("0"))
                    needed = max(Decimal("0"), -(after - prior_deficit))
                    ledger.append((effective_date, currency, needed))
                cash[currency] = after
        return tuple(ledger)

    @staticmethod
    def _fx_rate(
        rates: tuple[FxRateObservation, ...],
        currency: str,
        base: str,
        as_of: date,
        fx_index: dict[tuple[str, str], tuple[FxRateObservation, ...]] | None = None,
    ) -> Decimal | None:
        if currency.upper() == base.upper():
            return Decimal("1")
        if fx_index is None:
            observation = max(
                (
                    rate
                    for rate in rates
                    if rate.base_currency == currency.upper()
                    and rate.quote_currency == base.upper()
                    and rate.effective_date <= as_of
                ),
                key=lambda item: item.effective_date,
                default=None,
            )
        else:
            observations = fx_index.get((currency.upper(), base.upper()), ())
            end = bisect_right(observations, as_of, key=lambda item: item.effective_date)
            if end:
                rate_date = observations[end - 1].effective_date
                first_equal = end - 1
                while first_equal and observations[first_equal - 1].effective_date == rate_date:
                    first_equal -= 1
                observation = observations[first_equal]
            else:
                observation = None
        if observation is None or (as_of - observation.effective_date).days > MAX_FX_STALE_AGE_DAYS:
            return None
        return observation.rate

    @staticmethod
    def _implicit_capital(events: tuple[FinancialEvent, ...], as_of: date) -> Money:
        return sum(
            (amount for _, amount in PerformanceProjector._implicit_funding_events(events, as_of)),
            Money.zero(),
        )

    @staticmethod
    def _implicit_funding_dates(events: tuple[FinancialEvent, ...], as_of: date) -> set[date]:
        return {
            funding_date
            for funding_date, _ in PerformanceProjector._implicit_funding_events(events, as_of)
        }

    @staticmethod
    def _implicit_funding_events(
        events: tuple[FinancialEvent, ...], as_of: date
    ) -> tuple[tuple[date, Money], ...]:
        """Infer only the cash needed by purchases, never by withdrawals."""
        cash = Money.zero()
        fundings: list[tuple[date, Money]] = []
        ordered_events = sorted(
            (item for item in events if item.effective_date <= as_of),
            key=lambda item: (item.effective_date, item.registered_at),
        )
        # TWR boundaries and historic valuations are date-based. Net the day's
        # real cash effects before inferring opening capital so that a dividend
        # reinvested on the same date is not mistaken for a second contribution
        # merely because the BUY happened to be registered first.
        for effective_date, day_events in groupby(
            ordered_events, key=lambda item: item.effective_date
        ):
            cash_before = cash
            day_cash_effect = Money.zero()
            has_purchase = False
            for event in day_events:
                has_purchase = has_purchase or event.event_type is FinancialEventType.BUY
                for effect in FinancialEffectFactory.from_event(event):
                    if isinstance(effect, CashEffect):
                        day_cash_effect += effect.amount
            cash += day_cash_effect
            if has_purchase and cash.amount < Decimal("0"):
                prior_deficit = min(cash_before.amount, Decimal("0"))
                required_amount = max(Decimal("0"), -(cash.amount - prior_deficit))
                if required_amount > 0:
                    fundings.append((effective_date, Money(required_amount)))
        return tuple(fundings)

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
