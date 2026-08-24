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
from income_analytics.domain.entities.currency import Currency
from income_analytics.domain.entities.financial_event import FinancialEvent
from income_analytics.domain.entities.institution import Institution
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
        currency=Currency(
            code="BRL",
            name="Real brasileiro",
            symbol="R$",
            decimal_places=2,
        ),
        institution=Institution(name="Petrobras", country="BR"),
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
        )
    )

    ledger.append(
        FinancialEvent(
            account_id=account_id,
            asset=asset,
            event_type=FinancialEventType.BUY,
            occurred_at=datetime(2026, 1, 11, tzinfo=UTC),
            quantity=Quantity(Decimal("100")),
            unit_price=Money(Decimal("40")),
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
        print(f"Average Price..: {position.average_price}")
        print(f"Total Cost.....: {position.cost}")
        print("-" * 60)

    print(f"Positions......: {portfolio.position_count}")
    print(f"Total Cost.....: {portfolio.total_cost}")

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
