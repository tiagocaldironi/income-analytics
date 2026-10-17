"""Pure, versioned Magic Formula V1 normalization and ranking rules."""

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from income_analytics.application.magic_formula_activation_gate import MagicFormulaActivationGate
from income_analytics.application.magic_formula_contract import EligibilityDecision

# Ranking validation consumes only the approved component-lineage snapshots.
ADAPTER_VERSION = "CVM_MAGIC_FORMULA_ADAPTER_V2_COMPONENT_LINEAGE"
METHODOLOGY_VERSION = "MAGIC_FORMULA_STOCKS_V1"


@dataclass(frozen=True, slots=True)
class NormalizedCompanyFundamentals:
    issuer_id: str
    company_name: str
    ticker: str
    sector: str | None
    ebit: Decimal | None
    cash_and_equivalents: Decimal | None
    financial_debt: Decimal | None
    operating_current_assets: Decimal | None
    operating_current_liabilities: Decimal | None
    net_fixed_assets: Decimal | None
    market_cap: Decimal | None
    financial_reference_date: str
    statement_type: str
    statement_scope: str

    def metrics(self) -> tuple[Decimal, Decimal, Decimal, Decimal] | None:
        values = (
            self.ebit,
            self.cash_and_equivalents,
            self.financial_debt,
            self.operating_current_assets,
            self.operating_current_liabilities,
            self.net_fixed_assets,
            self.market_cap,
        )
        if any(value is None for value in values):
            return None
        net_debt = self.financial_debt - self.cash_and_equivalents
        enterprise_value = self.market_cap + net_debt
        invested_capital = (
            self.operating_current_assets
            - self.operating_current_liabilities
            + self.net_fixed_assets
        )
        if enterprise_value <= 0 or invested_capital <= 0:
            return None
        return (
            net_debt,
            enterprise_value,
            self.ebit / enterprise_value,
            self.ebit / invested_capital,
        )


class RankingEvidenceRepository(Protocol):
    def eligibility(self, issuer_id: str, reference_date: str) -> EligibilityDecision: ...
    def read_snapshot(self, snapshot_id: str) -> dict | None: ...


