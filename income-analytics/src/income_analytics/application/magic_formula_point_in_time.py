"""Point-in-time selection and independent temporal checks for Magic Formula."""

from __future__ import annotations

from datetime import date
from typing import Any


def select_annual_financial_document(
    candidates: list[dict[str, Any]], as_of_date: str
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Select the latest eligible annual DFP, using receipt dates before values.

    Candidate financial values are deliberately ignored. ITR documents are
    recorded as unsupported by the existing annual-only accounting contract.
    """
    cutoff = date.fromisoformat(as_of_date)
    audited: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    for raw in candidates:
        item = dict(raw)
        item["selection_status"] = "REJECTED"
        item["rejection_reason"] = None
        if item.get("document_type") != "DFP":
            item["rejection_reason"] = "INTERIM_NOT_SUPPORTED_BY_ANNUAL_CONTRACT"
        else:
            available = item.get("information_available_date") or item.get("filing_date")
            if not available:
                item["rejection_reason"] = "AVAILABILITY_DATE_UNVERIFIED"
            elif date.fromisoformat(available) > cutoff:
                item["rejection_reason"] = "POST_AS_OF_INFORMATION"
            elif not item.get("period_end"):
                item["rejection_reason"] = "REFERENCE_PERIOD_UNVERIFIED"
            elif not item["period_end"].endswith("-12-31"):
                item["rejection_reason"] = "NON_ANNUAL_DFP_NOT_SUPPORTED_BY_ACCOUNTING_CONTRACT"
            else:
                item["information_available_date"] = available
                item["selection_status"] = "ELIGIBLE_CANDIDATE"
                eligible.append(item)
        audited.append(item)

    eligible.sort(
        key=lambda row: (
            row["period_end"],
            row["information_available_date"],
            int(row.get("version") or 0),
            str(row.get("source_id") or ""),
        ),
        reverse=True,
    )
    selected = eligible[0] if eligible else None
    if selected:
        selected["selection_status"] = "SELECTED"
        selected["rejection_reason"] = None
        for row in eligible[1:]:
            row["selection_status"] = "ELIGIBLE_NOT_SELECTED"
            row["rejection_reason"] = "OLDER_ELIGIBLE_ANNUAL_DOCUMENT"
    return selected, audited


def validate_point_in_time_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Validate saved lineage independently of the ranking builder."""
    as_of = date.fromisoformat(snapshot["ranking_as_of_date"])
    failures: list[dict[str, str]] = []
    checked = 0
    for row in snapshot.get("results", []):
        ticker = str(row.get("selected_security") or row.get("ticker") or "UNKNOWN")
        provenance = row.get("point_in_time_lineage")
        if not isinstance(provenance, dict):
            failures.append({"ticker": ticker, "reason": "LINEAGE_MISSING"})
            continue
        checked += 1
        for key in (
            "financial_information_available_date",
            "shares_information_available_date",
            "price_date",
            "security_identity_information_available_date",
        ):
            value = provenance.get(key)
            if not value:
                failures.append({"ticker": ticker, "reason": f"{key.upper()}_MISSING"})
            elif date.fromisoformat(value) > as_of:
                failures.append({"ticker": ticker, "reason": f"{key.upper()}_AFTER_AS_OF"})
        valid_from = provenance.get("security_valid_from")
        valid_to = provenance.get("security_valid_to")
        if not valid_from:
            failures.append({"ticker": ticker, "reason": "SECURITY_VALID_FROM_MISSING"})
        elif date.fromisoformat(valid_from) > as_of:
            failures.append({"ticker": ticker, "reason": "SECURITY_NOT_YET_VALID"})
        if valid_to and date.fromisoformat(valid_to) < as_of:
            failures.append({"ticker": ticker, "reason": "SECURITY_EXPIRED"})
        if not provenance.get("security_identity_source"):
            failures.append({"ticker": ticker, "reason": "SECURITY_IDENTITY_SOURCE_MISSING"})
        for key in (
            "selected_financial_document",
            "financial_source_hash",
            "price_source",
            "price_source_hash",
            "shares_source",
            "shares_source_hash",
            "security_identity_source_hash",
        ):
            if not provenance.get(key):
                failures.append({"ticker": ticker, "reason": f"{key.upper()}_MISSING"})
    return {
        "status": "PASS" if not failures else "FAIL",
        "ranking_as_of_date": as_of.isoformat(),
        "companies_checked": checked,
        "lookahead_companies": len(
            {item["ticker"] for item in failures if item["reason"].endswith("AFTER_AS_OF")}
        ),
        "failures": failures,
    }
