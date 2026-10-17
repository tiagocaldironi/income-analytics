"""Independent, auditable accounting evidence for Magic Formula goldens.

This module deliberately does not call the production accounting adapter.  It
reads :class:`CvmRawAccount` records and applies the versioned, explicit CVM
accounting registry directly so a golden fixture can prove every component
before it is compared with a persisted snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from income_analytics.application.cvm_magic_formula_normalization import (
    RULES,
    AccountingRule,
    CvmRawAccount,
)
from income_analytics.application.monetary_amount import MonetaryScaleNormalizer


class AccountingEvidenceStatus(StrEnum):
    """Whether a bundle is safe to use as independent golden evidence."""

    COMPLETE = "COMPLETE"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    INVALID_SCOPE = "INVALID_SCOPE"
    TEMPORAL_CONFLICT = "TEMPORAL_CONFLICT"


@dataclass(frozen=True, slots=True)
class AccountingSourceEvidence:
    """One raw CVM account and its explicit BRL normalization evidence."""

    source: str
    source_file: str
    dataset: str
    source_reference: str
    account_code: str
    account_description: str
    statement: str
    statement_scope: str
    period_start: str | None
    period_end: str | None
    reference_date: str
    raw_value: Decimal
    currency: str
    currency_scale: str
    multiplier: Decimal
    normalized_value: Decimal


@dataclass(frozen=True, slots=True)
class AccountingEvidenceComponent:
    """Evidence for one normalized accounting metric."""

    metric: str
    rule_id: str
    sources: tuple[AccountingSourceEvidence, ...]
    normalized_value: Decimal


@dataclass(frozen=True, slots=True)
class DerivedAccountingEvidence:
    """A calculation performed outside the production assembler/adapter."""

    metric: str
    formula: str
    input_metrics: tuple[str, ...]
    normalized_value: Decimal


@dataclass(frozen=True, slots=True)
class AccountingEvidenceBundle:
    """Complete accounting evidence and independently-calculated totals."""

    issuer_id: str
    cvm_code: str
    reference_date: str
    components: tuple[AccountingEvidenceComponent, ...]
    derived: tuple[DerivedAccountingEvidence, ...]
    status: AccountingEvidenceStatus
    missing_metrics: tuple[str, ...]
    issues: tuple[str, ...]

    @property
    def lineage_complete(self) -> bool:
        return self.status is AccountingEvidenceStatus.COMPLETE

    def component(self, metric: str) -> AccountingEvidenceComponent:
        return next(item for item in self.components if item.metric == metric)

    def value(self, metric: str) -> Decimal:
        for item in self.components:
            if item.metric == metric:
                return item.normalized_value
        for item in self.derived:
            if item.metric == metric:
                return item.normalized_value
        raise KeyError(metric)


class MagicFormulaAccountingEvidenceBuilder:
    """Materializes CVM DFP/ITR evidence without reading snapshots.

    The narrow rule registry is imported to keep the evidence tied to the
    method version, but selection, monetary normalization and all totals are
    executed here independently from ``MagicFormulaAccountingAdapterV1``.
    """

    _normalizer = MonetaryScaleNormalizer()

    def build(self, records: tuple[CvmRawAccount, ...]) -> AccountingEvidenceBundle:
        if not records:
            return self._empty(AccountingEvidenceStatus.EVIDENCE_PENDING, ("NO_RECORDS",))

        issuer_ids = {record.issuer_id for record in records}
        cvm_codes = {record.cvm_code for record in records}
        dates = {record.reference_date for record in records}
        if len(issuer_ids) != 1 or len(cvm_codes) != 1:
            return self._empty(AccountingEvidenceStatus.INVALID_SCOPE, ("MIXED_ISSUER",))
        if any(record.statement_scope != "CONSOLIDATED" for record in records):
            return self._empty(
                AccountingEvidenceStatus.INVALID_SCOPE, ("NON_CONSOLIDATED",), records
            )
        if len(dates) != 1:
            return self._empty(
                AccountingEvidenceStatus.TEMPORAL_CONFLICT, ("MIXED_REFERENCE_DATE",), records
            )

        components: list[AccountingEvidenceComponent] = []
        missing: list[str] = []
        issues: list[str] = []
        for rule in RULES:
            component, component_issues = self._component(rule, records)
            issues.extend(component_issues)
            if component is None:
                missing.append(rule.metric)
            else:
                components.append(component)

        if missing or issues:
            return AccountingEvidenceBundle(
                records[0].issuer_id,
                records[0].cvm_code,
                records[0].reference_date,
                tuple(components),
                (),
                AccountingEvidenceStatus.EVIDENCE_PENDING,
                tuple(missing),
                tuple(issues),
            )

        values = {component.metric: component.normalized_value for component in components}
        derived = (
            DerivedAccountingEvidence(
                "financial_debt_total",
                "financial_debt_short_term + financial_debt_long_term",
                ("financial_debt_short_term", "financial_debt_long_term"),
                values["financial_debt_short_term"] + values["financial_debt_long_term"],
            ),
            DerivedAccountingEvidence(
                "net_debt",
                "financial_debt_total - cash_and_equivalents",
                ("financial_debt_total", "cash_and_equivalents"),
                values["financial_debt_short_term"]
                + values["financial_debt_long_term"]
                - values["cash_and_equivalents"],
            ),
            DerivedAccountingEvidence(
                "net_working_capital",
                "operating_current_assets - operating_current_liabilities",
                ("operating_current_assets", "operating_current_liabilities"),
                values["operating_current_assets"] - values["operating_current_liabilities"],
            ),
            DerivedAccountingEvidence(
                "invested_capital",
                "net_working_capital + net_fixed_assets",
                ("net_working_capital", "net_fixed_assets"),
                values["operating_current_assets"]
                - values["operating_current_liabilities"]
                + values["net_fixed_assets"],
            ),
        )
        return AccountingEvidenceBundle(
            records[0].issuer_id,
            records[0].cvm_code,
            records[0].reference_date,
            tuple(components),
            derived,
            AccountingEvidenceStatus.COMPLETE,
            (),
            (),
        )

    def _component(
        self,
        rule: AccountingRule,
        records: tuple[CvmRawAccount, ...],
    ) -> tuple[AccountingEvidenceComponent | None, tuple[str, ...]]:
        matched = tuple(
            record
            for record in records
            if record.statement == rule.statement and record.account_code in rule.account_codes
        )
        found_codes = {record.account_code for record in matched}
        missing_codes = tuple(code for code in rule.account_codes if code not in found_codes)
        duplicate_codes = tuple(
            code
            for code in rule.account_codes
            if sum(row.account_code == code for row in matched) > 1
        )
        if missing_codes or duplicate_codes:
            issues = tuple(
                [f"{rule.metric}:MISSING:{code}" for code in missing_codes]
                + [f"{rule.metric}:DUPLICATE:{code}" for code in duplicate_codes]
            )
            return None, issues

        sources: list[AccountingSourceEvidence] = []
        for record in matched:
            amount = self._normalizer.from_cvm(
                raw_value=record.value,
                currency=record.currency,
                source_scale=record.currency_scale,
                source=record.dataset,
            )
            if amount.normalized_value is None or amount.normalization_multiplier is None:
                return None, (f"{rule.metric}:UNRESOLVED_SCALE:{record.account_code}",)
            sources.append(
                AccountingSourceEvidence(
                    source="CVM_" + record.statement_type,
                    source_file=record.dataset,
                    dataset=record.dataset,
                    source_reference=self.source_reference(record),
                    account_code=record.account_code,
                    account_description=record.account_description,
                    statement=record.statement,
                    statement_scope=record.statement_scope,
                    period_start=record.period_start,
                    period_end=record.period_end,
                    reference_date=record.reference_date,
                    raw_value=amount.raw_value,
                    currency=amount.currency,
                    currency_scale=amount.source_scale.value,
                    multiplier=amount.normalization_multiplier,
                    normalized_value=amount.normalized_value,
                )
            )
        return (
            AccountingEvidenceComponent(
                rule.metric,
                rule.rule_id,
                tuple(sources),
                sum((source.normalized_value for source in sources), Decimal("0")),
            ),
            (),
        )

    @staticmethod
    def source_reference(record: CvmRawAccount) -> str:
        """Stable locator for the raw row inside the stated CVM CSV dataset."""
        return "|".join(
            (
                record.dataset,
                record.cvm_code,
                record.reference_date,
                record.statement_scope,
                record.statement,
                record.account_code,
                record.period_start or "",
                record.period_end or "",
            )
        )

    @staticmethod
    def _empty(
        status: AccountingEvidenceStatus,
        issues: tuple[str, ...],
        records: tuple[CvmRawAccount, ...] = (),
    ) -> AccountingEvidenceBundle:
        first = records[0] if records else None
        return AccountingEvidenceBundle(
            first.issuer_id if first else "",
            first.cvm_code if first else "",
            first.reference_date if first else "",
            (),
            (),
            status,
            tuple(rule.metric for rule in RULES),
            issues,
        )
