"""Auditable B3 COTAHIST market-price evidence for Magic Formula.

This boundary intentionally keeps an unavailable quote as unavailable.  It
never manufactures a price (including zero) merely to let a later market-cap
calculation continue.
"""

from __future__ import annotations

from datetime import date

from income_analytics.application.market_data import (
    CotahistEvidenceProvider as CotahistEvidenceProvider,
)
from income_analytics.application.market_data import (
    CotahistPriceEvidence as CotahistPriceEvidence,
)
from income_analytics.application.market_data import (
    MarketDataUnavailable,
)
from income_analytics.application.market_data import (
    MarketEvidenceStatus as MarketEvidenceStatus,
)


class MagicFormulaMarketEvidenceAgent:
    """Obtains a COTAHIST evidence bundle without changing issuer state."""

    def __init__(self, provider: CotahistEvidenceProvider) -> None:
        self._provider = provider

    def obtain(self, *, ticker: str, requested_reference_date: date) -> CotahistPriceEvidence:
        normalized_ticker = ticker.strip().upper()
        if not normalized_ticker:
            return self._missing(normalized_ticker, requested_reference_date, "Ticker inválido.")
        try:
            evidence = self._provider.price_evidence_on(normalized_ticker, requested_reference_date)
        except MarketDataUnavailable as error:
            return self._missing(normalized_ticker, requested_reference_date, str(error))

        # A provider is not allowed to claim a valid evidence record without
        # the raw-record locator and a strictly positive close.
        if (
            evidence.status is not MarketEvidenceStatus.VALID
            or evidence.ticker != normalized_ticker
            or evidence.effective_date is None
            or evidence.effective_date > requested_reference_date
            or evidence.price is None
            or evidence.price <= 0
            or not evidence.currency
            or not evidence.source_file
            or not evidence.record_reference
        ):
            return self._missing(
                normalized_ticker,
                requested_reference_date,
                evidence.reason or "Evidência COTAHIST incompleta ou inválida.",
            )
        return evidence

    @staticmethod
    def _missing(ticker: str, requested_reference_date: date, reason: str) -> CotahistPriceEvidence:
        return CotahistPriceEvidence(
            ticker=ticker,
            requested_reference_date=requested_reference_date,
            effective_date=None,
            price=None,
            currency=None,
            source="B3_COTAHIST",
            source_file=None,
            record_reference=None,
            status=MarketEvidenceStatus.INSUFFICIENT_MARKET_DATA,
            reason=reason,
        )
