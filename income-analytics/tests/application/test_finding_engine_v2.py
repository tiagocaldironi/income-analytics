from datetime import date, timedelta
from decimal import Decimal

import pytest

from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.enums.financial_event_type import FinancialEventType
from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)
from income_analytics.domain.projectors.portfolio_diagnostic_engine import PortfolioDiagnosticEngine

D = Decimal
TODAY = date(2026, 9, 23)
BEFORE = TODAY - timedelta(days=90)


def portfolio(
    previous: str = "75", current: str = "82", us_currency: str = "BRL"
) -> PortfolioSession:
    session = PortfolioSession()
    for ticker, country, asset_class in [
        ("BRTEST", "BR", AssetClass.BRAZILIAN_STOCK),
        ("USTEST", "US", AssetClass.INTERNATIONAL),
    ]:
        session.register_asset(
            ticker=ticker,
            name=ticker,
            country=country,
            currency_code=us_currency if country == "US" else "BRL",
            asset_class=asset_class,
        )
        session.register_trade(
            event_type=FinancialEventType.BUY,
            ticker=ticker,
            asset_class=asset_class,
            quantity=D("1"),
            unit_price=D("50"),
            effective_date=BEFORE - timedelta(days=1),
        )
        for day, value in [(BEFORE, D(previous)), (TODAY, D(current))]:
            session.update_market_price(
                ticker=ticker,
                current_price=value if country == "BR" else 100 - value,
                effective_date=day,
            )
    session.set_allocation_policy(
        AllocationPolicy(
            targets={AssetClass.BRAZILIAN_STOCK: D(".5"), AssetClass.INTERNATIONAL: D(".5")}
        )
    )
    return session


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        ("68", "76", "NEW"),
        ("76", "82", "WORSENING"),
        ("90", "82", "IMPROVING"),
        ("82", "82.5", "PERSISTENT"),
    ],
)
def test_economic_country_trajectory(previous, current, expected):
    session = portfolio(previous, current)
    finding = next(
        f for f in session.intelligence(as_of=TODAY).findings if f.code == "COUNTRY_CONCENTRATION"
    )
    assert finding.trajectory == expected
    assert finding.comparison_as_of == BEFORE
    assert finding.current_value == D(current) / 100
    assert finding.comparison_value == D(previous) / 100
    assert finding.change == (D(current) - D(previous)) / 100
    assert finding.change_pp == D(current) - D(previous)
    assert finding.subject == {"dimension": "COUNTRY", "key": "BR", "label": "Brasil"}
    assert finding.reference["type"] == "INCOME_TECHNICAL_THRESHOLD"
    assert finding.should_surface
    assert not finding.causes


def test_drift_reconciles_and_is_idempotent():
    session = portfolio()
    first = session.intelligence(as_of=TODAY)
    assert first == session.intelligence(as_of=TODAY)
    drift = next(f for f in first.findings if f.code == "PORTFOLIO_DRIFT")
    assert drift.current_value == D(".32")
    assert drift.comparison_value == D(".25")
    assert sum(abs(row["deviation_pp"]) for row in drift.decomposition) / 200 == drift.current_value
    assert drift.reference["type"] == "INCOME_TECHNICAL_THRESHOLD"
    assert drift.reference["policy"]["type"] == "USER_ALLOCATION_POLICY"
    assert drift.category == "STRATEGY"
    assert drift.materiality == "HIGH"
    assert not any(f.evidence.get("key") == "NOT_APPLICABLE" for f in first.findings)


def test_missing_history_is_unknown_without_future_price_fallback():
    session = portfolio()
    session._market_prices = [p for p in session._market_prices if p.effective_date == TODAY]
    for finding in session.intelligence(as_of=TODAY).findings:
        assert finding.trajectory == "UNKNOWN"
        assert finding.comparison_value is None
        assert finding.change_pp is None
        assert "INSUFFICIENT_COMPARISON_VALUATION" in finding.data_quality["issues"]


def test_resolved_supported_in_domain():
    assert PortfolioDiagnosticEngine.trajectory(D(".68"), D(".82"), D(".70")) == "RESOLVED"


def test_risk_coverage_is_series_presence_not_covariance():
    session = portfolio()
    session.register_fixed_income_asset(
        ticker="CDB",
        name="CDB",
        instrument_type=FixedIncomeInstrumentType.CDB,
        indexer_type=FixedIncomeIndexerType.PREFIXED,
        application_date=BEFORE,
        principal_amount=D("100"),
        contracted_rate=D("0"),
    )
    finding = next(
        f
        for f in session.intelligence(as_of=TODAY).findings
        if f.code == "INCOMPLETE_RISK_COVERAGE"
    )
    assert finding.current_value == D(".5")
    assert finding.reference["does_not_guarantee_covariance"]
    assert finding.category == "DATA_QUALITY"
    assert finding.trajectory == "UNKNOWN"
    assert finding.structured_evidence[0]["unit"] == "PERCENTAGE"


