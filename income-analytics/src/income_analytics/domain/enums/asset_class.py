"""Primary investment classes used for portfolio composition."""

from enum import StrEnum


class AssetClass(StrEnum):
    BRAZILIAN_STOCK = "BRAZILIAN_STOCK"
    FII = "FII"
    FIXED_INCOME = "FIXED_INCOME"
    INTERNATIONAL = "INTERNATIONAL"
    CRYPTO = "CRYPTO"
    CASH = "CASH"
    OTHER = "OTHER"
