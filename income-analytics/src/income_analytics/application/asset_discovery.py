"""Application boundary for public asset discovery providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from income_analytics.domain.enums.asset_class import AssetClass


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetCandidate:
    external_id: str | None
    symbol: str
    name: str
    instrument_type: str | None
    suggested_asset_class: AssetClass | None
    country: str | None
    currency_code: str | None
    sector: str | None
    source: str


class AssetDiscoveryUnavailable(Exception):
    """Raised when a public discovery source cannot be reached."""


class AssetDiscoveryProvider(Protocol):
    def search(self, query: str, *, limit: int = 8) -> tuple[AssetCandidate, ...]: ...
