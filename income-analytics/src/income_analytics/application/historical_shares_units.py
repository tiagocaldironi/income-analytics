"""Document-bound historical share units, never inferred from quantity or price."""

from copy import deepcopy
from decimal import Decimal, InvalidOperation

POLICY_VERSION = "MAGIC_FORMULA_HISTORICAL_SHARES_UNIT_V1"
UNIT_MULTIPLIERS = {"Unidade": Decimal(1), "Mil": Decimal(1000)}


def resolve(issuer, capital, evidence):
    result = dict(
        issuer_id=issuer["issuer_id"],
        reference_date=capital["DT_REFER"],
        policy_version=POLICY_VERSION,
        dataset="CVM_DFP_COMPOSICAO_CAPITAL",
        source_file=capital["source_reference"].split("|")[0],
        source_reference=capital["source_reference"],
        status="UNIT_UNRESOLVED",
        reason_code="MISSING_DOCUMENT_UNIT_EVIDENCE",
        resolution_method=None,
        raw_unit=None,
        normalization_multiplier=None,
        quantities=[],
        evidence=evidence,
    )
    if not evidence:
        return result
    if evidence.get("status") != "VERIFIED":
        result.update(
            status=evidence.get("status", "SOURCE_SCHEMA_ERROR"),
            reason_code=evidence.get("reason_code", "INVALID_EVIDENCE"),
        )
        return result
    if any(
        str(evidence.get(k)) != str(v)
        for k, v in dict(
            cnpj=issuer["cnpj"],
            cvm_code=issuer["cvm_code"],
            reference_date=capital["DT_REFER"],
            version=capital["VERSAO"],
        ).items()
    ):
        result.update(
            status="REVIEW_REQUIRED", reason_code="DOCUMENT_IDENTITY_DATE_VERSION_CONFLICT"
        )
        return result
    unit = evidence.get("unit_label")
    if unit not in UNIT_MULTIPLIERS:
        return result
    multiplier = UNIT_MULTIPLIERS[unit]
    result.update(
        raw_unit=dict(csv=None, xml_code=evidence["quantity_scale_code"], pdf_label=unit),
        normalization_multiplier=str(multiplier),
        resolution_method="EXPLICIT_SOURCE_UNIT",
    )
    for share_class, prefix in (("ON", "QT_ACAO_ORDIN_"), ("PN", "QT_ACAO_PREF_")):
        values = {}
        for kind, suffix in (("issued", "CAP_INTEGR"), ("treasury", "TESOURO")):
            field = prefix + suffix
            raw = capital.get(field)
            try:
                amount = Decimal(str(raw))
                source = Decimal(evidence["quantities"][field])
                if not amount.is_finite() or amount < 0:
                    raise ValueError("INVALID_QUANTITY")
                if amount != source:
                    raise ValueError("CSV_XML_QUANTITY_CONFLICT")
                normalized = amount * multiplier
                if normalized != normalized.to_integral_value():
                    raise ValueError("NON_INTEGRAL_NORMALIZED_QUANTITY")
            except (ValueError, InvalidOperation, KeyError):
                result.update(
                    status="REVIEW_REQUIRED", reason_code="INVALID_OR_CONFLICTING_QUANTITY"
                )
                return result
            values[kind] = normalized
            result["quantities"].append(
                dict(
                    issuer_id=issuer["issuer_id"],
                    share_class=share_class,
                    quantity_kind=kind,
                    raw_quantity=raw,
                    raw_unit_metadata=result["raw_unit"],
                    normalization_multiplier=str(multiplier),
                    normalized_quantity=str(int(normalized)),
                    reference_date=capital["DT_REFER"],
                    policy_version=POLICY_VERSION,
                    resolution_method="EXPLICIT_SOURCE_UNIT",
                    dataset=result["dataset"],
                    source_file=result["source_file"],
                    source_reference=result["source_reference"],
                    unit_source_reference=evidence["source_reference"],
                )
            )
        if values["treasury"] > values["issued"]:
            result.update(status="REVIEW_REQUIRED", reason_code="TREASURY_EXCEEDS_ISSUED")
            return result
    result.update(
        status="RESOLVED",
        reason_code=None,
        source_precision="THOUSAND_SHARES" if unit == "Mil" else "SINGLE_SHARE",
        confidence="EXPLICIT_DOCUMENT_METADATA_AND_PDF_LABEL",
    )
    return result


def outstanding(resolution):
    if resolution["status"] != "RESOLVED":
        raise ValueError("UNIT_RESOLUTION_REQUIRED")
    return {
        share_class: str(
            int(
                next(
                    Decimal(q["normalized_quantity"])
                    for q in resolution["quantities"]
                    if q["share_class"] == share_class and q["quantity_kind"] == "issued"
                )
                - next(
                    Decimal(q["normalized_quantity"])
                    for q in resolution["quantities"]
                    if q["share_class"] == share_class and q["quantity_kind"] == "treasury"
                )
            )
        )
        for share_class in ("ON", "PN")
    }


def apply_readiness(issuers, resolutions):
    """Reclassify readiness only; preserve accounting, securities and canonical evidence."""
    result = deepcopy(issuers)
    for issuer in result:
        resolution = resolutions.get(issuer["issuer_id"])
        if resolution is None or issuer["methodology_eligibility"] != "ELIGIBLE":
            continue
        issuer["historical_shares_unit_resolution"] = resolution
        if "UNIT_UNRESOLVED" not in issuer["data_reason_codes"]:
            continue
        market = issuer["market_readiness"]
        if resolution["status"] != "RESOLVED":
            if resolution["status"] in ("REVIEW_REQUIRED", "SOURCE_SCHEMA_ERROR"):
                issuer["data_readiness_status"] = "REVIEW_REQUIRED"
                issuer["eligibility_status"] = "REVIEW_REQUIRED"
                issuer["data_reason_codes"] = sorted(
                    set(issuer["data_reason_codes"] + [resolution["reason_code"]])
                )
            continue
        for target, key in ((issuer, "data_reason_codes"), (market, "reason_codes")):
            target[key] = [r for r in target[key] if r != "UNIT_UNRESOLVED"]
        reasons = issuer["data_reason_codes"]
        market["capital_ready"] = not any(
            r in reasons
            for r in (
                "NO_CAPITAL_DATA",
                "INVALID_CAPITAL_DATA",
                "AMBIGUOUS_CAPITAL_DATA",
                "TEMPORAL_CONFLICT",
                "UNRESOLVED_IDENTITY",
            )
        )
        market["quantity_unit"] = "UNIT"
        market["normalized_outstanding_by_class"] = outstanding(resolution)
        market["unit_resolution_policy_version"] = POLICY_VERSION
        market["status"] = (
            "TEMPORAL_CONFLICT"
            if "TEMPORAL_CONFLICT" in reasons
            else "SECURITY_UNRESOLVED"
            if not market["security_ready"]
            else "INSUFFICIENT_MARKET_DATA"
            if not market["price_ready"]
            else "RESOLVABLE"
            if market["capital_ready"]
            else "DATA_GAP"
        )
        full = (
            issuer["identity_status"] == "RESOLVED"
            and issuer["accounting_readiness"]["ready"]
            and all(market[k] for k in ("security_ready", "capital_ready", "price_ready"))
        )
        review = issuer["data_readiness_status"] == "REVIEW_REQUIRED"
        issuer["data_readiness_status"] = (
            "FULL_DATA_READY" if full else "REVIEW_REQUIRED" if review else "DATA_GAP"
        )
        issuer["eligibility_status"] = "ELIGIBLE" if full else issuer["data_readiness_status"]
    return result
