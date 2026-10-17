from datetime import date
from decimal import Decimal

from income_analytics.application.magic_formula_market_evidence import (
    CotahistPriceEvidence,
    MagicFormulaMarketEvidenceAgent,
    MarketEvidenceStatus,
)
from income_analytics.application.market_data import MarketDataUnavailable


class _Provider:
    def __init__(self, result: CotahistPriceEvidence | Exception) -> None:
        self._result = result

    def price_evidence_on(
        self, symbol: str, requested_reference_date: date
    ) -> CotahistPriceEvidence:
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def test_mkt_evid_returns_auditable_cotahist_bundle() -> None:
    requested = date(2025, 12, 31)
    evidence = CotahistPriceEvidence(
        ticker="WEGE3", requested_reference_date=requested, effective_date=date(2025, 12, 30),
        price=Decimal("48.51"), currency="BRL", source="B3_COTAHIST",
        source_file="COTAHIST_A2025.ZIP", record_reference="COTAHIST_A2025.ZIP|line=1",
        status=MarketEvidenceStatus.VALID,
    )

    result = MagicFormulaMarketEvidenceAgent(_Provider(evidence)).obtain(
        ticker="wege3", requested_reference_date=requested
    )

    assert result == evidence
    assert result.is_valid


def test_mkt_evid_missing_quote_is_explicit_and_never_zero() -> None:
    result = MagicFormulaMarketEvidenceAgent(
        _Provider(MarketDataUnavailable("cotação ausente"))
    ).obtain(ticker="WEGE3", requested_reference_date=date(2025, 12, 31))

    assert result.status is MarketEvidenceStatus.INSUFFICIENT_MARKET_DATA
    assert result.price is None
    assert result.effective_date is None
    assert result.reason == "cotação ausente"


def test_mkt_evid_rejects_provider_record_without_raw_locator() -> None:
    requested = date(2025, 12, 31)
    malformed = CotahistPriceEvidence(
        ticker="WEGE3", requested_reference_date=requested, effective_date=date(2025, 12, 30),
        price=Decimal("48.51"), currency="BRL", source="B3_COTAHIST", source_file=None,
        record_reference=None, status=MarketEvidenceStatus.VALID,
    )

    result = MagicFormulaMarketEvidenceAgent(_Provider(malformed)).obtain(
        ticker="WEGE3", requested_reference_date=requested
    )

    assert result.status is MarketEvidenceStatus.INSUFFICIENT_MARKET_DATA
    assert result.price is None
