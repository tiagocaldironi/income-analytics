"""Compute covariance-based marginal and component risk attribution."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from math import sqrt

from income_analytics.domain.read_models.allocation_projection import AllocationProjection
from income_analytics.domain.read_models.risk_contribution_projection import (
    AssetRiskContribution,
    RiskContributionProjection,
)


class RiskContributionProjector:
    @classmethod
    def project(
        cls,
        allocation: AllocationProjection,
        prices: dict[str, dict[date, Decimal]],
    ) -> RiskContributionProjection:
        weighted = [item for item in allocation.assets if item.portfolio_weight is not None]
        eligible = [item for item in weighted if str(item.position.asset.ticker) in prices]
        coverage = sum((item.portfolio_weight or Decimal("0") for item in eligible), Decimal("0"))
        if len(eligible) < 2:
            return cls._unavailable(coverage)
        common_dates = set.intersection(
            *(set(prices[str(item.position.asset.ticker)]) for item in eligible)
        )
        if len(common_dates) < 3:
            return cls._unavailable(coverage)
        tickers = tuple(str(item.position.asset.ticker) for item in eligible)
        returns = {
            ticker: cls._returns(prices[ticker], tuple(sorted(common_dates))) for ticker in tickers
        }
        covariance = {
            left: {right: cls._covariance(returns[left], returns[right]) for right in tickers}
            for left in tickers
        }
        correlation = {
            left: {
                right: cls._correlation(
                    covariance[left][right], covariance[left][left], covariance[right][right]
                )
                for right in tickers
            }
            for left in tickers
        }
        weights = {
            str(item.position.asset.ticker): item.portfolio_weight or Decimal("0")
            for item in eligible
        }
        variance = sum(
            (
                weights[left] * covariance[left][right] * weights[right]
                for left in tickers
                for right in tickers
            ),
            Decimal("0"),
        )
        volatility = Decimal(str(sqrt(float(variance)))) if variance > 0 else None
        contributions = {
            ticker: cls._contribution(ticker, tickers, weights, covariance, volatility)
            for ticker in tickers
        }
        assets: tuple[AssetRiskContribution, ...] = tuple(
            sorted(
                (
                    AssetRiskContribution(
                        ticker=ticker,
                        weight=weights[ticker],
                        volatility=Decimal(str(sqrt(float(covariance[ticker][ticker])))),
                        contribution=contributions[ticker],
                        contribution_share=cls._share(contributions[ticker], volatility),
                    )
                    for ticker in tickers
                ),
                key=lambda item: (item.contribution or Decimal("0"), item.ticker),
                reverse=True,
            )
        )
        return RiskContributionProjection(
            assets=assets,
            portfolio_volatility=volatility,
            risk_coverage=coverage,
            covariance=covariance,
            correlation=correlation,
        )

    @staticmethod
    def _share(contribution: Decimal | None, volatility: Decimal | None) -> Decimal | None:
        if contribution is None or volatility is None:
            return None
        return contribution / volatility

    @staticmethod
    def _returns(values: dict[date, Decimal], dates: tuple[date, ...]) -> tuple[Decimal, ...]:
        return tuple(
            values[current] / values[previous] - Decimal("1")
            for previous, current in zip(dates, dates[1:], strict=False)
        )

    @staticmethod
    def _covariance(left: tuple[Decimal, ...], right: tuple[Decimal, ...]) -> Decimal:
        left_mean = sum(left, Decimal("0")) / Decimal(len(left))
        right_mean = sum(right, Decimal("0")) / Decimal(len(right))
        numerator = sum(
            ((a - left_mean) * (b - right_mean) for a, b in zip(left, right, strict=True)),
            Decimal("0"),
        )
        return numerator / Decimal(len(left) - 1)

    @staticmethod
    def _correlation(
        covariance: Decimal, left_variance: Decimal, right_variance: Decimal
    ) -> Decimal:
        product = left_variance * right_variance
        return Decimal("0") if product == 0 else covariance / Decimal(str(sqrt(float(product))))

    @staticmethod
    def _contribution(
        ticker: str,
        tickers: tuple[str, ...],
        weights: dict[str, Decimal],
        covariance: dict[str, dict[str, Decimal]],
        volatility: Decimal | None,
    ) -> Decimal | None:
        if volatility is None:
            return None
        marginal = sum(
            (covariance[ticker][other] * weights[other] for other in tickers), Decimal("0")
        )
        return weights[ticker] * marginal / volatility

    @staticmethod
    def _unavailable(coverage: Decimal) -> RiskContributionProjection:
        return RiskContributionProjection(
            assets=(),
            portfolio_volatility=None,
            risk_coverage=coverage,
            covariance={},
            correlation={},
        )
