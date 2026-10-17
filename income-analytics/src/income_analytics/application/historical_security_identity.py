"""Resolve malformed declared tickers only through independent identity evidence."""

import re
from copy import deepcopy
from datetime import datetime

from income_analytics.application.historical_price import resolve

POLICY = "HISTORICAL_SECURITY_IDENTITY_V1"


def recover_price(issuer, offer, current, records, reference):
    """Return a proposal; caller must verify source hashes and independently read back.

    Deliberately excludes corporate actions and already plausible tickers. A current
    directory entry alone cannot authorize a historical mapping.
    """

    def require(condition, reason):
        if not condition:
            raise ValueError(reason)

    market = issuer["market_readiness"]
    require(
        issuer["methodology_eligibility"] == "ELIGIBLE"
        and issuer["identity_status"] == "RESOLVED"
        and issuer["accounting_readiness"]["ready"]
        and market["security_ready"]
        and market["capital_ready"]
        and not market["price_ready"]
        and issuer["data_reason_codes"] == ["NO_REFERENCE_PRICE"],
        "NOT_PRICE_ONLY_BLOCKER",
    )
    require(len(issuer["securities"]) == 1, "MULTIPLE_SECURITIES_REQUIRE_REVIEW")
    security = issuer["securities"][0]
    require(
        not re.fullmatch(r"[A-Z]{4}\d{1,2}", security["ticker"] or ""),
        "TICKER_HISTORY_REQUIRES_EVENT_EVIDENCE",
    )
    require(offer["schema_version"] == "B3_OFFER_IDENTITY_V1", "UNSUPPORTED_PROOF")
    require(offer["cnpj"] == current["cnpj"] == issuer["cnpj"], "CNPJ_MISMATCH")
    require(int(current["codeCVM"]) == int(issuer["cvm_code"]), "CVM_MISMATCH")
    require(
        offer["document_date"] <= security["form_reference"] <= reference,
        "PROOF_POSTDATES_REFERENCE",
    )
    require(security["share_class"] == offer["share_class"] == "ON", "SHARE_CLASS_MISMATCH")
    require(
        current.get("otherCodes") == [{"code": offer["ticker"], "isin": offer["isin"]}],
        "AMBIGUOUS_CURRENT_IDENTITY",
    )
    listed = datetime.strptime(current["dateQuotation"], "%d/%m/%Y").date().isoformat()
    require(listed <= reference, "LISTING_AFTER_REFERENCE")
    require(offer["document_date"] <= listed, "OFFER_POSTDATES_LISTING")
    evidence = issuer["historical_shares_unit_resolution"]["evidence"]
    require(
        evidence["status"] == "VERIFIED"
        and evidence["cnpj"] == issuer["cnpj"]
        and evidence["reference_date"] == reference,
        "CAPITAL_IDENTITY_UNVERIFIED",
    )
    mapped = dict(
        security,
        ticker=offer["ticker"],
        isin=offer["isin"],
        valid_from=max(security["valid_from"], listed),
    )
    matching = [r for r in records if r["ticker"] == offer["ticker"] and r["market"] == "010"]
    require(
        bool(matching) and all(r["isin"] == offer["isin"] for r in matching),
        "HISTORICAL_ISIN_CONFLICT",
    )
    resolution = resolve(mapped, matching, reference)
    require(resolution["status"] == "RESOLVED", resolution["reason_code"])
    result = deepcopy(issuer)
    mapped.update(
        declared_ticker=security["ticker"],
        price_status="AVAILABLE",
        effective_market_date=resolution["effective_date"],
        price=resolution["price"],
        price_source_reference=resolution["source_reference"],
        identity_resolution={
            "policy_version": POLICY,
            "offer": deepcopy(offer),
            "current_directory": deepcopy(current),
            "price": resolution,
        },
    )
    result["securities"] = [mapped]
    result["market_readiness"].update(
        status="RESOLVABLE",
        price_ready=True,
        price_readiness_tickers=[mapped["ticker"]],
        reason_codes=[],
    )
    result.update(
        data_readiness_status="FULL_DATA_READY", eligibility_status="ELIGIBLE", data_reason_codes=[]
    )
    return result


EXCHANGE_DIRECTORY_POLICY = "B3_LISTED_SECURITY_IDENTITY_V1"


def _class_matches_ticker_isin(ticker, isin, share_class):
    """Accept only standard B3 share suffixes and matching Brazilian ISIN classes."""
    classes = {
        "3": ("ON", "CNOR"),
        "4": ("PN", "CNPR"),
        "5": ("PNA", "CNPA"),
        "6": ("PNB", "CNPB"),
    }
    if not isinstance(ticker, str) or not isinstance(isin, str) or len(isin) != 12:
        return False
    suffix = ticker[-1:]
    mapping = classes.get(suffix)
    return bool(mapping and mapping == (share_class, isin[7:11]))


