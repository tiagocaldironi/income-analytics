"""Conservative aggregation of currently held acquisition cost."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection

_TRADED_CLASSES_WITH_CANONICAL_COST = frozenset(
    {
        AssetClass.BRAZILIAN_STOCK,
        AssetClass.BRAZILIAN_ETF,
        AssetClass.FII,
        AssetClass.CRYPTO,
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
    projection: PortfolioProjection, *, base_currency: str
) -> CapitalApplied:
    """Sum canonical open-position cost only when all positions are comparable.

    The projector's cost basis is native-currency and already applies average-cost
    sales. We deliberately do not convert foreign cost using today's FX rate or
    infer cost for asset classes with separate financial models.
    """
    positions = tuple(position for position in projection.positions if not position.is_empty)
    if not positions:
        return CapitalApplied(Decimal("0"), Decimal("0"), "ZERO", (), (), 0, 0)

    included: list[Decimal] = []
    incomplete: list[tuple[str, str]] = []
    base = base_currency.upper()
    for position in positions:
        ticker = str(position.asset.ticker)
        if position.asset.currency.code.upper() != base:
            incomplete.append((ticker, "custo não convertido pela taxa histórica"))
        elif position.asset.asset_class not in _TRADED_CLASSES_WITH_CANONICAL_COST:
            incomplete.append((ticker, "modelo de custo específico não conectado"))
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
