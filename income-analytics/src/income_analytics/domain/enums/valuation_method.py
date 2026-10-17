"""How a wealth asset obtains its current valuation."""

from enum import StrEnum


class ValuationMethod(StrEnum):
    MARKET_PRICE = "MARKET_PRICE"
    CONTRACT_CURVE = "CONTRACT_CURVE"
    REPORTED_BALANCE = "REPORTED_BALANCE"
    MANUAL_ESTIMATE = "MANUAL_ESTIMATE"
    MARK_TO_MARKET = "MARK_TO_MARKET"
    MARKET_MODEL_ESTIMATE = "MARKET_MODEL_ESTIMATE"
