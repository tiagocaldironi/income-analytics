from datetime import date
from decimal import Decimal

from income_analytics.application.historical_portfolio_reconstruction import (
    HistoricalPortfolioReconstructionService,
)
from income_analytics.application.portfolio_context import MAIN_PORTFOLIO_ID
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.read_models.portfolio_projection import PortfolioProjection


def _service(session: PortfolioSession) -> HistoricalPortfolioReconstructionService:
    return HistoricalPortfolioReconstructionService(
        events=session.history(),
        market_prices=session._market_prices,
        portfolio_at=lambda as_of: session.projection(as_of=as_of),
        valuation_at=lambda as_of: session.base_currency_valuation(as_of=as_of),
    )


def _buy_petr4(session: PortfolioSession, when: date) -> None:
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=Decimal("10"),
        unit_price=Decimal("10"),
        effective_date=when,
    )


def test_reconstruction_keeps_unvalued_positions_out_of_valued_wealth() -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("200"),
        effective_date=date(2026, 1, 1),
    )
    _buy_petr4(session, date(2026, 1, 1))
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="AAPL",
        asset_class=AssetClass.INTERNATIONAL,
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        effective_date=date(2026, 1, 1),
    )
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("12"), effective_date=date(2026, 1, 2)
    )

    result = _service(session).portfolio_as_of(date(2026, 1, 2))

    assert result.coverage_status == "PARTIAL"
    assert result.valued_wealth == Decimal("120")
    assert result.valued_positions == 1
    assert result.unvalued_positions == 1
    assert result.issues == ("MISSING_HISTORICAL_PRICE",)


def test_reconstruction_never_uses_a_future_quote() -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("100"),
        effective_date=date(2026, 1, 1),
    )
    _buy_petr4(session, date(2026, 1, 1))
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("12"), effective_date=date(2026, 1, 31)
    )

    before_quote = _service(session).portfolio_as_of(date(2026, 1, 30))
    on_quote = _service(session).portfolio_as_of(date(2026, 1, 31))

    assert before_quote.coverage_status == "INSUFFICIENT"
    assert before_quote.valued_wealth is None
    assert on_quote.coverage_status == "COMPLETE"
    assert on_quote.valued_wealth == Decimal("120")


def test_evolution_includes_economic_price_and_event_boundaries() -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    _buy_petr4(session, date(2026, 1, 5))
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("12"), effective_date=date(2026, 1, 10)
    )

    points = _service(session).wealth_series(
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)
    )

    assert [point.as_of_date for point in points] == [
        date(2026, 1, 1),
        date(2026, 1, 5),
        date(2026, 1, 10),
        date(2026, 1, 31),
    ]


def test_reconstruction_reuses_each_point_projection_for_valuation() -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    _buy_petr4(session, date(2026, 1, 5))
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("12"), effective_date=date(2026, 1, 10)
    )
    projection_dates: list[date] = []

    def portfolio_at(as_of: date) -> PortfolioProjection:
        projection_dates.append(as_of)
        return session.projection(as_of=as_of)

    service = HistoricalPortfolioReconstructionService(
        events=session.history(),
        market_prices=session._market_prices,
        portfolio_at=portfolio_at,
        valuation_at=lambda as_of: session.base_currency_valuation(as_of=as_of),
        valuation_for_portfolio=lambda as_of, projection: session.base_currency_valuation(
            as_of=as_of, projection=projection
        ),
    )

    points = service.wealth_series(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))

    assert projection_dates == [point.as_of_date for point in points]


def test_reused_projection_preserves_historical_results() -> None:
    session = PortfolioSession(
        portfolio_id=MAIN_PORTFOLIO_ID,
    )
    _buy_petr4(session, date(2026, 1, 5))
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("12"), effective_date=date(2026, 1, 10)
    )
    legacy = _service(session).wealth_series(
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)
    )
    optimized = HistoricalPortfolioReconstructionService(
        events=session.history(),
        market_prices=session._market_prices,
        portfolio_at=lambda as_of: session.projection(as_of=as_of),
        valuation_at=lambda as_of: session.base_currency_valuation(as_of=as_of),
        valuation_for_portfolio=lambda as_of, projection: session.base_currency_valuation(
            as_of=as_of, projection=projection
        ),
    ).wealth_series(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))

    assert optimized == legacy
