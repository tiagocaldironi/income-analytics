"""Asset persistence contract."""

from __future__ import annotations

from typing import Protocol

from income_analytics.domain.entities.asset import Asset


class AssetRepository(Protocol):
    def save(self, asset: Asset) -> None: ...

    def get_by_ticker(self, ticker: str) -> Asset | None: ...

    def list(self) -> tuple[Asset, ...]: ...
