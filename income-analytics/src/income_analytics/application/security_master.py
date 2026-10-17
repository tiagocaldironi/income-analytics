"""Stable issuer/security identity records for auditable market-cap inputs."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class SecurityResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    MISSING = "MISSING"
    TEMPORAL_CONFLICT = "TEMPORAL_CONFLICT"
    UNIT_UNRESOLVED = "UNIT_UNRESOLVED"


@dataclass(frozen=True, slots=True)
class SecurityMaster:
    issuer_id: str
    cvm_code: str
    b3_issuer_id: str
    security_id: str
    ticker: str
    isin: str
    share_class: str
    valid_from: date
    valid_to: date | None
    source: str
    source_reference: str
    status: SecurityResolutionStatus


@dataclass(frozen=True, slots=True)
class B3IssuerRecord:
    cvm_code: str
    b3_issuer_id: str
    cnpj: str
    source_reference: str


class SecurityMasterResolver:
    """Resolve issuer identity only through CVM code plus normalized CNPJ."""

    @staticmethod
    def resolve_issuer(
        *, issuer_id: str, cvm_code: str, cvm_cnpj: str, b3_record: B3IssuerRecord
    ) -> SecurityResolutionStatus:
        if b3_record.cvm_code != cvm_code:
            return SecurityResolutionStatus.AMBIGUOUS
        if SecurityMasterResolver._digits(b3_record.cnpj) != SecurityMasterResolver._digits(
            cvm_cnpj
        ):
            return SecurityResolutionStatus.AMBIGUOUS
        if not b3_record.b3_issuer_id:
            return SecurityResolutionStatus.MISSING
        return SecurityResolutionStatus.RESOLVED

    @staticmethod
    def _digits(value: str) -> str:
        return "".join(character for character in value if character.isdigit())
