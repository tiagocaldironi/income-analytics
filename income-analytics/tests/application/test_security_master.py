from income_analytics.application.security_master import (
    B3IssuerRecord,
    SecurityMasterResolver,
    SecurityResolutionStatus,
)


def test_resolves_cvm_to_b3_only_with_matching_cvm_code_and_cnpj() -> None:
    result = SecurityMasterResolver.resolve_issuer(
        issuer_id="vale",
        cvm_code="4170",
        cvm_cnpj="33.592.510/0001-54",
        b3_record=B3IssuerRecord(
            cvm_code="4170",
            b3_issuer_id="VALE",
            cnpj="33592510000154",
            source_reference="GetInitialCompanies",
        ),
    )
    assert result is SecurityResolutionStatus.RESOLVED


def test_rejects_name_like_match_when_cnpj_is_different() -> None:
    result = SecurityMasterResolver.resolve_issuer(
        issuer_id="vale",
        cvm_code="4170",
        cvm_cnpj="33.592.510/0001-54",
        b3_record=B3IssuerRecord(
            cvm_code="4170",
            b3_issuer_id="VALE",
            cnpj="00000000000000",
            source_reference="GetInitialCompanies",
        ),
    )
    assert result is SecurityResolutionStatus.AMBIGUOUS
