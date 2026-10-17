"""Identity corrections must fail closed and preserve unrelated evidence."""

from copy import deepcopy

import pytest

from income_analytics.application.historical_security_identity import (
    EXCHANGE_DIRECTORY_POLICY,
    recover_price,
    recover_price_from_exchange_identity,
)


@pytest.fixture
def inputs():
    issuer = {
        "issuer_id": "issuer-a",
        "cnpj": "12345678000199",
        "cvm_code": "012345",
        "methodology_eligibility": "ELIGIBLE",
        "identity_status": "RESOLVED",
        "accounting_readiness": {"ready": True, "evidence": ["unchanged"]},
        "market_readiness": {
            "security_ready": True,
            "capital_ready": True,
            "price_ready": False,
            "normalized_outstanding_by_class": {"ON": "100"},
        },
        "data_reason_codes": ["NO_REFERENCE_PRICE"],
        "historical_shares_unit_resolution": {
            "evidence": {
                "status": "VERIFIED",
                "cnpj": "12345678000199",
                "reference_date": "2025-12-31",
            }
        },
        "securities": [
            {
                "issuer_id": "issuer-a",
                "security_id": "security-a",
                "ticker": "12345",
                "share_class": "ON",
                "form_reference": "2025-01-01",
                "valid_from": "2020-01-01",
                "valid_to": None,
                "source_reference": "fca|line=2",
            }
        ],
    }
    offer = {
        "schema_version": "B3_OFFER_IDENTITY_V1",
        "cnpj": "12345678000199",
        "ticker": "TEST3",
        "isin": "BRTESTACNOR1",
        "share_class": "ON",
        "document_date": "2019-12-01",
    }
    current = {
        "cnpj": "12345678000199",
        "codeCVM": "12345",
        "dateQuotation": "01/01/2020",
        "otherCodes": [{"code": "TEST3", "isin": "BRTESTACNOR1"}],
    }
    records = [
        {
            "ticker": "TEST3",
            "isin": "BRTESTACNOR1",
            "market": "010",
            "effective_date": "2025-12-30",
            "price": "5.67",
            "raw_price": "0000000000567",
            "currency": "R$",
            "source_reference": "cotahist|line=10",
        }
    ]
    return issuer, offer, current, records


def test_recovers_only_price_and_mapping_without_mutating_inputs(inputs):
    before = deepcopy(inputs)
    result = recover_price(*inputs, "2025-12-31")
    assert inputs == before
    assert result["accounting_readiness"] == before[0]["accounting_readiness"]
    assert (
        result["historical_shares_unit_resolution"]
        == before[0]["historical_shares_unit_resolution"]
    )
    assert result["securities"][0]["security_id"] == "security-a"
    assert result["securities"][0]["declared_ticker"] == "12345"
    assert result["securities"][0]["price"] == "5.67"
    assert result["data_readiness_status"] == "FULL_DATA_READY"


@pytest.mark.parametrize(
    "case,reason",
    [
        ("cnpj", "CNPJ_MISMATCH"),
        ("cvm", "CVM_MISMATCH"),
        ("future", "PROOF_POSTDATES_REFERENCE"),
        ("class", "SHARE_CLASS_MISMATCH"),
        ("event", "TICKER_HISTORY_REQUIRES_EVENT_EVIDENCE"),
        ("ambiguous", "AMBIGUOUS_CURRENT_IDENTITY"),
        ("isin", "HISTORICAL_ISIN_CONFLICT"),
        ("stale", "EFFECTIVE_DATE_GAP"),
        ("capital", "CAPITAL_IDENTITY_UNVERIFIED"),
    ],
)
def test_rejects_incomplete_or_conflicting_evidence(inputs, case, reason):
    issuer, offer, current, rows = inputs
    if case == "cnpj":
        current["cnpj"] = "different"
    if case == "cvm":
        current["codeCVM"] = "999"
    if case == "future":
        offer["document_date"] = "2026-01-01"
    if case == "class":
        offer["share_class"] = "PN"
    if case == "event":
        issuer["securities"][0]["ticker"] = "OLDX3"
    if case == "ambiguous":
        current["otherCodes"].append({"code": "TEST3", "isin": "BRTESTACNOR2"})
    if case == "isin":
        rows[0]["isin"] = "different"
    if case == "stale":
        rows[0]["effective_date"] = "2025-12-23"
    if case == "capital":
        issuer["historical_shares_unit_resolution"]["evidence"]["status"] = "UNKNOWN"
    with pytest.raises(ValueError, match=reason):
        recover_price(*inputs, "2025-12-31")


