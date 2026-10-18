from decimal import Decimal

from income_analytics.application.cvm_magic_formula_normalization import (
    CvmRawAccount,
    MagicFormulaAccountingAdapterV1,
    NormalizationStatus,
)


def test_normalization_requires_one_consolidated_reference_date() -> None:
    records = tuple(
        CvmRawAccount(
            "issuer",
            "1",
            "2025-12-31",
            "DFP",
            "CONSOLIDATED",
            statement,
            code,
            code,
            Decimal("10"),
            "fixture",
            currency_scale="UNIDADE",
        )
        for statement, code in (
            ("DRE", "3.05"),
            ("BPA", "1.01.01"),
            ("BPP", "2.01.04"),
            ("BPP", "2.02.01"),
            ("BPA", "1.01.03"),
            ("BPA", "1.01.04"),
            ("BPP", "2.01.02"),
            ("BPA", "1.02.03"),
        )
    )
    values, lineage, status = MagicFormulaAccountingAdapterV1().normalize(records)
    assert status is NormalizationStatus.VALID
    assert values["cash_and_equivalents"] == Decimal("10")
    assert values["ebit"] == Decimal("10")
    assert lineage[0].adapter_version == "CVM_MAGIC_FORMULA_ADAPTER_V2_COMPONENT_LINEAGE"


def test_financial_investments_are_excluded_from_operating_working_capital() -> None:
    values = {
        "3.05": "50",
        "1.01.01": "10",
        "1.01.02": "999",
        "1.01.03": "30",
        "1.01.04": "20",
        "2.01.02": "15",
        "2.01.04": "7",
        "2.02.01": "9",
        "1.02.03": "40",
    }
    statements = {
        "3.05": "DRE",
        "1.01.01": "BPA",
        "1.01.02": "BPA",
        "1.01.03": "BPA",
        "1.01.04": "BPA",
        "2.01.02": "BPP",
        "2.01.04": "BPP",
        "2.02.01": "BPP",
        "1.02.03": "BPA",
    }
    records = tuple(
        CvmRawAccount(
            "issuer",
            "1",
            "2025-12-31",
            "DFP",
            "CONSOLIDATED",
            statements[code],
            code,
            code,
            Decimal(value),
            "fixture",
            currency_scale="UNIDADE",
        )
        for code, value in values.items()
    )
    normalized, lineage, status = MagicFormulaAccountingAdapterV1().normalize(records)

    assert status is NormalizationStatus.VALID
    assert normalized["operating_current_assets"] == Decimal("50")
    assert normalized["operating_current_liabilities"] == Decimal("15")
    assert normalized["operating_current_assets"] - normalized[
        "operating_current_liabilities"
    ] == Decimal("35")
    assert all(item.account_code != "1.01.02" for item in lineage)


def test_lineage_keeps_each_component_value_not_the_aggregate() -> None:
    records = tuple(
        CvmRawAccount(
            "issuer",
            "1",
            "2025-12-31",
            "DFP",
            "CONSOLIDATED",
            statement,
            code,
            code,
            Decimal(value),
            "fixture",
            currency_scale="UNIDADE",
        )
        for statement, code, value in (
            ("DRE", "3.05", "50"),
            ("BPA", "1.01.01", "10"),
            ("BPP", "2.01.04", "7"),
            ("BPP", "2.02.01", "9"),
            ("BPA", "1.01.03", "30"),
            ("BPA", "1.01.04", "20"),
            ("BPP", "2.01.02", "15"),
            ("BPA", "1.02.03", "40"),
        )
    )

    _, lineage, status = MagicFormulaAccountingAdapterV1().normalize(records)

    assert status is NormalizationStatus.VALID
    oca_components = [entry for entry in lineage if entry.metric == "operating_current_assets"]
    assert [entry.normalized_value for entry in oca_components] == [Decimal("30"), Decimal("20")]
