from decimal import Decimal

from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.capital_flow_type import CapitalFlowType
from income_analytics.domain.enums.financial_event_type import FinancialEventType


def test_unclassified_historical_event_is_explicitly_unknown() -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="TEST",
        quantity=Decimal("1"),
        unit_price=Decimal("10"),
    )
    event = session.history()[-1]

    assert event.capital_flow_type is CapitalFlowType.UNKNOWN


def test_event_reads_persisted_internal_transfer_classification() -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="TEST",
        asset_class=AssetClass.FII,
        quantity=Decimal("1"),
        unit_price=Decimal("10"),
        capital_flow_type=CapitalFlowType.INTERNAL_TRANSFER,
        source_asset_class=AssetClass.BRAZILIAN_STOCK,
    )
    event = session.history()[-1]

    assert event.capital_flow_type is CapitalFlowType.INTERNAL_TRANSFER