def test_duplicate_quotes_remain_ambiguous(inputs):
    inputs[3].append(deepcopy(inputs[3][0]))
    with pytest.raises(ValueError, match="AMBIGUOUS_REFERENCE_PRICE"):
        recover_price(*inputs, "2025-12-31")


@pytest.fixture
def exchange_inputs(inputs):
    issuer, _, _, rows = inputs
    issuer["securities"][0]["ticker"] = "4030"
    issuer["securities"][0]["security_id"] = "BR:4030"
    proof = {
        "schema_version": EXCHANGE_DIRECTORY_POLICY,
        "cnpj": "12345678000199",
        "cvm_code": "012345",
        "ticker": "TEST3",
        "isin": "BRTESTACNOR1",
        "share_class": "ON",
        "listing_date": "2020-01-01",
        "source_file": "directory.json",
        "source_sha256": "source-hash",
    }
    current = {
        "cnpj": "12345678000199",
        "codeCVM": "12345",
        "code": "TEST3",
        "dateQuotation": "01/01/2020",
        "otherCodes": [{"code": "TEST3", "isin": "BRTESTACNOR1"}],
        "institutionCommon": "BROKER",
        "institutionPreferred": "",
        "status": "A",
        "hasQuotation": "S",
        "market": "BOLSA",
    }
    return issuer, proof, current, rows


def test_exchange_identity_recovers_numeric_declared_ticker(exchange_inputs):
    issuer, proof, current, records = exchange_inputs
    before = deepcopy(exchange_inputs)

    result = recover_price_from_exchange_identity(issuer, proof, current, records, "2025-12-31")

    assert exchange_inputs == before
    assert result["securities"][0]["declared_ticker"] == "4030"
    assert result["securities"][0]["ticker"] == "TEST3"
    assert result["securities"][0]["isin"] == "BRTESTACNOR1"
    assert result["securities"][0]["price"] == "5.67"
    assert result["data_readiness_status"] == "FULL_DATA_READY"


@pytest.mark.parametrize(
    "case,reason",
    [
        ("cnpj", "CNPJ_MISMATCH"),
        ("cvm", "CVM_MISMATCH"),
        ("ambiguous", "AMBIGUOUS_CURRENT_IDENTITY"),
        ("class", "TICKER_ISIN_CLASS_MISMATCH"),
        ("listing", "LISTING_AFTER_REFERENCE"),
        ("isin", "HISTORICAL_ISIN_CONFLICT"),
        ("stale", "EFFECTIVE_DATE_GAP"),
    ],
)
def test_exchange_identity_rejects_ambiguous_or_undated_links(exchange_inputs, case, reason):
    issuer, proof, current, rows = exchange_inputs
    if case == "cnpj":
        current["cnpj"] = "different"
    if case == "cvm":
        current["codeCVM"] = "999"
    if case == "ambiguous":
        current["otherCodes"].append({"code": "TEST3", "isin": "BRTESTACNOR2"})
    if case == "class":
        proof["share_class"] = "PN"
        current["institutionCommon"] = ""
        current["institutionPreferred"] = "BROKER"
    if case == "listing":
        proof["listing_date"] = "2026-01-01"
        current["dateQuotation"] = "01/01/2026"
    if case == "isin":
        rows[0]["isin"] = "different"
    if case == "stale":
        rows[0]["effective_date"] = "2025-12-23"
    with pytest.raises(ValueError, match=reason):
        recover_price_from_exchange_identity(issuer, proof, current, rows, "2025-12-31")
