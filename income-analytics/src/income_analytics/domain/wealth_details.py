"""Non-listed wealth instruments, modelled separately from the asset master."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class PensionPlanDetails:
    asset_id: UUID
    institution: str
    institution_cnpj: str | None
    plan_name: str
    tax_regime: str
    start_date: date
    reported_balance: Decimal
    reported_balance_date: date
    # Legacy field retained for persisted v1 records.  New callers should use
    # product_type, which is meaningful only for an open pension plan.
    pension_type: str = "OUTRO"
    ownership_origin: str = "PARTICULAR"
    pension_system_type: str = "OPEN"
    product_type: str | None = None
    closed_plan_modality: str | None = None
    sponsor_name: str | None = None
    sponsor_cnpj: str | None = None
    susep_process_number: str | None = None
    cnpb: str | None = None
    participant_balance: Decimal | None = None
    sponsor_balance: Decimal | None = None
    employer_match_enabled: bool | None = None
    employer_match_rate: Decimal | None = None
    match_limit: Decimal | None = None
    match_rule_notes: str | None = None
    vesting_enabled: bool | None = None
    current_vested_percentage: Decimal | None = None
    vesting_rule_notes: str | None = None
    status: str = "ACTIVE"

    def __post_init__(self) -> None:
        if self.ownership_origin not in {"PARTICULAR", "EMPLOYER", "ASSOCIATION"}:
            raise ValueError("ownership_origin is invalid.")
        if self.pension_system_type not in {"OPEN", "CLOSED", "UNKNOWN"}:
            raise ValueError("pension_system_type is invalid.")
        if self.tax_regime not in {
            "UNDEFINED",
            "PROGRESSIVE",
            "REGRESSIVE",
            "DESCONHECIDO",
            "PROGRESSIVO",
            "REGRESSIVO",
        }:
            raise ValueError("tax_regime is invalid.")
        product_type = self.product_type or self.pension_type
        open_products = {"PGBL", "VGBL", "OTHER", "UNKNOWN", "OUTRO"}
        if self.pension_system_type == "OPEN" and product_type not in open_products:
            raise ValueError("product_type is invalid for an open pension plan.")
        if self.pension_system_type == "OPEN" and self.closed_plan_modality is not None:
            raise ValueError("closed_plan_modality is only valid for a closed pension plan.")
        if self.pension_system_type == "CLOSED" and self.closed_plan_modality not in {
            "CD",
            "CV",
            "BD",
            "UNKNOWN",
        }:
            raise ValueError("closed_plan_modality is required for a closed pension plan.")
        if self.pension_system_type == "CLOSED" and self.product_type is not None:
            raise ValueError("product_type is only valid for an open pension plan.")
        if self.pension_system_type == "UNKNOWN" and (
            self.product_type is not None or self.closed_plan_modality is not None
        ):
            raise ValueError(
                "product_type and closed_plan_modality require a known pension system."
            )
        object.__setattr__(
            self, "product_type", product_type if self.pension_system_type == "OPEN" else None
        )
        object.__setattr__(
            self, "pension_type", product_type if self.pension_system_type == "OPEN" else "OUTRO"
        )
        if not self.institution.strip() or not self.plan_name.strip():
            raise ValueError("Pension institution and plan name are required.")
        if self.reported_balance < 0:
            raise ValueError("reported_balance cannot be negative.")
        if self.reported_balance_date < self.start_date:
            raise ValueError("reported_balance_date cannot precede start_date.")
        if self.institution_cnpj:
            object.__setattr__(
                self, "institution_cnpj", _normalize_cnpj(self.institution_cnpj, "institution_cnpj")
            )
        if self.sponsor_cnpj:
            object.__setattr__(
                self, "sponsor_cnpj", _normalize_cnpj(self.sponsor_cnpj, "sponsor_cnpj")
            )
        for field_name in ("participant_balance", "sponsor_balance", "match_limit"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} cannot be negative.")
        if self.participant_balance is not None and self.sponsor_balance is not None:
            if self.participant_balance + self.sponsor_balance != self.reported_balance:
                raise ValueError(
                    "participant_balance plus sponsor_balance must equal reported_balance."
                )
        if self.employer_match_rate is not None and self.employer_match_rate < 0:
            raise ValueError("employer_match_rate cannot be negative.")
        if self.current_vested_percentage is not None and not Decimal(
            "0"
        ) <= self.current_vested_percentage <= Decimal("100"):
            raise ValueError("current_vested_percentage must be between 0 and 100.")
        if self.status not in {"ACTIVE", "INACTIVE", "PORTED", "CLOSED"}:
            raise ValueError("pension status is invalid.")

    @property
    def current_balance(self) -> Decimal:
        return self.reported_balance

    @property
    def balance_date(self) -> date:
        return self.reported_balance_date


@dataclass(frozen=True, slots=True, kw_only=True)
class RealEstateDetails:
    asset_id: UUID
    property_type: str
    description: str
    cep: str
    country: str = "BR"
    ownership_percentage: Decimal = Decimal("100")
    current_manual_value: Decimal
    valuation_date: date
    city: str | None = None
    state: str | None = None
    neighborhood: str | None = None
    usable_area_m2: Decimal | None = None
    bedrooms: int | None = None
    parking_spaces: int | None = None
    acquisition_date: date | None = None
    acquisition_value: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.property_type.strip() or not self.description.strip() or not self.cep.strip():
            raise ValueError("Property type, description and CEP are required.")
        if self.current_manual_value <= 0:
            raise ValueError("current_manual_value must be greater than zero.")
        if self.acquisition_value is not None and self.acquisition_value <= 0:
            raise ValueError("acquisition_value must be greater than zero when provided.")
        if self.acquisition_date and self.acquisition_date > self.valuation_date:
            raise ValueError("acquisition_date cannot be after valuation_date.")
        if not Decimal("0") < self.ownership_percentage <= Decimal("100"):
            raise ValueError("ownership_percentage must be greater than zero and up to 100.")
        postal_code = "".join(character for character in self.cep if character.isalnum())
        if self.country.upper() == "BR" and (len(postal_code) != 8 or not postal_code.isdigit()):
            raise ValueError("cep must contain 8 digits for Brazilian properties.")
        object.__setattr__(self, "cep", postal_code.upper())
        object.__setattr__(self, "country", self.country.strip().upper())

    @property
    def portfolio_value(self) -> Decimal:
        return self.current_manual_value * self.ownership_percentage / Decimal("100")


def _valid_cnpj(value: str) -> bool:
    if len(value) != 14 or value == value[0] * 14:
        return False
    numbers = [int(item) for item in value]
    for size in (12, 13):
        weights = list(range(size - 7, 1, -1)) + list(range(9, 1, -1))
        digit = sum(number * weight for number, weight in zip(numbers[:size], weights)) % 11
        if numbers[size] != (0 if digit < 2 else 11 - digit):
            return False
    return True


def _normalize_cnpj(value: str, field_name: str) -> str:
    normalized = "".join(character for character in value if character.isdigit())
    if not _valid_cnpj(normalized):
        raise ValueError(f"{field_name} must be a valid CNPJ.")
    return normalized
