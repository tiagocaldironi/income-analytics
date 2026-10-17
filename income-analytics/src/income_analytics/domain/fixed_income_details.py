"""Contract data for fixed-income instruments, kept outside the asset master."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from income_analytics.domain.enums.fixed_income import (
    FixedIncomeIndexerType,
    FixedIncomeInstrumentType,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class FixedIncomeDetails:
    """The contractual terms used to value one fixed-income asset."""

    asset_id: UUID
    instrument_type: FixedIncomeInstrumentType
    indexer_type: FixedIncomeIndexerType
    application_date: date
    principal_amount: Decimal
    issuer: str | None = None
    contracted_rate: Decimal | None = None
    percentage_of_indexer: Decimal | None = None
    spread: Decimal | None = None
    maturity_date: date | None = None
    liquidity_type: str | None = None
    tax_exempt: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not isinstance(self.asset_id, UUID):
            raise TypeError("asset_id must be a UUID.")
        if not isinstance(self.instrument_type, FixedIncomeInstrumentType):
            raise TypeError("instrument_type must be a FixedIncomeInstrumentType.")
        if not isinstance(self.indexer_type, FixedIncomeIndexerType):
            raise TypeError("indexer_type must be a FixedIncomeIndexerType.")
        if not isinstance(self.application_date, date):
            raise TypeError("application_date must be a date.")
        if not isinstance(self.principal_amount, Decimal) or self.principal_amount <= 0:
            raise ValueError("principal_amount must be greater than zero.")
        if self.maturity_date is not None and self.maturity_date < self.application_date:
            raise ValueError("maturity_date cannot precede application_date.")
        for name in ("contracted_rate", "percentage_of_indexer", "spread"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, Decimal):
                raise TypeError(f"{name} must be a Decimal when provided.")
        if self.indexer_type is FixedIncomeIndexerType.PREFIXED and self.contracted_rate is None:
            raise ValueError("PREFIXED instruments require contracted_rate.")
        if self.indexer_type is FixedIncomeIndexerType.CDI_PERCENT and (
            self.percentage_of_indexer is None
        ):
            raise ValueError("CDI_PERCENT instruments require percentage_of_indexer.")
        if self.indexer_type in (
            FixedIncomeIndexerType.CDI_PLUS,
            FixedIncomeIndexerType.IPCA_PLUS,
        ) and self.spread is None:
            raise ValueError(f"{self.indexer_type.value} instruments require spread.")
        if not isinstance(self.tax_exempt, bool):
            raise TypeError("tax_exempt must be a bool.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")
