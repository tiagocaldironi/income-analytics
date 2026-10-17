"""Build complete, independent Magic Formula golden fixtures."""
# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from income_analytics.application.cvm_magic_formula_normalization import ADAPTER_VERSION
from income_analytics.application.magic_formula_accounting_evidence import (
    AccountingEvidenceBundle,
    AccountingEvidenceStatus,
)
from income_analytics.application.magic_formula_contract import canonicalize_golden
from income_analytics.application.magic_formula_market_evidence import (
    CotahistPriceEvidence,
    MarketEvidenceStatus,
)
from income_analytics.application.magic_formula_security_capital_evidence import (
    SecurityCapitalEvidenceBundle,
    SecurityCapitalEvidenceStatus,
)


class GoldenFixtureStatus(StrEnum):
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
    READY_FOR_VALIDATION = "READY_FOR_VALIDATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class GoldenFixtureBuildResult:
    fixture: dict[str, object]
    status: GoldenFixtureStatus
    missing: tuple[str, ...]


class MagicFormulaGoldenEvidenceBuilder:
    """Join independent evidence bundles; never reads snapshots or providers."""

    def build(
        self,
        *,
        issuer_name: str,
        accounting: AccountingEvidenceBundle,
        security_capital: SecurityCapitalEvidenceBundle,
        prices: tuple[CotahistPriceEvidence, ...],
        market_reference_date: str,
        adapter_version: str = ADAPTER_VERSION,
        canonical_issuer: dict | None = None,
    ) -> GoldenFixtureBuildResult:
        if canonical_issuer is None:
            raise ValueError("CANONICAL_ISSUER_REQUIRED")
        missing = self._missing(accounting, security_capital, prices)
        status = (
            GoldenFixtureStatus.EVIDENCE_INCOMPLETE
            if missing
            else GoldenFixtureStatus.READY_FOR_VALIDATION
        )
        fixture: dict[str, object] = {
            "issuer": {
                "issuer_id": accounting.issuer_id,
                "cvm_code": accounting.cvm_code,
                "name": issuer_name,
            },
            "reference": {
                "financial_reference_date": accounting.reference_date,
                "market_reference_date": market_reference_date,
                "price_effective_date": (
                    prices[0].effective_date.isoformat()
                    if prices
                    and prices[0].effective_date
                    and len({p.effective_date for p in prices}) == 1
                    else None
                ),
                "adapter_version": adapter_version,
            },
            "accounting": self._accounting(accounting),
            "capital": {"securities": self._capital(security_capital)},
            "prices": self._prices(prices),
            "expected": self._expected(accounting, security_capital, prices) if not missing else {},
            "evidence_status": status.value,
            "lineage_complete": not missing,
            "lineage_missing": list(missing),
        }
        fixture = canonicalize_golden(fixture, canonical_issuer)
        for security in fixture["security"]:
            security["cvm_code"] = canonical_issuer["cvm_code"]
            price = next((p for p in prices if p.ticker == security["ticker"]), None)
            if price and price.isin:
                security["isin"] = price.isin
                security["isin_source_reference"] = price.record_reference
        return GoldenFixtureBuildResult(fixture, status, missing)

    @staticmethod
    def _accounting(bundle: AccountingEvidenceBundle) -> dict[str, object]:
        return {
            component.metric: {
                "rule_id": component.rule_id,
                "normalized_expected_value": str(component.normalized_value),
                "components": [
                    {
                        "source": source.source,
                        "source_file": source.source_file,
                        "dataset": source.dataset,
                        "source_reference": source.source_reference,
                        "account_code": source.account_code,
                        "account_description": source.account_description,
                        "statement_name": source.statement,
                        "statement_scope": source.statement_scope,
                        "period_start": source.period_start,
                        "period_end": source.period_end,
                        "reference_date": source.reference_date,
                        "raw_value": str(source.raw_value),
                        "currency": source.currency,
                        "currency_scale": source.currency_scale,
                        "normalization_multiplier": str(source.multiplier),
                        "normalized_expected_value": str(source.normalized_value),
                    }
                    for source in component.sources
                ],
            }
            for component in bundle.components
        }

    @staticmethod
    def _capital(bundle: SecurityCapitalEvidenceBundle) -> list[dict[str, object]]:
        return [
            {
                "issuer_id": item.issuer_id,
                "cvm_code": item.cvm_code,
                "security_id": item.security_id,
                "ticker": item.ticker,
                "share_class": item.share_class,
                "issued_or_integralized_shares": str(item.issued_shares),
                "treasury_shares": str(item.treasury_shares),
                "outstanding_shares": str(item.outstanding_shares),
                "quantity_unit": item.quantity_unit,
                "quantity_multiplier": str(item.quantity_multiplier),
                "normalized_quantity": str(item.normalized_quantity),
                "reference_date": item.reference_date.isoformat(),
                "source": item.source,
                "source_reference": item.source_reference,
                "issued_source_reference": item.issued_source_reference,
                "treasury_source_reference": item.treasury_source_reference,
                "outstanding_derivation_rule": item.outstanding_derivation_rule,
                "fca_source": item.fca_source,
                "fca_source_reference": item.fca_source_reference,
                "fca_form_id": item.fca_form_id,
                "valid_from": item.fca_valid_from.isoformat() if item.fca_valid_from else None,
                "valid_to": item.fca_valid_to.isoformat() if item.fca_valid_to else None,
            }
            for item in bundle.components
        ]

    @staticmethod
    def _prices(prices: tuple[CotahistPriceEvidence, ...]) -> list[dict[str, object]]:
        return [
            {
                "ticker": item.ticker,
                "requested_reference_date": item.requested_reference_date.isoformat(),
                "effective_date": item.effective_date.isoformat() if item.effective_date else None,
                "price": str(item.price) if item.price is not None else None,
                "currency": item.currency,
                "source": item.source,
                "source_file": item.source_file,
                "record_reference": item.record_reference,
                **({"isin": item.isin} if item.isin else {}),
            }
            for item in prices
        ]

    @staticmethod
    def _expected(
        accounting: AccountingEvidenceBundle,
        capital: SecurityCapitalEvidenceBundle,
        prices: tuple[CotahistPriceEvidence, ...],
    ) -> dict[str, str]:
        values = {item.metric: item.normalized_value for item in accounting.components}
        derived = {item.metric: item.normalized_value for item in accounting.derived}
        by_ticker = {item.ticker: item.price for item in prices}
        market_cap = sum(
            (item.normalized_quantity * by_ticker[item.ticker] for item in capital.components),
            Decimal("0"),
        )
        ev = market_cap + derived["net_debt"]
        return {
            "ebit": str(values["ebit"]),
            "cash_and_equivalents": str(values["cash_and_equivalents"]),
            "financial_debt_short_term": str(values["financial_debt_short_term"]),
            "financial_debt_long_term": str(values["financial_debt_long_term"]),
            "financial_debt_total": str(derived["financial_debt_total"]),
            "operating_current_assets": str(values["operating_current_assets"]),
            "operating_current_liabilities": str(values["operating_current_liabilities"]),
            "net_working_capital": str(derived["net_working_capital"]),
            "net_fixed_assets": str(values["net_fixed_assets"]),
            "invested_capital": str(derived["invested_capital"]),
            "net_debt": str(derived["net_debt"]),
            "market_cap": str(market_cap),
            "enterprise_value": str(ev),
            "earnings_yield": str(values["ebit"] / ev),
            "return_on_capital": str(values["ebit"] / derived["invested_capital"]),
        }

    @staticmethod
    def _missing(
        accounting: AccountingEvidenceBundle,
        capital: SecurityCapitalEvidenceBundle,
        prices: tuple[CotahistPriceEvidence, ...],
    ) -> tuple[str, ...]:
        missing = []
        if accounting.status is not AccountingEvidenceStatus.COMPLETE:
            missing.append("ACCOUNTING_EVIDENCE")
        if capital.status is not SecurityCapitalEvidenceStatus.RESOLVED:
            missing.append("SECURITY_CAPITAL_EVIDENCE")
        if not prices:
            missing.append("PRICE_EVIDENCE")
        for item in prices:
            if item.status is not MarketEvidenceStatus.VALID:
                missing.append(f"PRICE:{item.ticker}")
            elif not item.source_file or not item.record_reference:
                missing.append(f"PRICE_LINEAGE:{item.ticker}")
        if len({item.ticker for item in prices}) != len(prices):
            missing.append("DUPLICATE_PRICE_TICKER")
        if {item.ticker for item in capital.components} != {item.ticker for item in prices}:
            missing.append("CAPITAL_PRICE_SECURITY_MISMATCH")
        return tuple(missing)