class MagicFormulaStockRankingService:
    """Ranks only comparable, fully normalized issuers; ties use dense ranks."""

    def rank_validation_sample(self, sample: dict, *, repository) -> list[dict]:
        """Explicit validation execution, without granting publication permission."""
        from income_analytics.application.magic_formula_ranking_validation import (
            validate_frozen_sample,
        )

        inputs = validate_frozen_sample(repository, sample)
        return self._rank_approved(inputs)

    @staticmethod
    def _rank_approved(inputs: list[dict]) -> list[dict]:
        # These inputs have already passed canonical eligibility. Financial
        # ratios come directly from their frozen fundamentals snapshots.
        ranks = {}
        for metric in ("earnings_yield", "return_on_capital"):
            ordered = sorted(inputs, key=lambda i: Decimal(i[metric]), reverse=True)
            previous, position = None, 0
            ranks[metric] = {}
            for item in ordered:
                value = Decimal(item[metric])
                if value != previous:
                    position += 1
                    previous = value
                ranks[metric][item["issuer_id"]] = position
        result = []
        for item in inputs:
            issuer = item["issuer_id"]
            ey_rank = ranks["earnings_yield"][issuer]
            roc_rank = ranks["return_on_capital"][issuer]
            result.append(
                dict(
                    issuer_id=issuer,
                    fundamentals_snapshot_id=item["snapshot_id"],
                    formal_qa_id=item["qa_id"],
                    fundamentals_snapshot_digest=item["snapshot_digest"],
                    earnings_yield=item["earnings_yield"],
                    return_on_capital=item["return_on_capital"],
                    earnings_yield_rank=ey_rank,
                    return_on_capital_rank=roc_rank,
                    magic_formula_score=ey_rank + roc_rank,
                    adapter_version=ADAPTER_VERSION,
                    methodology_version=METHODOLOGY_VERSION,
                )
            )
        result.sort(key=lambda i: (i["magic_formula_score"], i["issuer_id"]))
        previous, rank = None, 0
        for display_order, item in enumerate(result, 1):
            score = item["magic_formula_score"]
            if score != previous:
                rank += 1
                previous = score
            item["final_rank"] = rank
            item["final_display_order"] = display_order
            item["score_tied"] = sum(r["magic_formula_score"] == score for r in result) > 1
        return result

    def rank(
        self,
        companies: tuple[NormalizedCompanyFundamentals, ...],
        *,
        repository: RankingEvidenceRepository | None = None,
        reference_date: str | None = None,
    ) -> tuple[dict[str, object], ...]:
        if repository is None or reference_date is None:
            raise ValueError("CANONICAL_ELIGIBILITY_REQUIRED")
        gate = MagicFormulaActivationGate().evaluate_canonical(
            repository,
            tuple(company.issuer_id for company in companies),
            reference_date,
        )
        if gate.tool_status != "AVAILABLE":
            raise ValueError("RANKING_GATE_BLOCKED")
        eligible = []
        for company in companies:
            decision = repository.eligibility(company.issuer_id, reference_date)
            if not decision.eligible or decision.snapshot_id is None:
                continue
            snapshot = repository.read_snapshot(decision.snapshot_id)
            if snapshot is None:
                continue
            values = json.loads(snapshot["metrics_json"])
            # Never attach a valid decision to a different set of caller-supplied numbers.
            if company.financial_reference_date != reference_date or (
                company.statement_type != snapshot["statement_type"]
                or company.statement_scope != snapshot["statement_scope"]
            ):
                continue
            keys = (
                "ebit",
                "cash_and_equivalents",
                "operating_current_assets",
                "operating_current_liabilities",
                "net_fixed_assets",
                "market_cap",
            )
            if any(getattr(company, key) != Decimal(values[key]) for key in keys):
                continue
            if company.financial_debt != (
                Decimal(values["financial_debt_short_term"])
                + Decimal(values["financial_debt_long_term"])
            ):
                continue
            if metrics := company.metrics():
                eligible.append((company, metrics))
        ordered_ey = sorted(eligible, key=lambda item: item[1][2], reverse=True)
        ordered_roc = sorted(eligible, key=lambda item: item[1][3], reverse=True)
        ey_rank = self._dense_ranks(ordered_ey, 2)
        roc_rank = self._dense_ranks(ordered_roc, 3)
        result = []
        for company, metrics in eligible:
            score = ey_rank[company.issuer_id] + roc_rank[company.issuer_id]
            result.append(
                {
                    "ticker": company.ticker,
                    "company_name": company.company_name,
                    "sector": company.sector,
                    "net_debt": metrics[0],
                    "enterprise_value": metrics[1],
                    "earnings_yield": metrics[2],
                    "return_on_capital": metrics[3],
                    "earnings_yield_rank": ey_rank[company.issuer_id],
                    "return_on_capital_rank": roc_rank[company.issuer_id],
                    "magic_formula_score": score,
                    "financial_reference_date": company.financial_reference_date,
                    "data_status": "AVAILABLE",
                    "adapter_version": ADAPTER_VERSION,
                }
            )
        return tuple(sorted(result, key=lambda item: (item["magic_formula_score"], item["ticker"])))

    @staticmethod
    def _dense_ranks(
        items: list[
            tuple[NormalizedCompanyFundamentals, tuple[Decimal, Decimal, Decimal, Decimal]]
        ],
        metric: int,
    ) -> dict[str, int]:
        ranks: dict[str, int] = {}
        previous = None
        rank = 0
        for company, values in items:
            if values[metric] != previous:
                rank += 1
                previous = values[metric]
            ranks[company.issuer_id] = rank
        return ranks