def recover_price_from_exchange_identity(issuer, proof, current, records, reference):
    """Resolve one missing class from B3 issuer identity and dated COTAHIST rows.

    CVM/CNPJ binds the issuer; ticker/ISIN and the ISIN class code bind one
    security class; a historical B3 row in the approved date window supplies the
    price. Multiple securities remain supported, but only one missing security
    of the proven class can be updated per call. Corporate actions without a
    same-issuer, same-class, same-ISIN chain fail closed.
    """

    def require(condition, reason):
        if not condition:
            raise ValueError(reason)

    market = issuer["market_readiness"]
    require(
        issuer["methodology_eligibility"] == "ELIGIBLE"
        and issuer["identity_status"] == "RESOLVED"
        and issuer["accounting_readiness"]["ready"]
        and market["security_ready"]
        and market["capital_ready"]
        and not market["price_ready"]
        and "NO_REFERENCE_PRICE" in issuer["data_reason_codes"],
        "NOT_PRICE_ONLY_BLOCKER",
    )
    require(proof["schema_version"] == EXCHANGE_DIRECTORY_POLICY, "UNSUPPORTED_PROOF")
    require(proof["cnpj"] == current["cnpj"] == issuer["cnpj"], "CNPJ_MISMATCH")
    require(int(current["codeCVM"]) == int(issuer["cvm_code"]), "CVM_MISMATCH")
    require(int(proof["cvm_code"]) == int(issuer["cvm_code"]), "CVM_MISMATCH")
    require(
        current.get("status") == "A" and current.get("hasQuotation") == "S",
        "SECURITY_NOT_CURRENTLY_LISTED",
    )
    require(
        _class_matches_ticker_isin(proof["ticker"], proof["isin"], proof["share_class"]),
        "TICKER_ISIN_CLASS_MISMATCH",
    )
    directory_codes = list(current.get("otherCodes") or [])
    if current.get("code") and current.get("otherCodes") is None:
        directory_codes.append({"code": current["code"], "isin": current.get("isin")})
    ticker_codes = [item for item in directory_codes if item.get("code") == proof["ticker"]]
    require(
        len(ticker_codes) == 1 and ticker_codes[0].get("isin") == proof["isin"],
        "AMBIGUOUS_CURRENT_IDENTITY" if ticker_codes else "TICKER_NOT_IN_DIRECTORY",
    )
    candidates = [
        (index, security)
        for index, security in enumerate(issuer["securities"])
        if security.get("share_class") == proof["share_class"]
        and not (security.get("price_status") == "AVAILABLE" and security.get("price") is not None)
    ]
    require(
        len(candidates) == 1,
        "AMBIGUOUS_SECURITY_CLASS" if len(candidates) > 1 else "NO_MISSING_SECURITY_OF_CLASS",
    )
    target_index, target = candidates[0]
    require(target.get("share_class") == proof["share_class"], "SHARE_CLASS_MISMATCH")
    require(
        proof["listing_date"]
        == datetime.strptime(current["dateQuotation"], "%d/%m/%Y").date().isoformat(),
        "LISTING_DATE_MISMATCH",
    )
    listed = proof["listing_date"]
    require(listed <= reference, "LISTING_AFTER_REFERENCE")
    require(target["form_reference"] <= reference, "FORM_POSTDATES_REFERENCE")
    unit_evidence = issuer["historical_shares_unit_resolution"]["evidence"]
    require(
        unit_evidence["status"] == "VERIFIED"
        and unit_evidence["cnpj"] == issuer["cnpj"]
        and unit_evidence["reference_date"] == reference,
        "CAPITAL_IDENTITY_UNVERIFIED",
    )
    matching = [
        row for row in records if row["ticker"] == proof["ticker"] and row["market"] == "010"
    ]
    require(bool(matching), "NO_HISTORICAL_TRADES_FOR_PROVEN_SECURITY")
    require(all(row["isin"] == proof["isin"] for row in matching), "HISTORICAL_ISIN_CONFLICT")
    mapped = dict(
        target,
        ticker=proof["ticker"],
        isin=proof["isin"],
        valid_from=max(target["valid_from"], listed),
    )
    resolution = resolve(mapped, matching, reference)
    require(resolution["status"] == "RESOLVED", resolution["reason_code"])

    result = deepcopy(issuer)
    mapped.update(
        declared_ticker=target.get("declared_ticker") or target["ticker"],
        price_status="AVAILABLE",
        effective_market_date=resolution["effective_date"],
        price=resolution["price"],
        price_source_reference=resolution["source_reference"],
        identity_resolution={
            "policy_version": EXCHANGE_DIRECTORY_POLICY,
            "source_type": "B3_CVM_CNPJ_CLASS_ISIN_COTAHIST",
            "source_document": proof["source_file"],
            "source_document_sha256": proof["source_sha256"],
            "reference_date": resolution["effective_date"],
            "security_identifier": target["security_id"],
            "ticker": proof["ticker"],
            "isin": proof["isin"],
            "security_class": proof["share_class"],
            "price": resolution["price"],
            "price_field": "PREULT",
            "identity_resolution_method": "B3_CVM_CNPJ_CLASS_ISIN_COTAHIST",
            "confidence": "HIGH",
            "exchange_identity": deepcopy(proof),
            "current_directory": deepcopy(current),
            "price_evidence": resolution,
        },
    )
    result["securities"][target_index] = mapped
    required = set(market.get("price_readiness_tickers") or [])
    old_ticker = target["ticker"]
    if old_ticker in required:
        required.remove(old_ticker)
    required.add(proof["ticker"])
    available_tickers = {
        security["ticker"]
        for security in result["securities"]
        if security.get("price_status") == "AVAILABLE" and security.get("price") is not None
    }
    result_market = result["market_readiness"]
    result_market["price_readiness_tickers"] = sorted(required)
    price_ready = bool(required) and required <= available_tickers
    result_market["price_ready"] = price_ready
    result_market["status"] = "READY" if price_ready else "INSUFFICIENT_MARKET_DATA"
    result_market["reason_codes"] = [] if price_ready else ["NO_REFERENCE_PRICE"]
    if price_ready:
        result["data_readiness_status"] = "FULL_DATA_READY"
        result["eligibility_status"] = "ELIGIBLE"
        result["data_reason_codes"] = [
            code for code in result["data_reason_codes"] if code != "NO_REFERENCE_PRICE"
        ]
    return result
