"""Normalized FX boundary used by portfolio valuation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True, kw_only=True)
class FxRateObservation:
    """One unit of base_currency expressed in quote_currency.

    Example: USD/BRL = 5.42 means one USD is worth 5.42 BRL.
    """

    base_currency: str
    quote_currency: str
    rate: Decimal
    effective_date: date
    source: str


class FxRateUnavailable(Exception):
    pass


class FxRateProvider(Protocol):
    def rate_on(
        self, base_currency: str, quote_currency: str, effective_date: date
    ) -> FxRateObservation: ...
