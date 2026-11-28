"""Routes for the investment tools catalog and Magic Formula rankings."""

from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status

from income_analytics.application.investment_tools import TOOLS, ranking_contract
from income_analytics.application.magic_formula_canonical_ranking import (
    MagicFormulaCanonicalRankingRepository,
    company_metadata_for_snapshot,
    ranking_read_model,
)

router = APIRouter(prefix="/api", tags=["Investment tools"])
logger = logging.getLogger(__name__)


@router.get("/tools")
def list_investment_tools() -> dict[str, object]:
    items = [tool.serialize() for tool in TOOLS]
    if MagicFormulaCanonicalRankingRepository().latest() is not None:
        items[0]["status"] = "PARTIAL"
        items[0]["version"] = "MF_BR_2027_V1"
    return {
        "category": "OPPORTUNITY_DISCOVERY",
        "category_label": "Oportunidades",
        "items": items,
    }


@router.get("/tools/magic-formula/stocks")
def magic_formula_stocks(
    q: str = "",
    exclude_retail: bool = False,
    exclude_aviation: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> dict[str, object]:
    try:
        snapshot = MagicFormulaCanonicalRankingRepository().latest()
        if snapshot is None:
            return {
                "tool": TOOLS[0].id,
                "methodology_version": "MF_BR_2027_V1",
                "status": "NO_PUBLISHED_RANKING",
                **ranking_read_model(
                    None,
                    query=q,
                    exclude_retail=exclude_retail,
                    exclude_aviation=exclude_aviation,
                    page=page,
                    page_size=page_size,
                ),
            }
        result = ranking_read_model(
            snapshot,
            company_metadata=company_metadata_for_snapshot(snapshot),
            query=q,
            exclude_retail=exclude_retail,
            exclude_aviation=exclude_aviation,
            page=page,
            page_size=page_size,
        )
    except (OSError, ValueError) as error:
        logger.exception("Unable to read published Magic Formula ranking")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MAGIC_FORMULA_RANKING_UNAVAILABLE",
        ) from error
    return {
        "tool": TOOLS[0].id,
        "methodology_version": "MF_BR_2027_V1",
        "status": "AVAILABLE",
        **result,
    }


