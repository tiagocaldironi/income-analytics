from __future__ import annotations

from datetime import date
from typing import Protocol

from income_analytics.domain.pension_market_data import PensionFundQuota, PensionInvestmentVehicle


class PensionMarketDataUnavailable(Exception):
    pass


class PensionMarketDataProvider(Protocol):
    def resolve_vehicle(self, cnpj: str) -> PensionInvestmentVehicle: ...

    def quota_history(
        self, vehicle: PensionInvestmentVehicle, start_date: date, end_date: date
    ) -> tuple[PensionFundQuota, ...]: ...
