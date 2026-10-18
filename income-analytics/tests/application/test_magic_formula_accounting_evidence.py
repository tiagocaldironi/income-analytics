from decimal import Decimal

from income_analytics.application.cvm_magic_formula_normalization import CvmRawAccount
from income_analytics.application.magic_formula_accounting_evidence import (
    AccountingEvidenceStatus,
    MagicFormulaAccountingEvidenceBuilder,
)


def _record(code: str, value: str, statement: str, *, scale: str = "MIL") -> CvmRawAccount:
    return CvmRawAccount(
        issuer_id="weg",
        cvm_code="005410",
        reference_date="2025-12-31",
        statement_type="DFP",
        statement_scope="CONSOLIDATED",
        statement=statement,
        account_code=code,
        account_description=f"Conta {code}",
        value=Decimal(value),
        dataset="dfp_cia_aberta_2025.zip",
        period_start="2025-01-01" if statement == "DRE" else None,
        period_end="2025-12-31",
        currency="BRL",
        currency_scale=scale,
    )


def _complete_records() -> tuple[CvmRawAccount, ...]:
    return (
        _record("3.05", "80", "DRE"),
        _record("1.01.01", "10", "BPA"),
        _record("2.01.04", "7", "BPP"),
        _record("2.02.01", "9", "BPP"),
        _record("1.01.03", "30", "BPA"),
        _record("1.01.04", "20", "BPA"),
        _record("2.01.02", "15", "BPP"),
        _record("1.02.03", "40", "BPA"),
    )


def test_acc_evid_builds_complete_evidence_and_independent_totals() -> None:
    bundle = MagicFormulaAccountingEvidenceBuilder().build(_complete_records())

    assert bundle.status is AccountingEvidenceStatus.COMPLETE
    assert bundle.lineage_complete is True
    assert bundle.component("ebit").rule_id == "EBIT_RULE_002"
    assert bundle.component("ebit").sources[0].source_reference == (
        "dfp_cia_aberta_2025.zip|005410|2025-12-31|CONSOLIDATED|DRE|3.05|2025-01-01|2025-12-31"
    )
    assert bundle.component("operating_current_assets").normalized_value == Decimal("50000")
    assert bundle.value("financial_debt_total") == Decimal("16000")
    assert bundle.value("net_debt") == Decimal("6000")
    assert bundle.value("net_working_capital") == Decimal("35000")
    assert bundle.value("invested_capital") == Decimal("75000")


def test_acc_evid_rejects_unknown_scale_without_default_multiplier() -> None:
    records = list(_complete_records())
    records[0] = _record("3.05", "80", "DRE", scale="UNKNOWN")

    bundle = MagicFormulaAccountingEvidenceBuilder().build(tuple(records))

    assert bundle.status is AccountingEvidenceStatus.EVIDENCE_PENDING
    assert bundle.missing_metrics == ("ebit",)
    assert bundle.issues == ("ebit:UNRESOLVED_SCALE:3.05",)


def test_acc_evid_requires_all_explicit_codes_and_never_includes_financial_investments() -> None:
    records = _complete_records()[:-1] + (_record("1.01.02", "999", "BPA"),)

    bundle = MagicFormulaAccountingEvidenceBuilder().build(records)

    assert bundle.status is AccountingEvidenceStatus.EVIDENCE_PENDING
    assert "net_fixed_assets" in bundle.missing_metrics
    assert all(
        source.account_code != "1.01.02"
        for component in bundle.components
        for source in component.sources
    )
