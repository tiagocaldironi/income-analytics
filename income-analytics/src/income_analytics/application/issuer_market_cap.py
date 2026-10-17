"""Issuer-level market capitalization with explicit class/date lineage."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from income_analytics.application.market_data import MarketPriceObservation


class MarketDataStatus(StrEnum):
    VALID = "VALID"
    INSUFFICIENT_MARKET_DATA = "INSUFFICIENT_MARKET_DATA"
    TEMPORAL_INCONSISTENCY = "TEMPORAL_INCONSISTENCY"
    CORPORATE_ACTION_RISK = "CORPORATE_ACTION_RISK"


class IssuerMarketCapResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    UNIT_UNRESOLVED = "UNIT_UNRESOLVED"
    SECURITY_UNRESOLVED = "SECURITY_UNRESOLVED"
    TEMPORAL_CONFLICT = "TEMPORAL_CONFLICT"
    INSUFFICIENT_MARKET_DATA = "INSUFFICIENT_MARKET_DATA"


@dataclass(frozen=True, slots=True)
class ShareClassCapital:
    issuer_id: str
    security_id: str
    ticker: str
    share_class: str
    shares_outstanding: Decimal
    reference_date: date
    source: str
    source_reference: str = ""
    retrieved_at: datetime | None = None
    status: MarketDataStatus = MarketDataStatus.VALID
    security_source: str = ""
    security_source_reference: str = ""
    validation_evidence_only: bool = False


@dataclass(frozen=True, slots=True)
class NormalizedSecurityPrice:
    security_id: str
    ticker: str
    requested_reference_date: date
    effective_date: date
    price: Decimal
    currency: str
    source: str
    source_reference: str = ""
    retrieved_at: datetime | None = None
    status: MarketDataStatus = MarketDataStatus.VALID


class B3PriceNormalizer:
    """Preserve B3's requested/effective date policy without price fallbacks."""

    def normalize(
        self,
        *,
        security_id: str,
        ticker: str,
        requested_reference_date: date,
        observation: MarketPriceObservation,
        source_reference: str,
        retrieved_at: datetime,
    ) -> NormalizedSecurityPrice:
        if observation.symbol != ticker.upper() or observation.price <= 0:
            raise ValueError("INSUFFICIENT_MARKET_DATA")
        if observation.effective_date > requested_reference_date:
            raise ValueError("TEMPORAL_INCONSISTENCY")
        return NormalizedSecurityPrice(
            security_id=security_id,
            ticker=ticker.upper(),
            requested_reference_date=requested_reference_date,
            effective_date=observation.effective_date,
            price=observation.price,
            currency=observation.currency_code,
            source=observation.source,
            source_reference=source_reference,
            retrieved_at=retrieved_at,
        )


class IssuerMarketCapService:
    def calculate(
        self, capitals: tuple[ShareClassCapital, ...], prices: tuple[NormalizedSecurityPrice, ...]
    ) -> tuple[Decimal, tuple[dict[str, object], ...]]:
        if len({capital.issuer_id for capital in capitals}) > 1:
            raise ValueError("TEMPORAL_INCONSISTENCY")
        if len({capital.security_id for capital in capitals}) != len(capitals):
            raise ValueError("INSUFFICIENT_MARKET_DATA")
        price_by_security = {price.security_id: price for price in prices}
        components = []
        for capital in capitals:
            price = price_by_security.get(capital.security_id)
            if (
                price is None
                or price.price <= 0
                or capital.shares_outstanding <= 0
                or capital.status is not MarketDataStatus.VALID
                or price.status is not MarketDataStatus.VALID
            ):
                raise ValueError("INSUFFICIENT_MARKET_DATA")
            # A market close may be from the immediately preceding trading day
            # (weekend/holiday), but its requested date must be the exact capital
            # reference date.  A source may flag corporate-action risk explicitly.
            if (
                price.requested_reference_date != capital.reference_date
                or price.effective_date > price.requested_reference_date
                or (price.requested_reference_date - price.effective_date).days > 7
            ):
                raise ValueError("TEMPORAL_INCONSISTENCY")
            partial = capital.shares_outstanding * price.price
            components.append(
                {
                    "ticker": capital.ticker,
                    "security_id": capital.security_id,
                    "share_class": capital.share_class,
                    "shares": capital.shares_outstanding,
                    "shares_reference_date": capital.reference_date,
                    "price": price.price,
                    "price_effective_date": price.effective_date,
                    "partial_market_cap": partial,
                    "shares_source": capital.source,
                    "shares_source_reference": capital.source_reference,
                    "security_source": capital.security_source,
                    "security_source_reference": capital.security_source_reference,
                    "validation_evidence_only": capital.validation_evidence_only,
                    "price_source": price.source,
                    "price_source_reference": price.source_reference,
                }
            )
        if not components:
            raise ValueError("INSUFFICIENT_MARKET_DATA")
        return sum((item["partial_market_cap"] for item in components), Decimal("0")), tuple(
            components
        )


@dataclass(frozen=True, slots=True)
class IssuerMarketCapResolution:
    issuer_id: str
    status: IssuerMarketCapResolutionStatus
    market_cap: Decimal | None
    components: tuple[dict[str, object], ...]
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class HistoricalMarketCapCoverage:
    total_eligible_issuers: int
    resolved_market_cap_issuers: int
    unresolved_market_cap_issuers: int
    coverage_percentage: Decimal


class PartialHistoricalMarketCapService:
    """Resolve market cap safely per issuer; never turns partial data into ranking input."""

    def __init__(self, calculator: IssuerMarketCapService | None = None) -> None:
        self._calculator = calculator or IssuerMarketCapService()

    def resolve(
        self,
        *,
        issuer_id: str,
        capitals: tuple[ShareClassCapital, ...],
        prices: tuple[NormalizedSecurityPrice, ...],
        precondition_status: IssuerMarketCapResolutionStatus = (
            IssuerMarketCapResolutionStatus.RESOLVED
        ),
        reason: str | None = None,
    ) -> IssuerMarketCapResolution:
        if precondition_status is not IssuerMarketCapResolutionStatus.RESOLVED:
            return IssuerMarketCapResolution(issuer_id, precondition_status, None, (), reason)
        try:
            market_cap, components = self._calculator.calculate(capitals, prices)
        except ValueError as error:
            code = str(error)
            status = (
                IssuerMarketCapResolutionStatus.TEMPORAL_CONFLICT
                if code == "TEMPORAL_INCONSISTENCY"
                else IssuerMarketCapResolutionStatus.INSUFFICIENT_MARKET_DATA
            )
            return IssuerMarketCapResolution(issuer_id, status, None, (), code)
        return IssuerMarketCapResolution(
            issuer_id, IssuerMarketCapResolutionStatus.RESOLVED, market_cap, components
        )

    @staticmethod
    def coverage(
        resolutions: tuple[IssuerMarketCapResolution, ...],
    ) -> HistoricalMarketCapCoverage:
        total = len(resolutions)
        resolved = sum(
            item.status is IssuerMarketCapResolutionStatus.RESOLVED for item in resolutions
        )
        return HistoricalMarketCapCoverage(
            total_eligible_issuers=total,
            resolved_market_cap_issuers=resolved,
            unresolved_market_cap_issuers=total - resolved,
            coverage_percentage=(
                Decimal("0") if total == 0 else Decimal("100") * Decimal(resolved) / Decimal(total)
            ),
        )
