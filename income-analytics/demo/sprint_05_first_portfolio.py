"""
Sprint 05 demo.

Creates a simple portfolio projection from a Financial Ledger.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from income_analytics.domain.aggregates.financial_ledger import FinancialLedger
from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.projectors.portfolio_projector import (
    PortfolioProjector,
)
from income_analytics.domain.value_objects.money import Money
from income_analytics.domain.value_objects.quantity import Quantity
from income_analytics.domain.value_objects.ticker import Ticker


def main() -> None:

    account_id = uuid4()
    asset = Asset(
        ticker=Ticker("PETR4"),
        name="Petrobras PN",
        asset_type=AssetType.STOCK,
        currency=object(),  # type: ignore[arg-type]
        institution=object(),  # type: ignore[arg-type]
    )

    ledger = FinancialLedger.create(account_id)

    ledger.append(
        FinancialEvent(
            account_id=account_id,
            asset=asset,
            event_type=FinancialEventType.BUY,
            occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
            quantity=Quantity(Decimal("100")),
            unit_price=Money(Decimal("30")),
            total_amount=Money(Decimal("3000")),
        )
    )

    portfolio = PortfolioProjector.project(
        ledger.replay(),
    )

    print()
    print("=" * 60)
    print("Income Analytics")
    print("=" * 60)
    print()

    print("Portfolio")
    print("-" * 60)

    for position in portfolio.positions:
        print(f"Ticker.........: {position.asset.ticker}")
        print(f"Quantity.......: {position.quantity}")
        print(f"Average Cost...: {position.average_cost}")
        print(f"Invested.......: {position.invested_amount}")
        print("-" * 60)

    print(f"Positions......: {portfolio.position_count}")
    print(f"Total Invested.: {portfolio.total_invested}")

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
