"""Historical close resolution; never substitute a ticker or extend the approved window."""

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

POLICY_VERSION = "MAGIC_FORMULA_HISTORICAL_PRICE_V1"


def resolve(security, records, requested_date, *, source_available=True):
    requested = date.fromisoformat(requested_date)
    result = dict(
        issuer_id=security["issuer_id"],
        security_id=security["security_id"],
        ticker=security["ticker"],
        security_class=security["share_class"],
        valid_from=security.get("valid_from"),
        valid_to=security.get("valid_to"),
        requested_date=requested_date,
        effective_date=None,
        price=None,
        currency=None,
        resolution_method=None,
        source="B3_COTAHIST",
        source_reference=None,
        security_source_reference=security.get("source_reference"),
        policy_version=POLICY_VERSION,
        status="DATA_GAP",
        reason_code=None,
        cotahist_file_available=source_available,
        cotahist_record_found=False,
    )
    if not source_available:
        return dict(result, reason_code="SOURCE_FILE_UNAVAILABLE")
    if not security.get("ticker") or not security.get("valid_from"):
        return dict(result, reason_code="SECURITY_MAPPING_GAP")
    try:
        valid_from = date.fromisoformat(security["valid_from"])
        valid_to = date.fromisoformat(security["valid_to"]) if security.get("valid_to") else None
    except ValueError:
        return dict(result, status="REVIEW_REQUIRED", reason_code="TEMPORAL_CONFLICT")
    if valid_to and valid_to < valid_from:
        return dict(result, status="REVIEW_REQUIRED", reason_code="TEMPORAL_CONFLICT")
    if valid_from > requested or (valid_to and valid_to < requested):
        return dict(result, reason_code="SECURITY_NOT_ACTIVE_AT_REFERENCE_DATE")
    exact = [r for r in records if r["ticker"] == security["ticker"]]
    candidates = [
        r
        for r in exact
        if requested - timedelta(days=7) <= date.fromisoformat(r["effective_date"]) <= requested
        and valid_from <= date.fromisoformat(r["effective_date"])
        and (not valid_to or date.fromisoformat(r["effective_date"]) <= valid_to)
    ]
    result["cotahist_record_found"] = bool(candidates)
    if not candidates:
        return dict(
            result,
            reason_code="EFFECTIVE_DATE_GAP" if exact else "PRICE_RECORD_NOT_FOUND",
            last_source_date=max((r["effective_date"] for r in exact), default=None),
        )
    latest = max(r["effective_date"] for r in candidates)
    candidates = [r for r in candidates if r["effective_date"] == latest]
    if len(candidates) != 1:
        return dict(result, status="REVIEW_REQUIRED", reason_code="AMBIGUOUS_REFERENCE_PRICE")
    row = candidates[0]
    try:
        price = Decimal(row["price"])
    except InvalidOperation, TypeError, ValueError:
        return dict(result, status="REVIEW_REQUIRED", reason_code="INVALID_REFERENCE_PRICE")
    if not price.is_finite() or price <= 0 or row["currency"] != "R$":
        return dict(result, status="REVIEW_REQUIRED", reason_code="INVALID_REFERENCE_PRICE")
    return dict(
        result,
        status="RESOLVED",
        effective_date=latest,
        price=str(price),
        currency="BRL",
        raw_price=row["raw_price"],
        source_reference=row["source_reference"],
        resolution_method="EXACT_COTAHIST_DATE"
        if latest == requested_date
        else "PREVIOUS_TRADING_DAY_BY_POLICY",
    )


def gap_analysis(issuers):
    """Mutually exclusive intersections and gains from fixing one dimension alone."""
    eligible = [i for i in issuers if i["methodology_eligibility"] == "ELIGIBLE"]
    intersections, marginal = Counter(), Counter()
    for issuer in eligible:
        market = issuer["market_readiness"]
        flags = dict(
            PRICE=not market["price_ready"],
            ACCOUNTING=not issuer["accounting_readiness"]["ready"],
            SECURITY=not market["security_ready"],
            CAPITAL=not market["capital_ready"],
            IDENTITY=issuer["identity_status"] != "RESOLVED",
        )
        missing = [name for name, absent in flags.items() if absent]
        key = " + ".join(missing) if missing else "READY"
        intersections[key] += 1
        if len(missing) == 1:
            marginal[missing[0]] += 1
    full = sum(i["data_readiness_status"] == "FULL_DATA_READY" for i in eligible)
    return dict(
        intersections=dict(sorted(intersections.items())),
        marginal_blockers=dict(sorted(marginal.items())),
        price_only_blockers=marginal["PRICE"],
        max_full_data_ready_after_price=full + marginal["PRICE"],
        top_3_marginal_blockers=[
            [name, count]
            for name, count in sorted(marginal.items(), key=lambda x: (-x[1], x[0]))[:3]
        ],
    )
