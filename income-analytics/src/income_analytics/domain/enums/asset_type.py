"""Classification of financial assets supported by the domain."""

from enum import StrEnum


class AssetType(StrEnum):
    """Closed vocabulary used to classify a financial asset."""

    STOCK = "STOCK"
    ETF = "ETF"
    FII = "FII"
    REIT = "REIT"
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
    # Wealth-domain categories. Existing granular values remain supported for migration.
    LISTED_SECURITY = "LISTED_SECURITY"
    FIXED_INCOME = "FIXED_INCOME"
    PENSION = "PENSION"
    REAL_ESTATE = "REAL_ESTATE"
    CASH = "CASH"
    SAVINGS_ACCOUNT = "SAVINGS_ACCOUNT"