def test_fx_is_economic_and_future_fx_cannot_fill_history(monkeypatch):
    from income_analytics.application.base_currency_valuation import BaseCurrencyValuationProjector
    from income_analytics.application.fx_data import FxRateObservation

    session = portfolio(previous="95", current="95", us_currency="USD")
    rates = tuple(
        FxRateObservation(
            base_currency="USD",
            quote_currency="BRL",
            rate=D(rate),
            effective_date=day,
            source="TEST",
        )
        for day, rate in [(TODAY, "5"), (TODAY + timedelta(days=1), "100")]
    )
    monkeypatch.setattr(
        PortfolioSession,
        "base_currency_valuation",
        lambda self, *, as_of=None: BaseCurrencyValuationProjector.project(
            self.projection(as_of=as_of), base_currency="BRL", fx_rates=rates, as_of=as_of
        ),
    )
    finding = next(
        f for f in session.intelligence(as_of=TODAY).findings if f.code == "COUNTRY_CONCENTRATION"
    )
    assert finding.current_value == D("95") / D("120")
    assert finding.comparison_value is None
    assert finding.trajectory == "UNKNOWN"
    assert not finding.data_quality["comparison_valuation_complete"]


def test_missing_current_fx_suppresses_financial_assertions():
    findings = portfolio(us_currency="USD").intelligence(as_of=TODAY).findings
    assert all(not f.should_surface for f in findings if f.category != "DATA_QUALITY")
    assert any(f.code == "INCOMPLETE_VALUATION" for f in findings)


def test_no_undated_asset_price_fallback():
    from income_analytics.domain.value_objects.money import Money

    session = portfolio()
    session._market_prices = []
    for asset in session._assets.values():
        asset.current_price = Money(D("500"))
    assert session._finding_allocation(BEFORE).valuation_coverage == 0


def test_future_events_and_quotes_do_not_change_past_findings():
    session = portfolio()
    expected = session.intelligence(as_of=BEFORE)
    session.register_trade(
        event_type=FinancialEventType.BUY,
        ticker="BRTEST",
        asset_class=AssetClass.BRAZILIAN_STOCK,
        quantity=D("100"),
        unit_price=D("1000"),
        effective_date=TODAY,
    )
    session.update_market_price(ticker="BRTEST", current_price=D("1000"), effective_date=TODAY)
    assert session.intelligence(as_of=BEFORE) == expected


def test_small_breach_has_deterministic_low_materiality_and_is_not_surfaced():
    finding = next(
        f
        for f in portfolio("70", "70.05").intelligence(as_of=TODAY).findings
        if f.code == "COUNTRY_CONCENTRATION"
    )
    assert finding.materiality == "LOW"
    assert finding.materiality_reasons == ("REFERENCE_BREACH",)
    assert not finding.should_surface


def test_api_serializes_full_v2_contract_and_percentage_fraction(monkeypatch):
    from pydantic import TypeAdapter

    from income_analytics.api.routers import dashboard

    monkeypatch.setattr(dashboard, "session", portfolio())
    result = TypeAdapter(dict[str, object]).dump_python(
        dashboard.get_portfolio_intelligence(as_of=TODAY), mode="json"
    )
    finding = next(f for f in result["findings"] if f["code"] == "COUNTRY_CONCENTRATION")
    required = {
        "logical_key",
        "category",
        "subject",
        "current_value",
        "reference",
        "comparison_value",
        "change",
        "change_pp",
        "trajectory",
        "materiality",
        "materiality_reasons",
        "should_surface",
        "structured_evidence",
        "causes",
        "data_quality",
        "as_of",
        "comparison_as_of",
    }
    assert required <= finding.keys()
    assert D(finding["current_value"]) == D(".82")
    assert f"{D(finding['current_value']) * 100:.2f}%" == "82.00%"
    assert D(finding["change_pp"]) == 7
    assert finding["comparison_as_of"] == BEFORE.isoformat()
    assert finding["causes"] == []


def test_existing_disproportionate_risk_rule_retains_its_metric_and_reference():
    from income_analytics.domain.projectors.diversification_projector import (
        DiversificationProjector,
    )
    from income_analytics.domain.read_models.risk_contribution_projection import (
        AssetRiskContribution,
        RiskContributionProjection,
    )

    allocation = portfolio()._finding_allocation(TODAY)
    risk = RiskContributionProjection(
        assets=(
            AssetRiskContribution(
                ticker="USTEST",
                weight=D(".18"),
                volatility=D(".2"),
                contribution=D(".1"),
                contribution_share=D(".5"),
            ),
        ),
        portfolio_volatility=D(".2"),
        risk_coverage=D("1"),
        covariance={},
        correlation={},
    )
    result = PortfolioDiagnosticEngine.analyze(
        allocation=allocation,
        diversification=DiversificationProjector.project(allocation),
        risk=risk,
        as_of=TODAY,
    )
    finding = next(f for f in result.findings if f.code == "DISPROPORTIONATE_RISK_CONTRIBUTION")
    assert finding.category == "RISK"
    assert finding.current_value == D(".5")
    assert finding.reference["value"] == D(".36")
    assert finding.should_surface
