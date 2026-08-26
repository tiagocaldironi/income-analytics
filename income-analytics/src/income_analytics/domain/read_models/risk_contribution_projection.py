"""Risk attribution by asset, based on covariance of observed returns."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetRiskContribution:
    ticker: str
    weight: Decimal
    volatility: Decimal | None
    contribution: Decimal | None
    contribution_share: Decimal | None


@dataclass(frozen=True, slots=True, kw_only=True)
class RiskContributionProjection:
    assets: tuple[AssetRiskContribution, ...]
    portfolio_volatility: Decimal | None
    risk_coverage: Decimal
    covariance: dict[str, dict[str, Decimal]]
    correlation: dict[str, dict[str, Decimal]]
