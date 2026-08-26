"""Market-price persistence contract."""

from typing import Protocol

from income_analytics.domain.market_price import MarketPrice


class MarketPriceRepository(Protocol):
    def save(self, price: MarketPrice) -> None: ...

    def list(self) -> tuple[MarketPrice, ...]: ...
