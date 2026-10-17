"""Explicit diversification metrics, without cross-currency aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class DimensionExposure:
    key: str
    weight: Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class DiversificationDimension:
    exposures: tuple[DimensionExposure, ...]
    hhi: Decimal | None
    largest_exposure: DimensionExposure | None
    coverage: Decimal
    unavailable_reason: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DiversificationProjection:
    asset: DiversificationDimension
    asset_class: DiversificationDimension
    sector: DiversificationDimension
    country: DiversificationDimension
    currency: DiversificationDimension