@router.get("/tools/magic-formula/stocks/{company_id}")
def magic_formula_stock_detail(
    company_id: str, snapshot_id: str | None = Query(default=None, min_length=1)
) -> dict[str, object]:
    repository = MagicFormulaCanonicalRankingRepository()
    try:
        snapshot = repository.read_published(snapshot_id) if snapshot_id else repository.latest()
        metadata = company_metadata_for_snapshot(snapshot) if snapshot else {}
    except ValueError as error:
        if str(error) in {"MISSING_RANKING_SNAPSHOT", "RANKING_NOT_PUBLISHED"}:
            raise HTTPException(status_code=404, detail="RANKING_SNAPSHOT_NOT_FOUND") from error
        logger.exception("Unable to read published Magic Formula company detail")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MAGIC_FORMULA_COMPANY_DETAIL_UNAVAILABLE",
        ) from error
    except OSError as error:
        logger.exception("Unable to read published Magic Formula company detail")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MAGIC_FORMULA_COMPANY_DETAIL_UNAVAILABLE",
        ) from error
    if snapshot is None:
        raise HTTPException(status_code=404, detail="RANKING_NOT_AVAILABLE")
    result = next((row for row in snapshot["results"] if row["company_id"] == company_id), None)
    provenance = next(
        (row for row in snapshot["provenance"] if row["company_id"] == company_id), None
    )
    if result is None or provenance is None:
        raise HTTPException(status_code=404, detail="COMPANY_NOT_FOUND")
    company = {
        "company_id": result["company_id"],
        "ticker": result["selected_security"],
        "company_name": result["company_name"],
        "cvm_code": result["cvm_code"],
        "isin": result.get("selected_isin"),
        "sector": metadata.get(company_id, {}).get("sector"),
        "sector_source": "CVM_FCA_GENERAL_2025",
        "sector_source_reference": metadata.get(company_id, {}).get("sector_source_reference"),
        "sector_point_in_time_safe": "UNKNOWN",
        "listing_segment": None,
    }
    ranking = {
        "global_rank": result["global_rank"],
        "earnings_yield": result["earnings_yield"],
        "earnings_yield_rank": result["earnings_yield_rank"],
        "return_on_capital": result["return_on_capital"],
        "return_on_capital_rank": result["return_on_capital_rank"],
        "combined_score": result["combined_score"],
    }
    accounting = provenance.get("accounting", [])

    def accounting_total(*metrics: str) -> str | None:
        values = [
            Decimal(item["normalized_value"])
            for item in accounting
            if item.get("metric") in metrics and item.get("normalized_value") is not None
        ]
        return str(sum(values, Decimal("0"))) if values else None

    cash = accounting_total("cash_and_equivalents")
    debt = accounting_total("financial_debt_short_term", "financial_debt_long_term")
    calculation = {
        "ebit": result.get("ebit"),
        "enterprise_value": result.get("enterprise_value"),
        "capital_employed": result.get("invested_capital"),
        "market_cap": None,
        "cash": cash,
        "debt": debt,
        "share_price": result.get("price"),
        "shares_outstanding": None,
        "value_types": {
            "ebit": "SOURCE_VALUE",
            "enterprise_value": "DERIVED",
            "capital_employed": "DERIVED",
            "cash": "SOURCE_VALUE" if cash is not None else "UNAVAILABLE",
            "debt": "DERIVED" if debt is not None else "UNAVAILABLE",
            "market_cap": "UNAVAILABLE",
            "share_price": "SOURCE_VALUE",
        },
        "lineage": {
            "ebit": [
                item["source_reference"] for item in accounting if item.get("metric") == "ebit"
            ],
            "enterprise_value": {
                "formula": (
                    "market_cap + financial_debt_short_term + "
                    "financial_debt_long_term - cash_and_equivalents"
                ),
                "market_cap_source": provenance.get("market", {}).get("capital_source_reference"),
                "accounting_sources": [
                    item["source_reference"]
                    for item in accounting
                    if item.get("metric")
                    in {
                        "cash_and_equivalents",
                        "financial_debt_short_term",
                        "financial_debt_long_term",
                    }
                ],
                "price_source": provenance.get("selected_security_source", {}).get(
                    "price_source_reference"
                ),
                "shares_source": provenance.get("point_in_time", {}).get("shares_source"),
            },
            "capital_employed": {
                "formula": (
                    "operating_current_assets - operating_current_liabilities + net_fixed_assets"
                ),
                "accounting_sources": [
                    item["source_reference"]
                    for item in accounting
                    if item.get("metric")
                    in {
                        "operating_current_assets",
                        "operating_current_liabilities",
                        "net_fixed_assets",
                    }
                ],
            },
        },
    }
    snapshot_context = {
        "ranking_snapshot_id": snapshot["ranking_snapshot_id"],
        "ranking_as_of_date": snapshot["ranking_reference_date"],
        "policy_id": snapshot["policy_id"],
        "ranking_hash": snapshot["ranking_hash"],
    }
    return {
        # Keep the established response keys while adding a typed company-detail contract.
        "item": result,
        "provenance": provenance,
        "snapshot": snapshot_context,
        "company": company,
        "ranking": ranking,
        "calculation": calculation,
        "data_basis": {
            "financial_document_type": "DFP",
            "financial_reference_period": result.get("financial_reference_date"),
            "filing_date": result.get("filing_date"),
            "information_available_date": result.get("filing_date"),
            "financial_source": "CVM",
            "price_date": result.get("price_reference_date"),
            "price_source": provenance.get("selected_security_source", {}).get(
                "price_source_reference"
            ),
            "shares_reference_date": provenance.get("market", {})
            .get("shares_resolution", {})
            .get("reference_date"),
            "shares_source": provenance.get("market", {})
            .get("shares_resolution", {})
            .get("source_reference"),
            "point_in_time": provenance.get("point_in_time"),
            "sector_classification_date": None,
            "sector_point_in_time_safe": "UNKNOWN",
        },
    }


@router.get("/tools/magic-formula/fiis")
def magic_formula_fiis() -> dict[str, object]:
    return ranking_contract(TOOLS[1])
