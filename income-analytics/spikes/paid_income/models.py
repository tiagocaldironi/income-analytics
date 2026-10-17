from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class IncomeType(StrEnum):
    DIVIDEND = "DIVIDEND"
    JCP = "JCP"
    FII_INCOME = "FII_INCOME"
    AMORTIZATION = "AMORTIZATION"
    OTHER = "OTHER"


class QueryResult(StrEnum):
    SUCCESS = "SUCCESS"
    NO_EVENTS = "NO_EVENTS"
    UNSUPPORTED_TICKER = "UNSUPPORTED_TICKER"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    PLAN_LIMITATION = "PLAN_LIMITATION"
    RATE_LIMIT = "RATE_LIMIT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    NETWORK_ERROR = "NETWORK_ERROR"


@dataclass(frozen=True, slots=True)
class PaidIncomeEvent:
    asset_identifier: str
    income_type: IncomeType
    amount_per_unit: Decimal
    record_date: date | None
    payment_date: date
    approval_date: date | None
    provider: str
    provider_event_id: str | None


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    result: QueryResult
    status_code: int | None
    elapsed_ms: int
    events: tuple[PaidIncomeEvent, ...] = ()
    detail: str | None = None
