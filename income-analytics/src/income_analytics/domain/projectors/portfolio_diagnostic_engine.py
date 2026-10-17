"""Centralized deterministic diagnostic rules."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from income_analytics.domain.projectors.diversification_projector import DiversificationProjector
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
        comparison_allocation: AllocationProjection | None = None,
        comparison_analysis: PortfolioAllocationAnalysis | None = None,
        thresholds: DiagnosticThresholds = DiagnosticThresholds(),
        as_of: date | None = None,
    ) -> PortfolioIntelligence:
        as_of = as_of or date.today()
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
        findings = [
            cls._enrich(
                finding,
                allocation,
                allocation_analysis,
                comparison_allocation,
                comparison_analysis,
                thresholds,
                as_of,
            )
            for finding in findings
        ]
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
            candidates = [
                item
                for item in dimension.exposures
                if item.key not in {"NOT_APPLICABLE", "UNKNOWN", "UNCLASSIFIED", ""}
            ]
            if sum((item.weight for item in candidates), Decimal("0")) < Decimal("0.999999"):
                continue
            candidate = max(candidates, key=lambda item: item.weight, default=None)
            if candidate and candidate.weight > threshold:
                evidence: dict[str, Decimal | str] = {
                    "key": candidate.key,
                    "weight": candidate.weight,
                    "threshold": threshold,
                    "reference_type": "INCOME_TECHNICAL_THRESHOLD",
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
    def trajectory(
        current: Decimal,
        previous: Decimal,
        reference: Decimal,
        tolerance: Decimal = Decimal("0.01"),
    ) -> str:
        if current <= reference:
            return "RESOLVED" if previous > reference else "PERSISTENT"
        if previous <= reference:
            return "NEW"
        if current - previous > tolerance:
            return "WORSENING"
        if previous - current > tolerance:
            return "IMPROVING"
        return "PERSISTENT"

    @classmethod
    def _enrich(
        cls,
        finding: PortfolioFinding,
        allocation: AllocationProjection,
        analysis: PortfolioAllocationAnalysis | None,
        comparison: AllocationProjection | None,
        comparison_analysis: PortfolioAllocationAnalysis | None,
        thresholds: DiagnosticThresholds,
        as_of: date,
    ) -> PortfolioFinding:
        current = Decimal(
            str(
                finding.evidence.get(
                    "drift", finding.evidence.get("weight", finding.evidence.get("coverage", "0"))
                )
            )
        )
        threshold = Decimal(str(finding.evidence.get("threshold", "1")))
        key = str(finding.evidence.get("key", finding.evidence.get("ticker", "PORTFOLIO")))
        dimension = {
            "COUNTRY_CONCENTRATION": "COUNTRY",
            "SECTOR_CONCENTRATION": "SECTOR",
            "CLASS_CONCENTRATION": "ASSET_CLASS",
            "ASSET_CONCENTRATION": "ASSET",
            "DISPROPORTIONATE_RISK_CONTRIBUTION": "ASSET",
        }.get(finding.code, "PORTFOLIO")
        category = "DATA_QUALITY" if finding.category == "DATA_QUALITY" else "EXPOSURE"
        if finding.code == "DISPROPORTIONATE_RISK_CONTRIBUTION":
            category = "RISK"
            current = Decimal(str(finding.evidence["risk_contribution_share"]))
            threshold = (
                Decimal(str(finding.evidence["weight"]))
                * thresholds.max_risk_contribution_multiple
            )
        labels = {
            "BR": "Brasil",
            "US": "Estados Unidos",
            "BRAZILIAN_STOCK": "Ações Brasil",
            "FII": "FIIs",
            "FIXED_INCOME": "Renda fixa",
            "INTERNATIONAL": "Exterior",
            "CRYPTO": "Cripto",
            "US_REIT": "REITs EUA",
            "PENSION": "Previdência",
            "REAL_ESTATE": "Imóveis",
            "BRAZILIAN_ETF": "ETFs Brasil",
            "INTERNATIONAL_ETF": "ETFs exterior",
            "OTHER": "Outros",
        }
        previous = None
        issues: list[str] = []
        complete = (
            allocation.valuation_coverage == 1 and allocation.portfolio_market_value.amount > 0
        )
        comparable = (
            complete
            and comparison is not None
            and comparison.valuation_coverage == 1
            and comparison.portfolio_market_value.amount > 0
        )
        reference: dict[str, object] = {"type": "INCOME_TECHNICAL_THRESHOLD", "value": threshold}
        decomposition: tuple[dict[str, object], ...] = ()
        if finding.code == "PORTFOLIO_DRIFT":
            category, key = "STRATEGY", "ALLOCATION_POLICY"
            if analysis:
                decomposition = tuple(
                    {
                        "asset_class": item.asset_class.value,
                        "label": labels.get(item.asset_class.value, item.asset_class.value),
                        "current_weight": item.current_weight,
                        "target_weight": item.target_weight,
                        "deviation_pp": item.deviation * 100,
                    }
                    for item in sorted(
                        analysis.comparisons, key=lambda item: item.asset_class.value
                    )
                )
                reference["policy"] = {
                    "type": "USER_ALLOCATION_POLICY",
                    "targets": {
                        item.asset_class.value: item.target_weight
                        for item in sorted(
                            analysis.comparisons, key=lambda item: item.asset_class.value
                        )
                    },
                }
                reference["comparison_basis"] = "CURRENT_POLICY_APPLIED_TO_BOTH_DATES"
            if comparable and comparison_analysis:
                previous = comparison_analysis.portfolio_drift
        elif finding.code == "COUNTRY_CONCENTRATION" and comparable and comparison:
            country = DiversificationProjector.project(comparison).country
            invalid = {"NOT_APPLICABLE", "UNKNOWN", "UNCLASSIFIED", ""}
            if not any(item.key in invalid for item in country.exposures):
                previous = sum(
                    (item.weight for item in country.exposures if item.key == key), Decimal("0")
                )
        elif finding.code == "INCOMPLETE_RISK_COVERAGE":
            key = "RISK_COVERAGE"
            reference = {
                "type": "ANALYSIS_COMPLETENESS",
                "value": Decimal("1"),
                "denominator": "BASE_CURRENCY_MARKET_VALUE_OF_OPEN_INVESTED_POSITIONS",
                "numerator": "MARKET_VALUE_OF_POSITIONS_WITH_ANY_PERSISTED_PRICE_SERIES",
                "does_not_guarantee_covariance": True,
            }
        if not complete:
            issues.append("INCOMPLETE_CURRENT_VALUATION")
        if previous is None:
            issues.append(
                "INSUFFICIENT_COMPARISON_VALUATION"
                if not comparable
                else "COMPARISON_NOT_SUPPORTED_FOR_RULE"
            )
        if category == "DATA_QUALITY":
            issues.append(finding.code)
        change = current - previous if previous is not None else None
        trajectory = (
            cls.trajectory(current, previous, threshold, thresholds.trajectory_tolerance)
            if previous is not None
            else "UNKNOWN"
        )
        magnitude = 1 - current if category == "DATA_QUALITY" else current - threshold
        materiality = (
            "HIGH"
            if magnitude >= threshold and category != "DATA_QUALITY"
            else ("MEDIUM" if magnitude > thresholds.trajectory_tolerance else "LOW")
        )
        reason = (
            "DATA_COVERAGE_LIMITED"
            if category == "DATA_QUALITY"
            else ("EXCESS_AT_LEAST_REFERENCE" if materiality == "HIGH" else "REFERENCE_BREACH")
        )
        surface = magnitude > thresholds.surface_tolerance and (
            complete or category == "DATA_QUALITY"
        )
        label = {
            "ALLOCATION_POLICY": "Política de alocação",
            "RISK_COVERAGE": "Cobertura de risco",
        }.get(key, labels.get(key, key))
        current_label = {
            "PORTFOLIO_DRIFT": "Distância agregada à política de alocação",
            "INCOMPLETE_RISK_COVERAGE": "Peso dos ativos com série de preços",
            "DISPROPORTIONATE_RISK_CONTRIBUTION": "Participação no risco estimado",
        }.get(finding.code, "Exposição atual")
        evidence: list[dict[str, Decimal | str | date | None]] = [
            {
                "type": "CURRENT_VALUE",
                "label": current_label,
                "value": current,
                "unit": "PERCENTAGE",
                "as_of": as_of,
            },
            {
                "type": "REFERENCE",
                "label": "Completude esperada"
                if category == "DATA_QUALITY"
                else "Referência técnica do Income",
                "value": threshold,
                "unit": "PERCENTAGE",
                "as_of": as_of,
            },
        ]
        if previous is not None:
            evidence.extend(
                [
                    {
                        "type": "COMPARISON",
                        "label": "Valor há 90 dias",
                        "value": previous,
                        "unit": "PERCENTAGE",
                        "as_of": as_of - timedelta(days=90),
                    },
                    {
                        "type": "CHANGE",
                        "label": "Mudança em 90 dias",
                        "value": change * 100 if change is not None else None,
                        "unit": "PERCENTAGE_POINTS",
                        "as_of": as_of,
                    },
                ]
            )
        return replace(
            finding,
            category=category,
            logical_key=f"{finding.code}:{dimension}:{key}",
            subject={"dimension": dimension, "key": key, "label": label},
            current_value=current,
            reference=reference,
            comparison_value=previous,
            change=change,
            change_pp=change * 100 if change is not None else None,
            comparison_as_of=as_of - timedelta(days=90),
            trajectory=trajectory,
            materiality=materiality,
            materiality_reasons=(reason,),
            should_surface=surface,
            structured_evidence=tuple(evidence),
            decomposition=decomposition,
            causes=(),
            data_quality={
                "status": "PARTIAL" if issues else "COMPLETE",
                "issues": issues,
                "current_valuation_complete": complete,
                "comparison_valuation_complete": bool(comparable),
            },
            as_of=as_of,
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
