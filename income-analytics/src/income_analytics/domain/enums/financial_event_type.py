from __future__ import annotations

from enum import Enum


class FinancialEventType(str, Enum):
    """
    Canonical financial event types supported by Income Analytics.
    """

    BUY = "BUY"
    SELL = "SELL"

    DIVIDEND = "DIVIDEND"
    INTEREST_ON_EQUITY = "INTEREST_ON_EQUITY"
    FII_INCOME = "FII_INCOME"

    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"

    SPLIT = "SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    BONUS_SHARE = "BONUS_SHARE"
    SUBSCRIPTION = "SUBSCRIPTION"

    APPLICATION = "APPLICATION"
    REDEMPTION = "REDEMPTION"
    FIXED_INCOME_INTEREST = "FIXED_INCOME_INTEREST"

    BROKERAGE_FEE = "BROKERAGE_FEE"
    TAX = "TAX"

    FX_EXCHANGE = "FX_EXCHANGE"

    STAKING_REWARD = "STAKING_REWARD"
