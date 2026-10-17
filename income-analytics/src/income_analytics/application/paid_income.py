"""Application service for an opt-in paid-income provider."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

from income_analytics.domain.enums.financial_event_type import FinancialEventType


class PaidIncomeIntegrationStatus(StrEnum):
    DISABLED = "DISABLED"
    TOKEN_MISSING = "TOKEN_MISSING"
    CONNECTED = "CONNECTED"
    PLAN_NOT_SUPPORTED = "PLAN_NOT_SUPPORTED"
    AUTH_ERROR = "AUTH_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_ERROR = "PROVIDER_ERROR"


class IncomeType(StrEnum):
    DIVIDEND = "DIVIDEND"
    JCP = "JCP"
    FII_INCOME = "FII_INCOME"
    AMORTIZATION = "AMORTIZATION"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class PaidIncomeEvent:
    asset_identifier: str
    income_type: IncomeType
    amount_per_unit: Decimal
    record_date: date | None
    payment_date: date | None
    approval_date: date | None
    provider: str
    provider_event_id: str | None

    @property
    def fingerprint(self) -> str:
        raw = "|".join(
            (
                self.provider,
                self.asset_identifier.upper(),
                self.income_type,
                str(self.record_date),
                str(self.payment_date),
                str(self.amount_per_unit),
            )
        )
        return sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PaidIncomeProviderResponse:
    status: PaidIncomeIntegrationStatus
    events: tuple[PaidIncomeEvent, ...] = ()
    detail: str | None = None


class PaidIncomeProvider(Protocol):
    def get_paid_income(
        self, ticker: str, start_date: date, end_date: date
    ) -> PaidIncomeProviderResponse: ...


@dataclass(frozen=True, slots=True)
class PaidIncomeSettings:
    enabled: bool = False
    api_token: str | None = None
    last_sync_at: datetime | None = None
    last_result: str | None = None

    @property
    def status(self) -> PaidIncomeIntegrationStatus:
        if not self.enabled:
            return PaidIncomeIntegrationStatus.DISABLED
        return (
            PaidIncomeIntegrationStatus.CONNECTED
            if self.api_token
            else PaidIncomeIntegrationStatus.TOKEN_MISSING
        )


class PaidIncomeSettingsRepository(Protocol):
    def get(self) -> PaidIncomeSettings: ...
    def save(self, settings: PaidIncomeSettings) -> None: ...


class ImportedPaidIncomeRepository(Protocol):
    def find_by_fingerprint(self, fingerprint: str): ...
    def save(self, **kwargs): ...


class PaidIncomeSyncService:
    """Imports only already-paid, historically entitled events."""

    def __init__(self, settings_repository, import_repository) -> None:
        self._settings_repository = settings_repository
        self._import_repository = import_repository

    def sync(self, portfolio, provider: PaidIncomeProvider, *, today: date | None = None):
        settings = self._settings_repository.get()
        today = today or date.today()
        if not settings.enabled:
            return {"status": PaidIncomeIntegrationStatus.DISABLED, "consulted": 0, "imported": 0}
        if not settings.api_token:
            return {
                "status": PaidIncomeIntegrationStatus.TOKEN_MISSING,
                "consulted": 0,
                "imported": 0,
            }
        start = (
            settings.last_sync_at.date()
            if settings.last_sync_at
            else date(today.year - 2, today.month, today.day)
        )
        imported = consulted = found = 0
        final_status = PaidIncomeIntegrationStatus.CONNECTED
        for asset in portfolio._assets.values():
            if asset.asset_class.value not in {"BRAZILIAN_STOCK", "FII"}:
                continue
            consulted += 1
            response = provider.get_paid_income(str(asset.ticker), start, today)
            if response.status is not PaidIncomeIntegrationStatus.CONNECTED:
                final_status = response.status
                continue
            for item in response.events:
                found += 1
                if (
                    item.payment_date is None
                    or item.payment_date > today
                    or item.record_date is None
                ):
                    continue
                existing = self._import_repository.find_by_fingerprint(item.fingerprint)
                if existing:
                    if existing.amount_per_unit != str(item.amount_per_unit):
                        self._import_repository.save(
                            event=item,
                            asset_id=str(asset.id),
                            import_status="REVIEW_REQUIRED",
                            detail="Dados materiais foram retificados.",
                            eligible_quantity=None,
                            calculated_amount=None,
                            financial_event_id=None,
                        )
                    continue
                position = portfolio.project(as_of=item.record_date)
                quantity = next(
                    (p.quantity.value for p in position.positions if p.asset.id == asset.id),
                    Decimal("0"),
                )
                if quantity <= 0:
                    self._import_repository.save(
                        event=item,
                        asset_id=str(asset.id),
                        import_status="NOT_ELIGIBLE",
                        detail=None,
                        eligible_quantity=quantity,
                        calculated_amount=None,
                        financial_event_id=None,
                    )
                    continue
                amount = quantity * item.amount_per_unit
                event_type = {
                    IncomeType.DIVIDEND: FinancialEventType.DIVIDEND,
                    IncomeType.JCP: FinancialEventType.INTEREST_ON_EQUITY,
                    IncomeType.FII_INCOME: FinancialEventType.FII_INCOME,
                }.get(item.income_type)
                if event_type is None:
                    continue
                financial_event = portfolio.register_income(
                    event_type=event_type,
                    asset=asset,
                    amount=amount,
                    effective_date=item.payment_date,
                    description="Importado automaticamente via BRAPI",
                )
                self._import_repository.save(
                    event=item,
                    asset_id=str(asset.id),
                    import_status="IMPORTED",
                    detail=None,
                    eligible_quantity=quantity,
                    calculated_amount=amount,
                    financial_event_id=str(financial_event.id),
                )
                imported += 1
        self._settings_repository.save(
            PaidIncomeSettings(
                settings.enabled, settings.api_token, datetime.now(UTC), final_status
            )
        )
        return {
            "status": final_status,
            "consulted": consulted,
            "found": found,
            "imported": imported,
        }
