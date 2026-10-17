"""Assemble comparable fundamentals; this service never downloads raw data."""

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Protocol

from income_analytics.application.cvm_magic_formula_normalization import ADAPTER_VERSION


@dataclass(frozen=True, slots=True)
class AssembledFundamentals:
    issuer_id: str
    cvm_code: str
    company_name: str
    financial_reference_date: str
    statement_type: str
    statement_scope: str
    ebit: Decimal
    financial_debt_short_term: Decimal
    financial_debt_long_term: Decimal
    cash_and_equivalents: Decimal
    operating_current_assets: Decimal
    operating_current_liabilities: Decimal
    net_fixed_assets: Decimal
    market_cap: Decimal
    net_debt: Decimal
    net_working_capital: Decimal
    invested_capital: Decimal
    enterprise_value: Decimal
    earnings_yield: Decimal | None
    return_on_capital: Decimal | None
    normalization_status: str
    validation_status: str
    adapter_version: str = ADAPTER_VERSION


class MagicFormulaFundamentalsAssembler:
    def assemble_and_snapshot(
        self,
        *,
        snapshot_repository: "SnapshotWriter",
        market_reference_date: str,
        lineage: list[dict[str, object]],
        **kwargs: object,
    ) -> tuple[AssembledFundamentals, str]:
        fundamentals = self.assemble(**kwargs)  # type: ignore[arg-type]
        snapshot_id = snapshot_repository.save_if_absent(
            issuer_id=fundamentals.issuer_id,
            financial_reference_date=__import__("datetime").date.fromisoformat(
                fundamentals.financial_reference_date
            ),
            market_reference_date=__import__("datetime").date.fromisoformat(market_reference_date),
            statement_type=fundamentals.statement_type,
            statement_scope=fundamentals.statement_scope,
            adapter_version=fundamentals.adapter_version,
            normalization_status=fundamentals.normalization_status,
            validation_status=fundamentals.validation_status,
            metrics=asdict(fundamentals),
            lineage=lineage,
        )
        return fundamentals, snapshot_id

    def assemble(
        self,
        *,
        issuer_id: str,
        cvm_code: str,
        company_name: str,
        financial_reference_date: str,
        statement_type: str,
        metrics: dict[str, Decimal],
        market_cap: Decimal,
    ) -> AssembledFundamentals:
        required = {
            "ebit",
            "financial_debt_short_term",
            "financial_debt_long_term",
            "cash_and_equivalents",
            "operating_current_assets",
            "operating_current_liabilities",
            "net_fixed_assets",
        }
        if not required.issubset(metrics) or market_cap <= 0:
            raise ValueError("INSUFFICIENT_DATA")
        debt = metrics["financial_debt_short_term"] + metrics["financial_debt_long_term"]
        net_debt = debt - metrics["cash_and_equivalents"]
        nwc = metrics["operating_current_assets"] - metrics["operating_current_liabilities"]
        invested = nwc + metrics["net_fixed_assets"]
        ev = market_cap + net_debt
        status = "VALID" if ev > 0 and invested > 0 else "INELIGIBLE_METRICS"
        return AssembledFundamentals(
            issuer_id,
            cvm_code,
            company_name,
            financial_reference_date,
            statement_type,
            "CONSOLIDATED",
            metrics["ebit"],
            metrics["financial_debt_short_term"],
            metrics["financial_debt_long_term"],
            metrics["cash_and_equivalents"],
            metrics["operating_current_assets"],
            metrics["operating_current_liabilities"],
            metrics["net_fixed_assets"],
            market_cap,
            net_debt,
            nwc,
            invested,
            ev,
            metrics["ebit"] / ev if ev > 0 else None,
            metrics["ebit"] / invested if invested > 0 else None,
            status,
            "NOT_VALIDATED",
        )


class SnapshotWriter(Protocol):
    def save_if_absent(self, **kwargs: object) -> str: ...
