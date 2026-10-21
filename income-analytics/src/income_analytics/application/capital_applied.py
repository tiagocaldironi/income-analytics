"""Conservative aggregation of currently held acquisition cost."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from income_analytics.application.fx_data import FxRateObservation
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.capital_flow_type import CapitalFlowType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection

_TRADED_CLASSES_WITH_CANONICAL_COST = frozenset(
    {
        AssetClass.BRAZILIAN_STOCK,
        AssetClass.BRAZILIAN_ETF,
        AssetClass.FII,
        AssetClass.FIXED_INCOME,
        AssetClass.CRYPTO,
        AssetClass.INTERNATIONAL,
        AssetClass.INTERNATIONAL_ETF,
        AssetClass.US_REIT,
    }
)


@dataclass(frozen=True, slots=True)
class CapitalApplied:
    amount: Decimal | None
    partial_amount: Decimal | None
    status: str
    incomplete_assets: tuple[str, ...]
    incomplete_reasons: tuple[tuple[str, str], ...]
    included_position_count: int
    position_count: int

    def as_payload(self) -> dict[str, object]:
        return {
            "capital_applied": self.amount,
            "capital_applied_partial_amount": self.partial_amount,
            "capital_applied_status": self.status,
            "capital_applied_incomplete_assets": list(self.incomplete_assets),
            "capital_applied_incomplete_reasons": [
                {"ticker": ticker, "reason": reason}
                for ticker, reason in self.incomplete_reasons
            ],
            "capital_applied_included_position_count": self.included_position_count,
            "capital_applied_position_count": self.position_count,
        }


def calculate_capital_applied(
    projection: PortfolioProjection,
    *,
    base_currency: str,
    events: Iterable[FinancialEvent] = (),
    fx_rates: Iterable[FxRateObservation] = (),
) -> CapitalApplied:
    """Sum canonical open-position cost only when all positions are comparable.

    BRL fixed-income positions use their recorded principal basis. Foreign basis
    is rebuilt from BUY/SELL events using the historical FX rate on each trade
    date, so sales reduce translated basis at average cost rather than using
    current FX or sale proceeds.
    """
    positions = tuple(position for position in projection.positions if not position.is_empty)
    if not positions:
        return CapitalApplied(Decimal("0"), Decimal("0"), "ZERO", (), (), 0, 0)

    included: list[Decimal] = []
    incomplete: list[tuple[str, str]] = []
    base = base_currency.upper()
    foreign_costs, foreign_errors = _foreign_open_costs(
        projection,
        events=tuple(events),
        fx_rates=tuple(fx_rates),
        base_currency=base,
    )
    for position in positions:
        ticker = str(position.asset.ticker)
        currency = position.asset.currency.code.upper()
        if position.asset.asset_class not in _TRADED_CLASSES_WITH_CANONICAL_COST:
            incomplete.append((ticker, "modelo de custo específico não conectado"))
        elif currency != base:
            if ticker in foreign_errors:
                incomplete.append((ticker, foreign_errors[ticker]))
            elif ticker not in foreign_costs:
                incomplete.append((ticker, "custo não convertido pela taxa histórica"))
            else:
                included.append(foreign_costs[ticker])
        elif position.cost.amount <= 0:
            incomplete.append((ticker, "custo de aquisição ausente"))
        else:
            included.append(position.cost.amount)

    if incomplete:
        return CapitalApplied(
            None,
            sum(included, Decimal("0")) if included else None,
            "PARTIAL" if included else "UNAVAILABLE",
            tuple(ticker for ticker, _ in sorted(incomplete)),
            tuple(sorted(incomplete)),
            len(included),
            len(positions),
        )
    return CapitalApplied(
        sum(included, Decimal("0")),
        None,
        "AVAILABLE",
        (),
        (),
        len(included),
        len(positions),
    )


def _foreign_open_costs(
    projection: PortfolioProjection,
    *,
    events: tuple[FinancialEvent, ...],
    fx_rates: tuple[FxRateObservation, ...],
    base_currency: str,
) -> tuple[dict[str, Decimal], dict[str, str]]:
    """Return translated open basis only when the event and FX evidence is complete."""
    foreign_positions = {
        str(position.asset.ticker): position
        for position in projection.positions
        if not position.is_empty and position.asset.currency.code.upper() != base_currency
    }
    if not foreign_positions:
        return {}, {}

    rate_history: dict[tuple[str, str], tuple[FxRateObservation, ...]] = {}
    for observation in fx_rates:
        key = (observation.base_currency.upper(), observation.quote_currency.upper())
        rate_history.setdefault(key, ())
        rate_history[key] = (*rate_history[key], observation)
    rate_history = {
        key: tuple(sorted(values, key=lambda item: item.effective_date))
        for key, values in rate_history.items()
    }

    costs: dict[str, Decimal] = {}
    errors: dict[str, str] = {}
    for ticker, position in foreign_positions.items():
        currency = position.asset.currency.code.upper()
        rate_series = rate_history.get((currency, base_currency), ())
        asset_events = sorted(
            (event for event in events if event.asset and str(event.asset.ticker) == ticker),
            key=lambda event: (event.effective_date, event.registered_at),
        )
        if not asset_events:
            errors[ticker] = "custo não convertido pela taxa histórica"
            continue
        quantity = Decimal("0")
        cost = Decimal("0")
        error: str | None = None
        for event in asset_events:
            if event.event_type not in (FinancialEventType.BUY, FinancialEventType.SELL):
                # Income events do not change acquisition basis. Corporate actions
                # and position transfers require a separate basis rule.
                if event.event_type in (
                    FinancialEventType.DIVIDEND,
                    FinancialEventType.INTEREST_ON_EQUITY,
                    FinancialEventType.FII_INCOME,
                ):
                    continue
                error = "histórico de operações exige regra de custo adicional"
                break
            if event.event_type is FinancialEventType.SELL and event.financial_status == "DATA_GAP":
                continue
            if event.quantity is None or event.unit_price is None:
                error = "operação sem quantidade ou preço para reconstruir o custo"
                break
            rate = _rate_on_or_before(rate_series, event.effective_date)
            if rate is None:
                error = "câmbio histórico ausente na data de uma operação"
                break
            event_quantity = event.quantity.value
            event_amount = event_quantity * event.unit_price.amount
            if event.event_type is FinancialEventType.BUY:
                quantity += event_quantity
                cost += event_amount * rate
            else:
                # Unmatched custody transfers are intentionally ignored by the
                # position projector; mirror that treatment here.
                if event_quantity > quantity and (
                    event.financial_status == "DATA_GAP"
                    or event.capital_flow_type is CapitalFlowType.INTERNAL_TRANSFER
                ):
                    continue
                if event_quantity > quantity or quantity <= 0:
                    error = "venda sem posição de origem suficiente"
                    break
                cost -= cost * event_quantity / quantity
                quantity -= event_quantity
        if error:
            errors[ticker] = error
        elif quantity != position.quantity.value:
            errors[ticker] = "operações disponíveis não reconciliam a quantidade atual"
        elif cost <= 0:
            errors[ticker] = "custo de aquisição ausente"
        else:
            costs[ticker] = cost
    return costs, errors


def _rate_on_or_before(
    observations: tuple[FxRateObservation, ...], effective_date: date
) -> Decimal | None:
    applicable = [item for item in observations if item.effective_date <= effective_date]
    return applicable[-1].rate if applicable else None
