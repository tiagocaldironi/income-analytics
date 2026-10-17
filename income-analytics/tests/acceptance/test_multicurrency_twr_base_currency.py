from datetime import date
from decimal import Decimal

from income_analytics.application.fx_data import FxRateObservation
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.projectors.performance_projector import PerformanceProjector


def test_usd_position_twr_includes_fx_return_in_brl() -> None:
    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="IVV",
        asset_class=AssetClass.INTERNATIONAL_ETF,
        country="US",
        currency_code="USD",
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        effective_date=date(2026, 1, 1),
    )
    session.update_market_price(
        ticker="IVV", current_price=Decimal("100"), effective_date=date(2026, 1, 2)
    )
    session.update_market_price(
        ticker="IVV", current_price=Decimal("100"), effective_date=date(2026, 1, 3)
    )
    rates = (
        FxRateObservation(
            base_currency="USD",
            quote_currency="BRL",
            rate=Decimal("5"),
            effective_date=date(2026, 1, 1),
            source="test",
        ),
        FxRateObservation(
            base_currency="USD",
            quote_currency="BRL",
            rate=Decimal("5"),
            effective_date=date(2026, 1, 2),
            source="test",
        ),
        FxRateObservation(
            base_currency="USD",
            quote_currency="BRL",
            rate=Decimal("5.5"),
            effective_date=date(2026, 1, 3),
            source="test",
        ),
    )

    result = PerformanceProjector.project(
        session.history(),
        session._market_prices,
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 3),
        fx_rates=rates,
    )

    assert result.twr == Decimal("0.1")


def test_future_fx_is_not_used_for_valuation() -> None:
    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="IVV",
        asset_class=AssetClass.INTERNATIONAL_ETF,
        country="US",
        currency_code="USD",
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        effective_date=date(2026, 1, 1),
    )
    session.update_market_price(
        ticker="IVV", current_price=Decimal("100"), effective_date=date(2026, 1, 2)
    )
    result = PerformanceProjector.project(
        session.history(),
        session._market_prices,
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 2),
        fx_rates=(
            FxRateObservation(
                base_currency="USD",
                quote_currency="BRL",
                rate=Decimal("5"),
                effective_date=date(2026, 1, 3),
                source="test",
            ),
        ),
    )
    assert result.twr is None
    assert result.performance_status == "INSUFFICIENT_DATA"


def test_fx_older_than_five_calendar_days_is_not_eligible() -> None:
    session = PortfolioSession()
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="IVV",
        asset_class=AssetClass.INTERNATIONAL_ETF,
        country="US",
        currency_code="USD",
        quantity=Decimal("1"),
        unit_price=Decimal("100"),
        effective_date=date(2026, 1, 1),
    )
    session.update_market_price(
        ticker="IVV", current_price=Decimal("100"), effective_date=date(2026, 1, 10)
    )
    result = PerformanceProjector.project(
        session.history(),
        session._market_prices,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 1, 10),
        fx_rates=(
            FxRateObservation(
                base_currency="USD",
                quote_currency="BRL",
                rate=Decimal("5"),
                effective_date=date(2026, 1, 4),
                source="test",
            ),
        ),
    )
    assert result.twr is None
    assert result.performance_status == "INSUFFICIENT_DATA"
