"""Classification of financial assets supported by the domain."""

from enum import StrEnum


class AssetType(StrEnum):
    """Closed vocabulary used to classify a financial asset."""

    STOCK = "STOCK"
    ETF = "ETF"
    FII = "FII"
    TREASURY = "TREASURY"
    CDB = "CDB"
    LCI = "LCI"
    LCA = "LCA"
    CRA = "CRA"
    CRI = "CRI"
    FUND = "FUND"
    CRYPTO = "CRYPTO"
    CURRENCY = "CURRENCY"
    OTHER = "OTHER"
