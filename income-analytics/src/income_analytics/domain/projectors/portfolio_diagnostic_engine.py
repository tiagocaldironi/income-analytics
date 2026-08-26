"""Centralized deterministic diagnostic rules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from income_analytics.domain.read_models.allocation_analysis import PortfolioAllocationAnalysis
from income_analytics.domain.read_models.allocation_projection import AllocationProjection
from income_analytics.domain.read_models.diversification_projection import DiversificationProjection
from income_analytics.domain.read_models.portfolio_intelligence import (
    DiagnosticThresholds,
    PortfolioFinding,
    PortfolioIntelligence,
)
from income_analytics.domain.read_models.risk_contribution_projection import (
    RiskContributionProjection,
)


class PortfolioDiagnosticEngine:
    @classmethod
    def analyze(
        cls,
        *,
        allocation: AllocationProjection,
        diversification: DiversificationProjection,
        risk: RiskContributionProjection | None = None,
        allocation_analysis: PortfolioAllocationAnalysis | None = None,
        thresholds: DiagnosticThresholds = DiagnosticThresholds(),
        as_of: date | None = None,
    ) -> PortfolioIntelligence:
        findings: list[PortfolioFinding] = []
        cls._asset_rule(findings, allocation, thresholds, as_of)
        cls._dimension_rules(findings, diversification, thresholds, as_of)
        if (
            allocation_analysis
            and allocation_analysis.portfolio_drift > thresholds.max_portfolio_drift
        ):
            findings.append(
                cls._finding(
                    "PORTFOLIO_DRIFT",
                    "ALLOCATION",
                    "ATTENTION",
                    "Desvio da política-alvo",
                    {
                        "drift": allocation_analysis.portfolio_drift,
                        "threshold": thresholds.max_portfolio_drift,
                    },
                    as_of,
                )
            )
        if allocation.valuation_coverage < 1:
            findings.append(
                cls._finding(
                    "INCOMPLETE_VALUATION",
                    "DATA_QUALITY",
                    "HIGH_ATTENTION",
                    "Valuation incompleto",
                    {"coverage": allocation.valuation_coverage},
                    as_of,
                )
            )
        if risk:
            cls._risk_rules(findings, risk, thresholds, as_of)
        findings = sorted(
            findings,
            key=lambda f: (
                {"HIGH_ATTENTION": 0, "ATTENTION": 1, "INFO": 2}[f.severity],
                f.category,
                f.code,
                str(f.evidence),
            ),
        )
        return PortfolioIntelligence(
            as_of=as_of,
            findings=tuple(findings),
            info_count=sum(f.severity == "INFO" for f in findings),
            attention_count=sum(f.severity == "ATTENTION" for f in findings),
            high_attention_count=sum(f.severity == "HIGH_ATTENTION" for f in findings),
        )

    @classmethod
    def _asset_rule(
        cls,
        findings: list[PortfolioFinding],
        allocation: AllocationProjection,
        thresholds: DiagnosticThresholds,
        as_of: date | None,
    ) -> None:
        if (
            allocation.largest_position_weight is None
            or allocation.largest_position_weight <= thresholds.max_asset_weight
        ):
            return
        item = max(
            (a for a in allocation.assets if a.portfolio_weight is not None),
            key=lambda a: (a.portfolio_weight or 0, str(a.position.asset.ticker)),
        )
        findings.append(
            cls._finding(
                "ASSET_CONCENTRATION",
                "CONCENTRATION",
                "ATTENTION",
                "Concentração por ativo",
                {
                    "ticker": str(item.position.asset.ticker),
                    "weight": item.portfolio_weight or Decimal("0"),
                    "threshold": thresholds.max_asset_weight,
                },
                as_of,
            )
        )

    @classmethod
    def _dimension_rules(
        cls,
        findings: list[PortfolioFinding],
        projection: DiversificationProjection,
        thresholds: DiagnosticThresholds,
        as_of: date | None,
    ) -> None:
        rules = (
            (
                projection.asset_class,
                "CLASS_CONCENTRATION",
                "CONCENTRATION",
                thresholds.max_class_weight,
            ),
            (
                projection.country,
                "COUNTRY_CONCENTRATION",
                "DIVERSIFICATION",
                thresholds.max_country_weight,
            ),
            (
                projection.sector,
                "SECTOR_CONCENTRATION",
                "DIVERSIFICATION",
                thresholds.max_sector_weight,
            ),
        )
        for dimension, code, category, threshold in rules:
            if dimension.largest_exposure and dimension.largest_exposure.weight > threshold:
                evidence: dict[str, Decimal | str] = {
                    "key": dimension.largest_exposure.key,
                    "weight": dimension.largest_exposure.weight,
                    "threshold": threshold,
                }
                findings.append(
                    cls._finding(
                        code, category, "ATTENTION", "Concentração de exposição", evidence, as_of
                    )
                )

    @classmethod
    def _risk_rules(
        cls,
        findings: list[PortfolioFinding],
        risk: RiskContributionProjection,
        thresholds: DiagnosticThresholds,
        as_of: date | None,
    ) -> None:
        if risk.risk_coverage < 1:
            findings.append(
                cls._finding(
                    "INCOMPLETE_RISK_COVERAGE",
                    "DATA_QUALITY",
                    "INFO",
                    "Cobertura de risco incompleta",
                    {"coverage": risk.risk_coverage},
                    as_of,
                )
            )
        for item in risk.assets:
            if (
                item.contribution_share is not None
                and item.contribution_share
                > item.weight * thresholds.max_risk_contribution_multiple
            ):
                evidence: dict[str, Decimal | str] = {
                    "ticker": item.ticker,
                    "weight": item.weight,
                    "risk_contribution_share": item.contribution_share,
                }
                findings.append(
                    cls._finding(
                        "DISPROPORTIONATE_RISK_CONTRIBUTION",
                        "RISK",
                        "ATTENTION",
                        "Contribuição de risco desproporcional",
                        evidence,
                        as_of,
                    )
                )

    @staticmethod
    def _finding(
        code: str,
        category: str,
        severity: str,
        title: str,
        evidence: dict[str, Decimal | str],
        as_of: date | None,
    ) -> PortfolioFinding:
        return PortfolioFinding(
            code=code,
            category=category,
            severity=severity,
            title=title,
            description=f"{title}.",
            evidence=evidence,
            as_of=as_of,
        )
