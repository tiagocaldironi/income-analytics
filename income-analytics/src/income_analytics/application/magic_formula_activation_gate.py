"""Explicit release gate for Magic Formula Stocks; it never activates a partial universe."""

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from income_analytics.application.issuer_market_cap import IssuerMarketCapResolutionStatus


@dataclass(frozen=True, slots=True)
class ActivationGateIssuer:
    issuer_id: str
    market_cap_status: IssuerMarketCapResolutionStatus
    fundamentals_comparable: bool
    lineage_complete: bool
    exclusion_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ActivationGateResult:
    total_eligible_issuers: int
    resolved_issuers: int
    ranked_issuers: int
    unresolved_issuers: int
    coverage_percentage: Decimal
    exclusion_breakdown: dict[str, int]
    critical_findings: tuple[str, ...]
    tool_status: str


class MagicFormulaActivationGate:
    minimum_resolved_issuers = 5

    def evaluate_canonical(self, repository, issuer_ids: tuple[str, ...], reference_date: str):
        """Use the one persisted eligibility policy; legacy booleans cannot approve release."""
        issuers = []
        for issuer_id in dict.fromkeys(issuer_ids):
            decision = repository.eligibility(issuer_id, reference_date)
            issuers.append(
                ActivationGateIssuer(
                    issuer_id,
                    IssuerMarketCapResolutionStatus.RESOLVED
                    if decision.eligible
                    else IssuerMarketCapResolutionStatus.INSUFFICIENT_MARKET_DATA,
                    decision.eligible,
                    decision.eligible,
                    None if decision.eligible else ",".join(decision.reasons),
                )
            )
        # The release gate remains closed in this phase, including with eligible inputs.
        return self.evaluate(tuple(issuers))

    def evaluate(
        self,
        issuers: tuple[ActivationGateIssuer, ...],
        *,
        critical_findings: tuple[str, ...] = (),
    ) -> ActivationGateResult:
        total = len(issuers)
        resolved = tuple(
            issuer
            for issuer in issuers
            if issuer.market_cap_status is IssuerMarketCapResolutionStatus.RESOLVED
            and issuer.fundamentals_comparable
            and issuer.lineage_complete
        )
        breakdown = Counter(
            issuer.exclusion_reason or issuer.market_cap_status.value
            for issuer in issuers
            if issuer not in resolved
        )
        findings = list(critical_findings)
        if len(resolved) < self.minimum_resolved_issuers:
            findings.append("INSUFFICIENT_RESOLVED_UNIVERSE")
        return ActivationGateResult(
            total_eligible_issuers=total,
            resolved_issuers=len(resolved),
            ranked_issuers=0,
            unresolved_issuers=total - len(resolved),
            coverage_percentage=(
                Decimal("0")
                if total == 0
                else Decimal("100") * Decimal(len(resolved)) / Decimal(total)
            ),
            exclusion_breakdown=dict(sorted(breakdown.items())),
            critical_findings=tuple(findings),
            tool_status="VALIDATION_REQUIRED",
        )
