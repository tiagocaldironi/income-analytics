from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType


def test_persistent_session_reconstructs_asset_event_price_benchmark_and_policy() -> None:
    ticker = f"T{uuid4().hex[:8]}"
    first = PortfolioSession(persistent=True)
    first.register_trade(
        event_type=FinancialEventType.BUY,
        ticker=ticker,
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("2"),
        unit_price=Decimal("10"),
        effective_date=date(2026, 1, 1),
    )
    first.update_market_price(
        ticker=ticker, current_price=Decimal("12"), effective_date=date(2026, 1, 2)
    )
    first.register_benchmark_rate(
        name="TEST_CDI", return_percentage=Decimal("0.001"), effective_date=date(2026, 1, 2)
    )
    first.set_allocation_policy(
        AllocationPolicy(targets={AssetClass.BRAZILIAN_STOCK: Decimal("1")})
    )

    rebuilt = PortfolioSession(persistent=True)

    tickers = {str(position.asset.ticker) for position in rebuilt.projection().positions}
    assert ticker.upper() in tickers
    assert rebuilt.projection().total_market_value.amount >= Decimal("24")
    assert rebuilt._allocation_policy is not None
