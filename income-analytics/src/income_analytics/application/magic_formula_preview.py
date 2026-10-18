"""Read-only Magic Formula preview over a frozen, complete-data universe."""

from decimal import Decimal, InvalidOperation

from income_analytics.application.magic_formula_ranking_validation import compare_independent_qa
from income_analytics.application.magic_formula_stocks import MagicFormulaStockRankingService
from income_analytics.application.monetary_amount import MonetaryScaleNormalizer

PREVIEW_STATUS = "ACTIVE"
PREVIEW_VERSION = "MAGIC_FORMULA_PREVIEW_V1"


def build_preview(universe: dict) -> dict:
    """Build a presentation-only preview without changing the release gate.

    ``FULL_DATA_READY`` establishes the source universe.  The ranking engine
    still refuses impossible ratios (zero or negative EV/invested capital), so
    those rows remain transparent and receive no position.
    """
    if universe["tool_status"] != "VALIDATION_REQUIRED" or universe["ranking_status"] != "INACTIVE":
        raise ValueError("PREVIEW_REQUIRES_BLOCKED_PRODUCTION_RANKING")
    complete = [
        issuer
        for issuer in universe["issuers"]
        if issuer["methodology_eligibility"] == "ELIGIBLE"
        and issuer["data_readiness_status"] == "FULL_DATA_READY"
    ]
    inputs, excluded = [], []
    for issuer in complete:
        try:
            input_row = _ranking_input(
                issuer, universe["reference_date"], universe["universe_snapshot_id"]
            )
        except ValueError as error:
            excluded.append(
                {
                    "issuer_id": issuer["issuer_id"],
                    "company_name": issuer["display_name"],
                    "reason_code": str(error),
                }
            )
        else:
            inputs.append(input_row)
    ranked = MagicFormulaStockRankingService()._rank_approved(inputs)
    compare_independent_qa(inputs, ranked)
    names = {issuer["issuer_id"]: issuer for issuer in complete}
    items = [
        {
            **row,
            "ticker": names[row["issuer_id"]]["securities"][0]["ticker"],
            "company_name": names[row["issuer_id"]]["display_name"],
            "sector": names[row["issuer_id"]]["economic_sector"],
        }
        for row in ranked
    ]
    total = len([i for i in universe["issuers"] if i["methodology_eligibility"] == "ELIGIBLE"])
    coverage = Decimal("100") * Decimal(len(complete)) / Decimal(total)
    return {
        "preview_status": PREVIEW_STATUS,
        "preview_version": PREVIEW_VERSION,
        "ranking_gate": "BLOCKED",
        "ranking_status": "INACTIVE",
        "data_status": "VALIDATION_REQUIRED",
        "reference_date": universe["reference_date"],
        "preview_eligible_count": len(complete),
        "preview_coverage": f"{coverage:.2f}",
        "coverage": {
            "companies_analyzed": len(complete),
            "universe_identified": total,
            "coverage_percentage": f"{coverage:.2f}",
            "awaiting_complete_data": total - len(complete),
            "ranked_companies": len(items),
            "not_ranked": len(excluded),
        },
        "items": items,
        "not_ranked": excluded,
        "message": (
            "Ranking preliminar. As posições podem mudar à medida que novas empresas "
            "forem incorporadas ao universo elegível."
        ),
        "production_ranking_message": "O ranking produtivo continua bloqueado.",
    }


def _ranking_input(issuer: dict, reference_date: str, universe_snapshot_id: str) -> dict:
    values: dict[str, Decimal] = {}
    normalizer = MonetaryScaleNormalizer()
    for evidence in issuer["accounting_readiness"]["evidence"]:
        try:
            amount = normalizer.from_cvm(
                raw_value=Decimal(evidence["raw_value"]),
                currency="BRL" if evidence["currency"] == "REAL" else "UNKNOWN",
                source_scale=evidence["currency_scale"],
                source=evidence["source_reference"],
            ).normalized_value
        except InvalidOperation, KeyError:
            amount = None
        if amount is None:
            raise ValueError("ACCOUNTING_VALUE_UNRESOLVED")
        values[evidence["metric"]] = values.get(evidence["metric"], Decimal("0")) + amount
    try:
        market_cap = _market_cap(issuer)
        enterprise_value = (
            market_cap
            + values["financial_debt_short_term"]
            + values["financial_debt_long_term"]
            - values["cash_and_equivalents"]
        )
        invested_capital = (
            values["operating_current_assets"]
            - values["operating_current_liabilities"]
            + values["net_fixed_assets"]
        )
        if enterprise_value <= 0:
            raise ValueError("NON_POSITIVE_ENTERPRISE_VALUE")
        if invested_capital <= 0:
            raise ValueError("NON_POSITIVE_INVESTED_CAPITAL")
        ebit = values["ebit"]
    except KeyError as error:
        raise ValueError("ACCOUNTING_VALUE_UNRESOLVED") from error
    return {
        "issuer_id": issuer["issuer_id"],
        "snapshot_id": universe_snapshot_id,
        "qa_id": "UNIVERSE_FULL_DATA_READY",
        "snapshot_digest": issuer["issuer_id"],
        "ebit": str(ebit),
        "enterprise_value": str(enterprise_value),
        "invested_capital": str(invested_capital),
        "earnings_yield": str(ebit / enterprise_value),
        "return_on_capital": str(ebit / invested_capital),
    }


def _market_cap(issuer: dict) -> Decimal:
    market = issuer["market_readiness"]
    outstanding = market.get("normalized_outstanding_by_class")
    if outstanding is None:
        quantities = issuer["historical_shares_unit_resolution"]["quantities"]
        outstanding = {
            item["share_class"]: item["normalized_quantity"]
            for item in quantities
            if item["quantity_kind"] == "issued"
        }
    treasury = market.get("raw_capital_quantities", {})
    components = []
    for security in issuer["securities"]:
        share_class = security["share_class"]
        if share_class not in {"ON", "PN"}:
            continue
        shares = Decimal(outstanding.get(share_class, "0")) - Decimal(
            treasury.get(share_class, {}).get("treasury", "0")
        )
        if shares > 0 and security.get("price"):
            components.append(shares * Decimal(security["price"]))
    if not components:
        raise ValueError("MARKET_CAP_UNRESOLVED")
    return sum(components, Decimal("0"))
