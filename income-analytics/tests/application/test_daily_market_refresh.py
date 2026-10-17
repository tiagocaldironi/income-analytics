from datetime import date
from decimal import Decimal

from income_analytics.application.market_data import MarketPriceObservation
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType


class FakeMarketProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def latest_price(self, symbol: str) -> MarketPriceObservation:
        self.calls.append(symbol)
        return MarketPriceObservation(
            symbol=symbol,
            price=Decimal("11"),
            currency_code="BRL",
            effective_date=date(2026, 1, 2),
            source="test",
        )


def test_daily_refresh_only_updates_open_position_once_per_day() -> None:
    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("1"),
        unit_price=Decimal("10"),
        effective_date=date(2026, 1, 1),
    )
    provider = FakeMarketProvider()

    first = session.refresh_open_market_prices(lambda _: provider, today=date(2026, 1, 2))
    second = session.refresh_open_market_prices(lambda _: provider, today=date(2026, 1, 2))

    assert first == (1, (), ())
    assert second == (0, (), ("PETR4",))
    assert provider.calls == ["PETR4"]
