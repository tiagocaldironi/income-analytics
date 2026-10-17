from decimal import Decimal

from scripts.audit_magic_formula_investable_universe_v6 import issuer_market_cap


def _issuer(market, securities):
    return {"market_readiness": market, "securities": securities}


def _security(share_class, price="10.00"):
    return {
        "share_class": share_class,
        "price_status": "AVAILABLE",
        "price": price,
        "effective_market_date": "2025-12-30",
    }


def test_market_cap_uses_only_document_resolved_normalized_shares():
    market = {
        "capital_ready": True,
        "quantity_unit": "UNIT",
        "unit_resolution_policy_version": "MAGIC_FORMULA_HISTORICAL_SHARES_UNIT_V1",
        "normalized_outstanding_by_class": {"ON": "4268779000", "PN": "0"},
        "raw_capital_quantities": {"ON": {"issued": "4539007", "treasury": "270228"}},
    }
    value, status = issuer_market_cap(_issuer(market, [_security("ON")]))
    assert value == Decimal("42687790000.00")
    assert status == "RESOLVED"


def test_market_cap_does_not_trust_raw_quantities_even_if_unit_says_unit():
    market = {
        "capital_ready": True,
        "quantity_unit": "UNIT",
        "raw_capital_quantities": {"ON": {"issued": "4539007", "treasury": "270228"}},
    }
    value, status = issuer_market_cap(_issuer(market, [_security("ON")]))
    assert value is None
    assert status == "CAPITAL_OR_SHARE_UNIT_UNRESOLVED"


def test_market_cap_requires_price_for_each_positive_share_class():
    market = {
        "capital_ready": True,
        "unit_resolution_policy_version": "MAGIC_FORMULA_HISTORICAL_SHARES_UNIT_V1",
        "normalized_outstanding_by_class": {"ON": "100", "PN": "100"},
    }
    value, status = issuer_market_cap(_issuer(market, [_security("ON")]))
    assert value is None
    assert status == "CLASS_PRICE_MISSING_OR_AMBIGUOUS"
