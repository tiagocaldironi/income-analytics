from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from income_analytics.application.issuer_market_cap import (
    B3PriceNormalizer,
    IssuerMarketCapResolutionStatus,
    IssuerMarketCapService,
    NormalizedSecurityPrice,
    PartialHistoricalMarketCapService,
    ShareClassCapital,
)
from income_analytics.application.market_data import MarketPriceObservation


def test_market_cap_sums_on_and_pn_without_using_one_class_as_proxy() -> None:
    capital = (
        ShareClassCapital(
            "issuer", "security-on", "TEST3", "ON", Decimal("100"), date(2025, 12, 31), "CVM"
        ),
        ShareClassCapital(
            "issuer", "security-pn", "TEST4", "PN", Decimal("50"), date(2025, 12, 31), "CVM"
        ),
    )
    prices = (
        NormalizedSecurityPrice(
            "security-on",
            "TEST3",
            date(2025, 12, 31),
            date(2025, 12, 30),
            Decimal("10"),
            "BRL",
            "B3",
        ),
        NormalizedSecurityPrice(
            "security-pn",
            "TEST4",
            date(2025, 12, 31),
            date(2025, 12, 30),
            Decimal("8"),
            "BRL",
            "B3",
        ),
    )
    # Capital reference precedes the price by one day, allowed by the B3 close policy.
    capital = tuple(
        item.__class__(
            item.issuer_id,
            item.security_id,
            item.ticker,
            item.share_class,
            item.shares_outstanding,
            date(2025, 12, 31),
            item.source,
        )
        for item in capital
    )
    market_cap, components = IssuerMarketCapService().calculate(capital, prices)
    assert market_cap == Decimal("1400")
    assert len(components) == 2


def test_market_cap_rejects_missing_security_price() -> None:
    capital = (
        ShareClassCapital(
            "issuer", "security-on", "TEST3", "ON", Decimal("100"), date(2025, 1, 1), "CVM"
        ),
    )
    with pytest.raises(ValueError, match="INSUFFICIENT_MARKET_DATA"):
        IssuerMarketCapService().calculate(capital, ())


def test_market_cap_rejects_price_requested_for_a_different_reference_date() -> None:
    capital = (
        ShareClassCapital(
            "issuer", "security-on", "TEST3", "ON", Decimal("100"), date(2025, 1, 5), "CVM"
        ),
    )
    prices = (
        NormalizedSecurityPrice(
            "security-on", "TEST3", date(2025, 1, 4), date(2025, 1, 3), Decimal("10"), "BRL", "B3"
        ),
    )
    with pytest.raises(ValueError, match="TEMPORAL_INCONSISTENCY"):
        IssuerMarketCapService().calculate(capital, prices)


def test_b3_price_preserves_previous_trading_day_for_weekend_request() -> None:
    price = B3PriceNormalizer().normalize(
        security_id="security-on",
        ticker="TEST3",
        requested_reference_date=date(2025, 1, 5),
        observation=MarketPriceObservation(
            symbol="TEST3",
            price=Decimal("10"),
            currency_code="BRL",
            effective_date=date(2025, 1, 3),
            source="b3_cotahist",
        ),
        source_reference="COTAHIST_A2025.ZIP",
        retrieved_at=datetime.now(UTC),
    )
    assert price.requested_reference_date == date(2025, 1, 5)
    assert price.effective_date == date(2025, 1, 3)


def test_petrobras_2025_golden_case_sums_real_on_and_pn_inputs() -> None:
    resolver = PartialHistoricalMarketCapService()
    capitals = (
        ShareClassCapital(
            "petrobras",
            "petr3",
            "PETR3",
            "ON",
            Decimal("7442231382"),
            date(2025, 12, 31),
            "CVM_DFP",
            "dfp_cia_aberta_composicao_capital_2025.csv",
            security_source="CVM_FCA",
        ),
        ShareClassCapital(
            "petrobras",
            "petr4",
            "PETR4",
            "PN",
            Decimal("5446501379"),
            date(2025, 12, 31),
            "CVM_DFP",
            "dfp_cia_aberta_composicao_capital_2025.csv",
            security_source="CVM_FCA",
        ),
    )
    prices = (
        NormalizedSecurityPrice(
            "petr3",
            "PETR3",
            date(2025, 12, 31),
            date(2025, 12, 30),
            Decimal("32.57"),
            "BRL",
            "b3_cotahist",
            "COTAHIST_A2025.ZIP",
        ),
        NormalizedSecurityPrice(
            "petr4",
            "PETR4",
            date(2025, 12, 31),
            date(2025, 12, 30),
            Decimal("30.82"),
            "BRL",
            "b3_cotahist",
            "COTAHIST_A2025.ZIP",
        ),
    )
    resolution = resolver.resolve(issuer_id="petrobras", capitals=capitals, prices=prices)
    assert resolution.status is IssuerMarketCapResolutionStatus.RESOLVED
    assert resolution.market_cap == Decimal("410254648612.52")
    components = resolution.components
    assert [item["ticker"] for item in components] == ["PETR3", "PETR4"]
    assert {item["shares_source"] for item in components} == {"CVM_DFP"}
    assert {item["security_source"] for item in components} == {"CVM_FCA"}
    assert {item["price_source"] for item in components} == {"b3_cotahist"}
    assert not any(item["validation_evidence_only"] for item in components)


def test_partial_coverage_keeps_unresolved_issuers_out_of_market_cap() -> None:
    service = PartialHistoricalMarketCapService()
    resolved = service.resolve(
        issuer_id="resolved",
        capitals=(
            ShareClassCapital(
                "resolved", "on", "ON3", "ON", Decimal("10"), date(2025, 12, 31), "CVM"
            ),
        ),
        prices=(
            NormalizedSecurityPrice(
                "on", "ON3", date(2025, 12, 31), date(2025, 12, 30), Decimal("5"), "BRL", "B3"
            ),
        ),
    )
    unresolved = service.resolve(
        issuer_id="vale",
        capitals=(),
        prices=(),
        precondition_status=IssuerMarketCapResolutionStatus.UNIT_UNRESOLVED,
        reason="quantity_unit_not_proven",
    )
    coverage = service.coverage((resolved, unresolved))

    assert unresolved.market_cap is None
    assert unresolved.status is IssuerMarketCapResolutionStatus.UNIT_UNRESOLVED
    assert coverage.total_eligible_issuers == 2
    assert coverage.resolved_market_cap_issuers == 1
    assert coverage.unresolved_market_cap_issuers == 1
    assert coverage.coverage_percentage == Decimal("50")
