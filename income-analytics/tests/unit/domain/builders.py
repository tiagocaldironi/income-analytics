"""Shared test builders for domain objects."""

from __future__ import annotations

from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.value_objects.ticker import Ticker


def build_asset(**overrides: object) -> Asset:
    values: dict[str, object] = {
        "ticker": Ticker("petr4"),
        "name": "Petrobras PN",
        "asset_type": AssetType.STOCK,
        "asset_class": AssetClass.BRAZILIAN_STOCK,
        "currency": object(),
        "institution": object(),
    }
    values.update(overrides)
    return Asset(**values)  # type: ignore[arg-type]
