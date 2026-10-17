"""Derive concentration across structural asset dimensions."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Callable

from income_analytics.domain.read_models.allocation_projection import (
    AllocationProjection,
    AssetAllocation,
)
from income_analytics.domain.read_models.diversification_projection import (
    DimensionExposure,
    DiversificationDimension,
    DiversificationProjection,
)


class DiversificationProjector:
    @classmethod
    def project(cls, allocation: AllocationProjection) -> DiversificationProjection:
        asset = cls._dimension(allocation, lambda item: str(item.position.asset.ticker))
        classes = cls._dimension(allocation, lambda item: item.position.asset.asset_class.value)
        sector = cls._dimension(
            allocation, lambda item: item.position.asset.sector or "NOT_APPLICABLE"
        )
        country = cls._dimension(allocation, lambda item: item.position.asset.country)
        currency_codes = {
            item.position.asset.currency.code
            for item in allocation.assets
            if not item.position.is_empty and item.position.current_price
        }
        currency = (
            cls._dimension(allocation, lambda item: item.position.asset.currency.code)
            if len(currency_codes) <= 1
            else cls._unavailable(allocation, "Exposição monetária requer conversão FX.")
        )
        return DiversificationProjection(
            asset=asset, asset_class=classes, sector=sector, country=country, currency=currency
        )

    @staticmethod
    def _dimension(
        allocation: AllocationProjection,
        key_for: Callable[[AssetAllocation], str],
    ) -> DiversificationDimension:
        open_assets = [item for item in allocation.assets if not item.position.is_empty]
        valued = [item for item in open_assets if item.position.current_price]
        if not valued or allocation.valuation_coverage != Decimal("1"):
            return DiversificationProjector._unavailable(allocation, "Valuation incompleto.")
        totals: defaultdict[str, Decimal] = defaultdict(Decimal)
        for item in valued:
            totals[key_for(item)] += item.position.market_value.amount
        total = allocation.portfolio_market_value.amount
        exposures = tuple(
            sorted(
                (DimensionExposure(key=key, weight=value / total) for key, value in totals.items()),
                key=lambda item: (-item.weight, item.key),
            )
        )
        return DiversificationDimension(
            exposures=exposures,
            hhi=sum((item.weight**2 for item in exposures), Decimal("0")),
            largest_exposure=exposures[0] if exposures else None,
            coverage=(
                Decimal(len(valued)) / Decimal(len(open_assets)) if open_assets else Decimal("1")
            ),
        )

    @staticmethod
    def _unavailable(allocation: AllocationProjection, reason: str) -> DiversificationDimension:
        return DiversificationDimension(
            exposures=(),
            hhi=None,
            largest_exposure=None,
            coverage=allocation.valuation_coverage,
            unavailable_reason=reason,
        )
