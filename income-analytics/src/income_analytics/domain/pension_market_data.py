"""Market-data records for open pension investment vehicles."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4


def _cnpj(value: str) -> str:
    normalized = "".join(character for character in value if character.isdigit())
    if len(normalized) != 14:
        raise ValueError("vehicle_cnpj must contain 14 digits.")
    return normalized


@dataclass(frozen=True, slots=True, kw_only=True)
class PensionInvestmentVehicle:
    pension_asset_id: UUID
    vehicle_name: str
    vehicle_cnpj: str
    vehicle_type: str = "FUND_CLASS"
    source: str = "USER_PROVIDED"
    valid_from: date | None = None
    valid_to: date | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.vehicle_type not in {"FIE", "FUND_CLASS", "UNKNOWN"}:
            raise ValueError("vehicle_type is invalid.")
        if self.source not in {"USER_PROVIDED", "MANUAL_VALIDATION", "SYSTEM_RESOLVED"}:
            raise ValueError("vehicle source is invalid.")
        if not self.vehicle_name.strip():
            raise ValueError("vehicle_name is required.")
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("vehicle valid_to cannot precede valid_from.")
        object.__setattr__(self, "vehicle_cnpj", _cnpj(self.vehicle_cnpj))


@dataclass(frozen=True, slots=True, kw_only=True)
class PensionFundQuota:
    vehicle_id: UUID
    reference_date: date
    quota: Decimal
    source: str = "CVM"
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.quota <= 0:
            raise ValueError("quota must be greater than zero.")
