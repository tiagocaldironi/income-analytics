from typing import Protocol

from income_analytics.application.fx_data import FxRateObservation


class FxRateRepository(Protocol):
    def save(self, observation: FxRateObservation) -> None: ...

    def latest_on_or_before(
        self, base_currency: str, quote_currency: str, effective_date: object
    ) -> FxRateObservation | None: ...
