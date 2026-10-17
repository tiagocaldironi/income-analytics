from income_analytics.application.magic_formula_component_validation import (
    ComponentValidationStatus,
    MagicFormulaComponentValidator,
)


def _fixture() -> dict[str, object]:
    return {
        "lineage_complete": True,
        "expected": {
            "ebit": "10",
            "cash_and_equivalents": "2",
            "financial_debt_short_term": "3",
            "financial_debt_long_term": "4",
            "financial_debt_total": "7",
            "operating_current_assets": "9",
            "operating_current_liabilities": "1",
            "net_working_capital": "8",
            "net_fixed_assets": "6",
            "invested_capital": "14",
            "net_debt": "5",
            "market_cap": "100",
            "enterprise_value": "105",
            "earnings_yield": "0.09523809523809523809523809524",
            "return_on_capital": "0.7142857142857142857142857143",
        },
        "accounting": {
            "operating_current_assets": {
                "rule_id": "NWC_ASSET_RULE_002",
                "components": [
                    {
                        "account_code": "1.01.03",
                        "normalized_expected_value": "9",
                        "source_reference": "dfp|x",
                    }
                ],
            }
        },
    }


def test_qa_passes_only_when_metrics_and_component_lineage_match() -> None:
    fixture = _fixture()
    actual = dict(fixture["expected"])
    lineage = [
        {"metric": "operating_current_assets", "account_code": "1.01.03", "normalized_value": "9"}
    ]

    result = MagicFormulaComponentValidator().validate(
        fixture=fixture, snapshot_metrics=actual, snapshot_lineage=lineage
    )

    assert result.status is ComponentValidationStatus.PASS


def test_qa_fails_when_aggregate_matches_but_component_lineage_diverges() -> None:
    fixture = _fixture()
    actual = dict(fixture["expected"])
    lineage = [
        {"metric": "operating_current_assets", "account_code": "1.01.03", "normalized_value": "8"}
    ]

    result = MagicFormulaComponentValidator().validate(
        fixture=fixture, snapshot_metrics=actual, snapshot_lineage=lineage
    )

    assert result.status is ComponentValidationStatus.FAIL


def test_qa_requires_fixture_lineage_and_snapshot_readback() -> None:
    fixture = _fixture()
    fixture["lineage_complete"] = False
    assert (
        MagicFormulaComponentValidator()
        .validate(fixture=fixture, snapshot_metrics={}, snapshot_lineage=[])
        .status
        is ComponentValidationStatus.REVIEW_REQUIRED
    )
    assert (
        MagicFormulaComponentValidator()
        .validate(fixture=_fixture(), snapshot_metrics=None, snapshot_lineage=[])
        .status
        is ComponentValidationStatus.FAIL
    )
