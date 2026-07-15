from dataclasses import dataclass

from income_analytics.domain.enums.currency_code import CurrencyCode


@dataclass(frozen=True, slots=True)
class Currency:
    code: CurrencyCode
    name: str
    symbol: str
    decimal_places: int