"""Explain a dated change in wealth from the existing portfolio ledger."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from income_analytics.application.base_currency_valuation import BaseCurrencyValuation
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.projectors.performance_projector import PerformanceProjector
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection

INCOME_EVENTS = {
    FinancialEventType.DIVIDEND,
    FinancialEventType.INTEREST_ON_EQUITY,
    FinancialEventType.FII_INCOME,
}


@dataclass(frozen=True, slots=True, kw_only=True)
class WealthExplanation:
    """A base-currency reconciliation of two persisted portfolio valuations."""

    payload: dict[str, object]


class WealthExplanationService:
    """Build a wealth explanation without fetching prices or recalculating TWR."""

    def __init__(
        self,
        *,
        events: Iterable[FinancialEvent],
        portfolio_at: Callable[[date], PortfolioProjection],
        valuation_at: Callable[[date], BaseCurrencyValuation],
        performance_at: Callable[[date, date], object],
    ) -> None:
        self._events = tuple(events)
        self._portfolio_at = portfolio_at
        self._valuation_at = valuation_at
        self._performance_at = performance_at

    def explain(self, *, start_date: date, end_date: date) -> WealthExplanation:
        if end_date < start_date:
            raise ValueError("A data final deve ser posterior à data inicial.")
        opening_portfolio = self._portfolio_at(start_date)
        closing_portfolio = self._portfolio_at(end_date)
        opening = self._valuation_at(start_date)
        closing = self._valuation_at(end_date)
        events = tuple(e for e in self._events if start_date < e.effective_date <= end_date)
        start_value = opening.known_market_value
        end_value = closing.known_market_value
        change = end_value - start_value

        converted: dict[int, Decimal] = {}
        unconverted_events = 0
        for event in events:
            if event.event_type not in {FinancialEventType.BUY, FinancialEventType.SELL, *INCOME_EVENTS}:
                continue
            amount = self._event_amount_in_base(event, closing.base_currency)
            if amount is None:
                unconverted_events += 1
            else:
                converted[id(event)] = amount
        contributors = self._contributors(
            opening_portfolio=opening_portfolio,
            closing_portfolio=closing_portfolio,
            opening=opening,
            closing=closing,
            events=events,
            event_amounts=converted,
        )
        rows = contributors["rows"]
        acquisitions = sum((r["flows"] for r in rows), Decimal("0"))
        fixed_income = sum((r["valuation_change"] for r in rows if r["asset_class"] == "FIXED_INCOME"), Decimal("0"))
        valuation_adjustments = sum((r["valuation_change"] for r in rows if not r["valuation_available"]), Decimal("0"))
        appreciation = sum((r["valuation_change"] for r in rows if r["valuation_available"] and r["asset_class"] != "FIXED_INCOME"), Decimal("0"))
        residual = change - acquisitions - fixed_income - valuation_adjustments - appreciation
        if abs(residual) < Decimal("0.00000001"):
            residual = Decimal("0")
        valuation_coverage = min(opening.valuation_coverage, closing.valuation_coverage)
        explanation_coverage = self._component_coverage(change, residual)

        income_children = self._income_children(events, closing.base_currency, converted)
        income_total = sum((x["signed_amount"] for x in income_children), Decimal("0"))
        dividends = sum((x["signed_amount"] for x in income_children if x["event_type"] == "DIVIDEND"), Decimal("0"))
        jcp = sum((x["signed_amount"] for x in income_children if x["event_type"] == "INTEREST_ON_EQUITY"), Decimal("0"))
        fii_income = sum((x["signed_amount"] for x in income_children if x["event_type"] == "FII_INCOME"), Decimal("0"))
        acquisition_children = self._flow_children(rows)
        components = [
            self._component("NET_ACQUISITIONS", "Aquisições líquidas", acquisitions, acquisition_children),
            self._component("MARKET_VALUATION", "Valorização dos ativos", appreciation, self._children(rows, lambda r: r["valuation_available"] and r["asset_class"] != "FIXED_INCOME")),
            self._component("FIXED_INCOME_ACCRUAL", "Rentabilidade da renda fixa", fixed_income, self._children(rows, lambda r: r["asset_class"] == "FIXED_INCOME")),
            self._component("VALUATION_ADJUSTMENTS", "Ajustes de valuation", valuation_adjustments, self._children(rows, lambda r: not r["valuation_available"])),
            self._component("UNEXPLAINED", "Variação não explicada", residual),
        ]
        components = [x for x in components if x["signed_amount"] != 0]
        expected_end = start_value + sum((x["signed_amount"] for x in components), Decimal("0"))
        reconciliation_difference = end_value - expected_end
        if abs(reconciliation_difference) < Decimal("0.00000001"):
            reconciliation_difference = Decimal("0")
        status = "COMPLETE" if opening.complete and closing.complete and residual == 0 and not unconverted_events else "PARTIAL"
        performance = self._performance_at(start_date, end_date)
        implicit_funding = PerformanceProjector._implicit_funding_events(self._events, end_date)
        return WealthExplanation(payload={
            "period": {"start_date": start_date, "end_date": end_date},
            "base_currency": closing.base_currency,
            "asset_balance": {"start": start_value, "end": end_value, "change": change,
                              "change_percentage": change / start_value if start_value > 0 else None},
            "bridge": {"net_acquisitions": acquisitions, "market_appreciation": appreciation,
                       "fixed_income_return": fixed_income, "fx_effect": None,
                       "valuation_adjustments": valuation_adjustments, "other_asset_effect": Decimal("0"),
                       "unexplained": residual},
            "income_generated": {"total": income_total, "dividends": dividends, "jcp": jcp,
                                 "fii_income": fii_income,
                                 "other_distributed_income": income_total-dividends-jcp-fii_income},
            "summary": {"opening_wealth": start_value, "closing_wealth": end_value,
                        "absolute_change": change,
                        "percentage_wealth_change": change / start_value if start_value > 0 else None,
                        "percentage_return_status": "AVAILABLE" if start_value > 0 else "RETURN_PERCENTAGE_UNAVAILABLE",
                        "percentage_return_reason": None if start_value > 0 else "INVALID_OPENING_ASSET_VALUE"},
            "reconciliation": {"net_acquisitions": acquisitions, "market_appreciation": appreciation,
                               "asset_appreciation": appreciation, "fixed_income_return": fixed_income,
                               "paid_income": income_total, "other_explained_changes": valuation_adjustments+residual,
                               "unexplained_change": residual, "economic_result": None,
                               "expected_closing_wealth": expected_end,
                               "reconciliation_difference": reconciliation_difference,
                               "reconstructed_opening_equity": None, "reconstructed_closing_equity": None,
                               "reconstructed_equity_change": None, "reconstructed_reconciliation_difference": None},
            "components": components,
            "by_asset_class": contributors["classes"],
            "top_contributors": contributors["top"],
            "performance": self._performance_payload(performance),
            "data_quality": {"coverage_status": status, "coverage_percentage": explanation_coverage,
                             "explanation_coverage_percentage": explanation_coverage,
                             "valuation_coverage_percentage": valuation_coverage,
                             "valuation_complete": opening.complete and closing.complete,
                             "opening_known_market_value": start_value, "closing_known_market_value": end_value,
                             "implicit_cash_used_in_asset_balance": False,
                             "twr_boundary_compatibility": "IMPLICIT_BUY_FUNDING_PRESENT" if implicit_funding else "NO_IMPLICIT_BUY_FUNDING",
                             "twr_algorithm_changed": False, "unknown_market_value": closing.unknown_market_value,
                             "unknown_fx_effect": closing.unknown_fx_effect,
                             "unconverted_event_count": unconverted_events,
                             "attention_codes": [] if status == "COMPLETE" else ["PARTIAL_VALUATION_COVERAGE"]},
        })

    def _event_amount_in_base(self, event: FinancialEvent, base_currency: str) -> Decimal | None:
        amount = event.total_amount.amount
        currency = event.asset.currency.code.upper() if event.asset is not None else base_currency.upper()
        if currency == base_currency.upper():
            return amount
        valuation = self._valuation_at(event.effective_date)
        ticker = str(event.asset.ticker) if event.asset is not None else None
        position = next((p for p in valuation.positions if p.ticker == ticker), None)
        return amount * position.fx_rate if position is not None and position.fx_rate is not None else None

    @staticmethod
    def _component(
        component_type: str,
        label: str,
        signed_amount: Decimal,
        children: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return {
            "component_type": component_type,
            "label": label,
            "signed_amount": signed_amount,
            "direction": "POSITIVE"
            if signed_amount > 0
            else "NEGATIVE"
            if signed_amount < 0
            else "NEUTRAL",
            "children": children or [],
            "source_count": len(children or []),
        }

    @staticmethod
    def _component_coverage(change: Decimal, unexplained: Decimal) -> Decimal | None:
        if change == 0:
            return Decimal("100") if unexplained == 0 else Decimal("0")
        return max(Decimal("0"), Decimal("100") - abs(unexplained) / abs(change) * Decimal("100"))

    @staticmethod
    def _children(rows, predicate):
        return [
            {
                "asset_class": row["asset_class"],
                "ticker": row["ticker"],
                "label": row["name"],
                "signed_amount": row["valuation_change"],
                "valuation_available": row["valuation_available"],
                "source_count": 1,
            }
            for row in rows
            if predicate(row)
        ]

    @staticmethod
    def _flow_children(rows):
        return [
            {"asset_class": row["asset_class"], "ticker": row["ticker"], "label": row["name"],
             "signed_amount": row["flows"], "valuation_available": row["valuation_available"], "source_count": 1}
            for row in rows if row["flows"] != 0
        ]

    @staticmethod
    def _income_children(events, base_currency: str, amounts: dict[int, Decimal]):
        return [
            {
                "asset_class": event.asset.asset_class.value,
                "ticker": str(event.asset.ticker),
                "label": event.asset.name,
                "signed_amount": amounts[id(event)],
                "event_type": event.event_type.value,
                "source_count": 1,
            }
            for event in events
            if event.asset is not None
            and event.event_type in INCOME_EVENTS
            and id(event) in amounts
        ]

    @staticmethod
    def _performance_payload(performance: object) -> dict[str, object]:
        twr = getattr(performance, "twr", None)
        return {
            "status": "AVAILABLE" if twr is not None else "INSUFFICIENT_DATA",
            "twr": twr,
            "xirr": getattr(performance, "xirr", None),
            "unavailable_reason": getattr(performance, "unavailable_reason", None),
            "issues": [] if twr is not None else ["MISSING_BOUNDARY_VALUATION"],
        }

    @staticmethod
    def _contributors(
        *,
        opening_portfolio: PortfolioProjection,
        closing_portfolio: PortfolioProjection,
        opening: BaseCurrencyValuation,
        closing: BaseCurrencyValuation,
        events: Iterable[FinancialEvent],
        event_amounts: dict[int, Decimal],
    ) -> dict[str, object]:
        opening_values = {item.ticker: item.market_value_base for item in opening.positions}
        closing_values = {item.ticker: item.market_value_base for item in closing.positions}
        assets = {
            str(position.asset.ticker): position.asset
            for position in (*opening_portfolio.positions, *closing_portfolio.positions)
        }
        buys: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        sells: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        income: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for event in events:
            if event.asset is None:
                continue
            ticker = str(event.asset.ticker)
            if event.event_type is FinancialEventType.BUY:
                buys[ticker] += event_amounts.get(id(event), Decimal("0"))
            elif event.event_type is FinancialEventType.SELL:
                sells[ticker] += event_amounts.get(id(event), Decimal("0"))
            elif event.event_type in INCOME_EVENTS:
                income[ticker] += event_amounts.get(id(event), Decimal("0"))
        rows = []
        for ticker, asset in assets.items():
            start = opening_values.get(ticker) or Decimal("0")
            end_value = closing_values.get(ticker)
            # For an unvalued closing position, retain the known purchase/sale
            # cash leg in the composition bridge. The missing position value is
            # reported separately as valuation coverage, not as unexplained cash.
            end = end_value if end_value is not None else Decimal("0")
            valuation_change = end - start - buys[ticker] + sells[ticker]
            contribution = valuation_change
            rows.append(
                {
                    "ticker": ticker,
                    "name": asset.name,
                    "asset_class": asset.asset_class.value,
                    "currency_code": asset.currency.code.upper(),
                    "opening_value": start,
                    "closing_value": end_value,
                    "valuation_available": end_value is not None
                    and (ticker not in opening_values or opening_values[ticker] is not None),
                    "flows": buys[ticker] - sells[ticker],
                    "paid_income": income[ticker],
                    "valuation_change": valuation_change,
                    "contribution": contribution,
                }
            )
        classes: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for row in rows:
            classes[str(row["asset_class"])] += row["contribution"]
        return {
            "rows": rows,
            "classes": [
                {"asset_class": asset_class, "contribution": contribution}
                for asset_class, contribution in sorted(classes.items())
            ],
            "top": {
                "positive": sorted(
                    (row for row in rows if row["contribution"] > 0),
                    key=lambda row: row["contribution"],
                    reverse=True,
                )[:5],
                "negative": sorted(
                    (row for row in rows if row["contribution"] < 0),
                    key=lambda row: row["contribution"],
                )[:5],
            },
        }
