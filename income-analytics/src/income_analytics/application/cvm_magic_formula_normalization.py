"""Auditable CVM accounting normalization for Magic Formula Stocks V1.

This module intentionally receives raw records only; downloading CSV/ZIP files
belongs to a provider.  Every accepted transformation carries a rule id.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from income_analytics.application.monetary_amount import MonetaryScaleNormalizer

# V2 keeps the V1 methodology intact and corrects only per-account lineage:
# a component now stores its own normalized value, never the aggregate total.
# Existing V1 snapshots remain immutable audit artifacts and must not be
# overwritten; the repaired evidence is materialized under this new version.
ADAPTER_VERSION = "CVM_MAGIC_FORMULA_ADAPTER_V2_COMPONENT_LINEAGE"


class NormalizationStatus(StrEnum):
    VALID = "VALID"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    ACCOUNTING_NOT_COMPARABLE = "ACCOUNTING_NOT_COMPARABLE"
    TEMPORAL_INCONSISTENCY = "TEMPORAL_INCONSISTENCY"


@dataclass(frozen=True, slots=True)
class CvmRawAccount:
    issuer_id: str
    cvm_code: str
    reference_date: str
    statement_type: str
    statement_scope: str
    statement: str
    account_code: str
    account_description: str
    value: Decimal
    dataset: str
    period_start: str | None = None
    period_end: str | None = None
    currency: str = "BRL"
    currency_scale: str = "UNKNOWN"
    filing_version: str | None = None


@dataclass(frozen=True, slots=True)
class MetricLineage:
    metric: str
    rule_id: str
    account_code: str
    account_description: str
    raw_value: Decimal
    normalized_value: Decimal
    reference_date: str
    statement_scope: str
    dataset: str
    adapter_version: str = ADAPTER_VERSION
    period_start: str | None = None
    period_end: str | None = None
    source_currency: str = "BRL"
    source_scale: str = "UNKNOWN"
    normalization_multiplier: Decimal | None = None
    normalization_rule_id: str | None = None


@dataclass(frozen=True, slots=True)
class AccountingRule:
    metric: str
    rule_id: str
    statement: str
    account_codes: tuple[str, ...]


# V1 was not released and has no persisted production snapshots.  These fixed
# codes are intentionally narrow: they prefer an explicit DATA GAP to a
# description-based or economically ambiguous inclusion.
RULES = (
    AccountingRule("ebit", "EBIT_RULE_002", "DRE", ("3.05",)),
    AccountingRule("cash_and_equivalents", "CASH_RULE_001", "BPA", ("1.01.01",)),
    AccountingRule("financial_debt_short_term", "DEBT_ST_RULE_001", "BPP", ("2.01.04",)),
    # The CVM structural account explicitly covers loans, financing and
    # debentures.  It deliberately excludes generic non-current liabilities.
    AccountingRule("financial_debt_long_term", "DEBT_LT_RULE_001", "BPP", ("2.02.01",)),
    # 1.01.02 is financial investments, not operating working capital and not
    # cash by default.  Never add it here without a separate methodology rule.
    AccountingRule("operating_current_assets", "NWC_ASSET_RULE_002", "BPA", ("1.01.03", "1.01.04")),
    AccountingRule("operating_current_liabilities", "NWC_LIABILITY_RULE_001", "BPP", ("2.01.02",)),
    AccountingRule("net_fixed_assets", "FIXED_ASSET_RULE_001", "BPA", ("1.02.03",)),
)


class MagicFormulaAccountingAdapterV1:
    """Centralized fixed-code mapping; ambiguous inputs stay out of ranking."""

    version = ADAPTER_VERSION
    _monetary_normalizer = MonetaryScaleNormalizer()

    def normalize(
        self, records: tuple[CvmRawAccount, ...]
    ) -> tuple[dict[str, Decimal], tuple[MetricLineage, ...], NormalizationStatus]:
        if not records or any(record.statement_scope != "CONSOLIDATED" for record in records):
            return {}, (), NormalizationStatus.ACCOUNTING_NOT_COMPARABLE
        if len({record.issuer_id for record in records}) != 1:
            return {}, (), NormalizationStatus.ACCOUNTING_NOT_COMPARABLE
        dates = {record.reference_date for record in records}
        if len(dates) != 1:
            return {}, (), NormalizationStatus.TEMPORAL_INCONSISTENCY
        if len({record.statement_type for record in records}) != 1 or any(
            record.period_end is not None and record.period_end != record.reference_date
            for record in records
        ):
            return {}, (), NormalizationStatus.TEMPORAL_INCONSISTENCY
        values: dict[str, Decimal] = {}
        lineage: list[MetricLineage] = []
        for rule in RULES:
            matched = [
                record
                for record in records
                if (
                    record.statement == rule.statement and record.account_code in rule.account_codes
                )
            ]
            # Every component must occur exactly once. In particular ITR may
            # contain both quarterly and YTD DRE rows: callers must select a
            # period explicitly, never sum the two or silently drop a component.
            if any(
                sum(record.account_code == code for record in matched) != 1
                for code in rule.account_codes
            ):
                return {}, tuple(lineage), NormalizationStatus.INSUFFICIENT_DATA
            amounts = tuple(
                self._monetary_normalizer.from_cvm(
                    raw_value=record.value,
                    currency=record.currency,
                    source_scale=record.currency_scale,
                    source=record.dataset,
                )
                for record in matched
            )
            if any(amount.normalized_value is None for amount in amounts):
                return {}, tuple(lineage), NormalizationStatus.INSUFFICIENT_DATA
            total = sum((amount.normalized_value for amount in amounts), Decimal("0"))
            values[rule.metric] = total
            lineage.extend(
                MetricLineage(
                    rule.metric,
                    rule.rule_id,
                    record.account_code,
                    record.account_description,
                    amount.raw_value,
                    # Lineage is evidence for one raw account, not the
                    # aggregate metric.  Keeping ``total`` here made a
                    # multi-account metric (for example OCA) impossible to
                    # audit component-by-component even when its aggregate
                    # value was correct.
                    amount.normalized_value,
                    record.reference_date,
                    record.statement_scope,
                    record.dataset,
                    ADAPTER_VERSION,
                    record.period_start,
                    record.period_end,
                    amount.currency,
                    amount.source_scale.value,
                    amount.normalization_multiplier,
                    amount.normalization_rule_id,
                )
                for record, amount in zip(matched, amounts, strict=True)
            )
        return values, tuple(lineage), NormalizationStatus.VALID
