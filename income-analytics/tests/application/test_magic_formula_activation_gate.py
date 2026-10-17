from income_analytics.application.issuer_market_cap import IssuerMarketCapResolutionStatus
from income_analytics.application.magic_formula_activation_gate import (
    ActivationGateIssuer,
    MagicFormulaActivationGate,
)


def test_gate_reports_partial_coverage_and_never_ranks_before_release() -> None:
    result = MagicFormulaActivationGate().evaluate(
        (
            ActivationGateIssuer(
                "petrobras",
                IssuerMarketCapResolutionStatus.RESOLVED,
                True,
                True,
            ),
            ActivationGateIssuer(
                "vale",
                IssuerMarketCapResolutionStatus.UNIT_UNRESOLVED,
                True,
                True,
            ),
            ActivationGateIssuer(
                "ambev",
                IssuerMarketCapResolutionStatus.UNIT_UNRESOLVED,
                True,
                True,
            ),
            ActivationGateIssuer(
                "mrv",
                IssuerMarketCapResolutionStatus.UNIT_UNRESOLVED,
                True,
                True,
            ),
        ),
    )

    assert result.total_eligible_issuers == 4
    assert result.resolved_issuers == 1
    assert result.ranked_issuers == 0
    assert result.unresolved_issuers == 3
    assert result.coverage_percentage == 25
    assert result.exclusion_breakdown["UNIT_UNRESOLVED"] == 3
    assert result.tool_status == "VALIDATION_REQUIRED"
