from __future__ import annotations

from datetime import date
from decimal import Decimal

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.benchmark_rate import BenchmarkRate
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.projectors.risk_projector import RiskProjector
from income_analytics.domain.read_models.risk_projection import PortfolioReturn


def test_risk_series_neutralizes_contribution_and_calculates_drawdown() -> None:
    session = PortfolioSession()
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("10000"),
        effective_date=date(2026, 1, 1),
    )
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="PETR4",
        quantity=Decimal("100"),
        unit_price=Decimal("100"),
        effective_date=date(2026, 1, 2),
    )
    for when, price in ((date(2026, 1, 2), "100"), (date(2026, 1, 3), "110")):
        session.update_market_price(
            ticker="PETR4", current_price=Decimal(price), effective_date=when
        )
    session.register_external_flow(
        event_type=FinancialEventType.DEPOSIT,
        amount=Decimal("10000"),
        effective_date=date(2026, 1, 4),
    )
    session.update_market_price(
        ticker="PETR4", current_price=Decimal("99"), effective_date=date(2026, 1, 5)
    )

    risk = session.risk(start_date=date(2026, 1, 1), end_date=date(2026, 1, 5))

    assert risk.frequency == "DAILY_OBSERVATIONS"
    assert risk.returns[2].return_percentage == Decimal("0")
    assert risk.maximum_drawdown == Decimal("-0.0523809523809523809523809527")
    assert risk.peak_date == date(2026, 1, 3)
    assert risk.trough_date == date(2026, 1, 5)
    assert risk.annualized_volatility is not None and risk.annualized_volatility >= 0


def test_sample_volatility_and_drawdown_recovery_are_deterministic() -> None:
    volatility = RiskProjector._sample_standard_deviation(
        (Decimal("0.01"), Decimal("-0.01"), Decimal("0.01"), Decimal("-0.01"))
    )

    assert volatility == Decimal("0.011547005383792516")


def test_sharpe_can_be_positive_or_negative_against_aligned_cdi() -> None:
    dates = (date(2026, 1, 2), date(2026, 1, 3))
    cdi = tuple(
        BenchmarkRate(name="CDI", effective_date=when, return_percentage=Decimal("0.001"))
        for when in dates
    )
    volatility = Decimal("0.007071067811865475")
    positive, _ = RiskProjector._sharpe(
        tuple(
            PortfolioReturn(effective_date=when, return_percentage=value)
            for when, value in zip(dates, (Decimal("0.02"), Decimal("0.01")), strict=True)
        ),
        cdi,
        volatility,
    )
    negative, _ = RiskProjector._sharpe(
        tuple(
            PortfolioReturn(effective_date=when, return_percentage=value)
            for when, value in zip(dates, (Decimal("0"), Decimal("-0.01")), strict=True)
        ),
        cdi,
        volatility,
    )

    assert positive is not None and positive > 0
    assert negative is not None and negative < 0
