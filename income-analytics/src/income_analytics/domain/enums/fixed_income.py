"""Fixed-income contract vocabularies."""

from enum import StrEnum


class FixedIncomeInstrumentType(StrEnum):
    CDB = "CDB"
    RDB = "RDB"
    LCI = "LCI"
    LCA = "LCA"
    TESOURO_DIRETO = "TESOURO_DIRETO"
    DEBENTURE = "DEBENTURE"
    SAVINGS_ACCOUNT = "SAVINGS_ACCOUNT"
    OTHER = "OTHER"


class FixedIncomeIndexerType(StrEnum):
    PREFIXED = "PREFIXED"
    CDI_PERCENT = "CDI_PERCENT"
    CDI_PLUS = "CDI_PLUS"
    IPCA_PLUS = "IPCA_PLUS"
    SELIC = "SELIC"
    SAVINGS_RULE = "SAVINGS_RULE"
    OTHER = "OTHER"
