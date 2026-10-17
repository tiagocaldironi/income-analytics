"""Primary investment classes used for portfolio composition."""

from enum import StrEnum


class AssetClass(StrEnum):
    BRAZILIAN_STOCK = "BRAZILIAN_STOCK"
    BRAZILIAN_ETF = "BRAZILIAN_ETF"
    FII = "FII"
    FIXED_INCOME = "FIXED_INCOME"
    INTERNATIONAL = "INTERNATIONAL"
    INTERNATIONAL_ETF = "INTERNATIONAL_ETF"
    US_REIT = "US_REIT"
    CRYPTO = "CRYPTO"
    CASH = "CASH"
    PENSION = "PENSION"
    REAL_ESTATE = "REAL_ESTATE"
    OTHER = "OTHER"
