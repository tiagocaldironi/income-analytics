"""Convert partial position and currency-aware cash valuations into base currency."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from income_analytics.application.fx_data import FxRateObservation
from income_analytics.domain.market_price import MarketPrice
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection

MAX_FX_STALE_AGE_DAYS = 5


@dataclass(frozen=True, slots=True, kw_only=True)
class BaseCurrencyPosition:
    ticker: str
    native_currency: str
    market_value_native: Decimal
    market_value_base: Decimal | None
    fx_rate: Decimal | None
    fx_effective_date: date | None
    valuation_available: bool = True
    quantity: Decimal | None = None
    price_effective_date: date | None = None
    price_source: str | None = None
    fx_status: str = "NOT_REQUIRED"


@dataclass(frozen=True, slots=True, kw_only=True)
class BaseCurrencyValuation:
    base_currency: str
    positions: tuple[BaseCurrencyPosition, ...]
    market_value: Decimal | None
    cash: Decimal | None
    equity: Decimal | None
    complete: bool
    known_cash: Decimal = Decimal("0")
    unknown_market_value: tuple[dict[str, object], ...] = ()
    unknown_fx_effect: tuple[dict[str, object], ...] = ()
    valuation_coverage: Decimal = Decimal("100")

    @property
    def known_market_value(self) -> Decimal:
        return self.market_value or Decimal("0")

    @property
    def equity_coverage(self) -> Decimal:
        return self.valuation_coverage


class BaseCurrencyValuationProjector:
    @classmethod
    def project(
        cls,
        portfolio: PortfolioProjection,
        *,
        base_currency: str,
        fx_rates: tuple[FxRateObservation, ...],
        as_of: date,
        market_prices: tuple[MarketPrice, ...] = (),
        max_fx_stale_age_days: int = MAX_FX_STALE_AGE_DAYS,
    ) -> BaseCurrencyValuation:
        base = base_currency.upper()
        positions: list[BaseCurrencyPosition] = []
        converted: list[Decimal] = []
        unknown_market: list[dict[str, object]] = []
        unknown_fx: list[dict[str, object]] = []
        complete = True
        active_count = 0
        valued_count = 0

        for position in portfolio.positions:
            native = position.asset.currency.code.upper()
            observation = cls._rate(fx_rates, native, base, as_of)
            fx_status = cls._fx_status(
                observation, fx_rates, native, base, as_of, max_fx_stale_age_days
            )
            if fx_status != "VALID":
                observation = None
            active = not position.is_empty
            if active:
                active_count += 1
            price_available = not active or position.current_price is not None
            native_value = position.market_value.amount if price_available else None
            amount = (
                native_value
                if native == base
                else (
                    native_value * observation.rate
                    if native_value is not None and observation
                    else None
                )
            )
            if amount is None:
                complete = False
                reason = "MISSING_PRICE" if not price_available else fx_status
                unknown_market.append(
                    {
                        "ticker": str(position.asset.ticker),
                        "currency_code": native,
                        "quantity": position.quantity.value,
                        "reason": reason,
                    }
                )
                if price_available:
                    unknown_fx.append(
                        {
                            "ticker": str(position.asset.ticker),
                            "currency_code": native,
                            "market_value_native": native_value,
                            "reason": "MISSING_FX",
                        }
                    )
            else:
                converted.append(amount)
                if active:
                    valued_count += 1
            price_observation = cls._price_observation(market_prices, position.asset.id, as_of)
            positions.append(
                BaseCurrencyPosition(
                    ticker=str(position.asset.ticker),
                    native_currency=native,
                    market_value_native=position.market_value.amount,
                    market_value_base=amount,
                    fx_rate=observation.rate
                    if observation
                    else (Decimal("1") if native == base else None),
                    fx_effective_date=observation.effective_date if observation else None,
                    valuation_available=amount is not None,
                    quantity=position.quantity.value,
                    price_effective_date=price_observation.effective_date
                    if price_observation
                    else None,
                    price_source=price_observation.provider if price_observation else None,
                    fx_status=fx_status,
                )
            )

        # A zero returned by PositionProjection for a missing quote is not a known value.
        market_value = sum(converted, Decimal("0"))
        cash_buckets = portfolio.cash_by_currency or ((base, portfolio.cash),)
        known_cash = Decimal("0")
        for currency, balance in cash_buckets:
            native = currency.upper()
            if native == base:
                known_cash += balance.amount
                continue
            observation = cls._rate(fx_rates, native, base, as_of)
            fx_status = cls._fx_status(
                observation, fx_rates, native, base, as_of, max_fx_stale_age_days
            )
            if fx_status == "VALID" and observation:
                known_cash += balance.amount * observation.rate
            else:
                complete = False
                unknown_fx.append(
                    {
                        "currency_code": native,
                        "cash_native": balance.amount,
                        "reason": fx_status,
                        "fx_effective_date": observation.effective_date if observation else None,
                        "fx_source": observation.source if observation else None,
                    }
                )

        coverage = (
            Decimal("100")
            if active_count == 0
            else Decimal(valued_count) / Decimal(active_count) * Decimal("100")
        )
        return BaseCurrencyValuation(
            base_currency=base,
            positions=tuple(positions),
            market_value=market_value,
            cash=known_cash,
            equity=market_value + known_cash,
            complete=complete,
            known_cash=known_cash,
            unknown_market_value=tuple(unknown_market),
            unknown_fx_effect=tuple(unknown_fx),
            valuation_coverage=coverage,
        )

    @staticmethod
    def _rate(
        rates: tuple[FxRateObservation, ...], base: str, quote: str, as_of: date
    ) -> FxRateObservation | None:
        candidates = [
            rate
            for rate in rates
            if rate.base_currency == base
            and rate.quote_currency == quote
            and rate.effective_date <= as_of
        ]
        return max(candidates, key=lambda rate: rate.effective_date) if candidates else None

    @classmethod
    def _fx_status(
        cls,
        observation: FxRateObservation | None,
        rates: tuple[FxRateObservation, ...],
        native: str,
        base: str,
        as_of: date,
        max_stale_age_days: int,
    ) -> str:
        if native == base:
            return "VALID"
        if observation is None:
            return (
                "MISSING_FX"
                if not any(
                    item.base_currency == native
                    and item.quote_currency == base
                    and item.effective_date <= as_of
                    for item in rates
                )
                else "STALE_FX"
            )
        age = (as_of - observation.effective_date).days
        return "VALID" if age <= max_stale_age_days else "STALE_FX"

    @staticmethod
    def _price_observation(
        prices: tuple[MarketPrice, ...], asset_id: object, as_of: date
    ) -> MarketPrice | None:
        candidates = [
            price
            for price in prices
            if price.asset.id == asset_id and price.effective_date <= as_of
        ]
        return max(
            candidates, key=lambda price: (price.effective_date, price.registered_at), default=None
        )
