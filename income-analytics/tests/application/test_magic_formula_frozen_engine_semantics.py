from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from income_analytics.application.historical_shares_units import outstanding, resolve
from income_analytics.application.issuer_market_cap import (
    IssuerMarketCapService,
    NormalizedSecurityPrice,
    ShareClassCapital,
)
from income_analytics.application.magic_formula_eligibility_policy_v7 import (
    select_buyable_security,
)
from income_analytics.application.magic_formula_investable_universe import (
    structural_decision,
    user_policy_decision,
)
from income_analytics.application.magic_formula_screening import (
    MagicFormulaMethodologyPolicy,
    methodology_policy_fingerprint,
    methodology_policy_payload,
)
from income_analytics.infrastructure.magic_formula_historical_price_sources import (
    exact_price_candidate,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDENS_PATH = (
    ROOT
    / "docs/appendices/multiportfolio_v2_certification_closure/frozen_engine_semantic_goldens.json"
)
BASELINE_PATH = (
    ROOT / "docs/appendices/multiportfolio_v2_certification_closure/frozen_engine_baseline_v2.json"
)
GOLDENS = json.loads(GOLDENS_PATH.read_text(encoding="utf-8"))["goldens"]


@pytest.mark.parametrize("golden", GOLDENS, ids=lambda item: item["rule_id"])
def test_frozen_engine_semantic_golden(golden: dict) -> None:
    case = golden["input"]
    expected = golden["expected_behavior"]
    rule = golden["rule_id"]

    if rule in {"MF-FE-010-MARKET", "MF-FE-020-NO-MARKET-SUBSTITUTION"}:
        result = exact_price_candidate(case["identity"], case["records"], case["reference_date"])
        assert result["status"] == expected["status"]
        if result["status"] == "CANDIDATE":
            assert result["record"]["market_type"] == expected["market_type"]
            assert result["record"]["price"] == expected["price"]
        else:
            assert result["reason"] == expected["reason"]
    elif rule == "MF-FE-UNIT-ONE-SECURITY":
        result = select_buyable_security(case["candidates"])
        assert result.status == expected["status"]
        assert result.selected_security["ticker"] == expected["selected_ticker"]
        assert len(case["candidates"]) == expected["selected_security_count"]
        assert result.selected_security["share_class"] == "UNIT"
    elif rule == "MF-FE-CLASS-AGGREGATION":
        capital = tuple(
            ShareClassCapital(
                "issuer-1",
                f"security-{item['class']}",
                f"TEST{item['class']}",
                item["class"],
                Decimal(item["shares_outstanding"]),
                date(2025, 12, 30),
                "CVM fixture",
            )
            for item in case["capital"]
        )
        prices = tuple(
            NormalizedSecurityPrice(
                f"security-{item['class']}",
                f"TEST{item['class']}",
                date(2025, 12, 30),
                date(2025, 12, 30),
                Decimal(item["price"]),
                "BRL",
                "B3 fixture",
            )
            for item in case["capital"]
        )
        value, components = IssuerMarketCapService().calculate(capital, prices)
        assert str(value) == expected["issuer_market_cap"]
        assert len(components) == expected["components"]
        assert len({component["share_class"] for component in components}) == 2
    elif rule == "MF-FE-TREASURY-AND-UNIT-SCALE":
        issued, treasury = case["issued_raw"], case["treasury_raw"]
        fields = {
            "QT_ACAO_ORDIN_CAP_INTEGR": issued["ON"],
            "QT_ACAO_ORDIN_TESOURO": treasury["ON"],
            "QT_ACAO_PREF_CAP_INTEGR": issued["PN"],
            "QT_ACAO_PREF_TESOURO": treasury["PN"],
        }
        issuer = {"issuer_id": "issuer-1", "cnpj": "12345678000190", "cvm_code": "000001"}
        capital = {
            "DT_REFER": "2024-12-31",
            "VERSAO": "1",
            "source_reference": "fixture.csv|row=1",
            **fields,
        }
        evidence = {
            "status": "VERIFIED",
            "cnpj": issuer["cnpj"],
            "cvm_code": issuer["cvm_code"],
            "reference_date": capital["DT_REFER"],
            "version": capital["VERSAO"],
            "unit_label": case["quantity_unit"],
            "quantity_scale_code": "2",
            "source_reference": "fixture.xml|EscalaQtdAcoes",
            "quantities": fields,
        }
        result = resolve(issuer, capital, evidence)
        assert result["status"] == "RESOLVED"
        assert result["normalization_multiplier"] == case["multiplier"]
        assert outstanding(result) == expected["outstanding"]
    elif rule == "MF-FE-MISSING-CLASS-PRICE":
        capital = (
            ShareClassCapital(
                "issuer-1", "security-on", "TEST3", "ON", Decimal("100"), date(2025, 12, 30), "CVM"
            ),
            ShareClassCapital(
                "issuer-1", "security-pn", "TEST4", "PN", Decimal("50"), date(2025, 12, 30), "CVM"
            ),
        )
        prices = (
            NormalizedSecurityPrice(
                "security-on",
                "TEST3",
                date(2025, 12, 30),
                date(2025, 12, 30),
                Decimal("10"),
                "BRL",
                "B3",
            ),
        )
        with pytest.raises(ValueError, match=expected["status"]):
            IssuerMarketCapService().calculate(capital, prices)
    elif rule == "MF-FE-S4-INDEPENDENCE":
        result = select_buyable_security(case["candidates"])
        assert result.status == "RESOLVED"
        assert result.selected_security["ticker"] == expected["selected_ticker"]
        assert result.criteria[0:2] == ("valid_listing", expected["selection_metric"])
    elif rule == "MF-FE-POLICY-AND-RANKING-INVARIANTS":
        policy = MagicFormulaMethodologyPolicy()
        assert methodology_policy_fingerprint(policy) == (
            "96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac"
        )
        assert policy.market_type == expected["market_type"]
        assert policy.security_selection == expected["security_selection"]
        assert policy.minimum_market_cap_brl == expected["minimum_market_cap_brl"]
        payload = methodology_policy_payload(policy)
        assert (
            payload["methodology"]["liquidity"]["volume_is_minimum_threshold"]
            is expected["volume_is_minimum_threshold"]
        )
        assert structural_decision({"economic_sector": "Energia Elétrica"})["status"] == "PASS"
        assert (
            structural_decision({"economic_sector": "Bancos"})["status"] == "INELIGIBLE_STRUCTURAL"
        )
        assert (
            user_policy_decision({"economic_sector": "Comércio (Atacado e Varejo)"})["status"]
            == "PASS"
        )
        assert policy.retail_methodology_exclusion is expected["retail_exclusion"]
        assert policy.aviation_methodology_exclusion is expected["aviation_exclusion"]
        assert policy.utilities_new_exclusion is expected["new_utilities_exclusion"]
    else:
        raise AssertionError(f"Unhandled frozen-engine golden: {rule}")


def test_published_canonical_ranking_is_unchanged() -> None:
    snapshot_path = ROOT / "docs/appendices/magic_formula_v12_2/ranking_snapshot.json"
    snapshot_bytes = snapshot_path.read_bytes()
    assert hashlib.sha256(snapshot_bytes).hexdigest() == (
        "08d8776ee27af53c54c36efd9768fbc40e190f6f0ea0e0c18ec549199ff7cad0"
    )
    snapshot = json.loads(snapshot_bytes)
    gate = json.loads(
        (ROOT / "docs/appendices/magic_formula_v12_2/release_gate.json").read_text(encoding="utf-8")
    )
    reconciliation = json.loads(
        (
            ROOT
            / (
                "docs/appendices/multiportfolio_v2_certification_closure/"
                "magic_formula_reconciliation.json"
            )
        ).read_text(encoding="utf-8")
    )
    rows = snapshot["results"]
    assert (
        snapshot["policy_id"] == gate["policy_id"] == reconciliation["policy_id"] == "MF_BR_2027_V1"
    )
    assert snapshot["policy_hash"] == gate["policy_hash_after"] == reconciliation["policy_hash"]
    assert snapshot["ranking_snapshot_id"] == gate["snapshot_id"] == reconciliation["snapshot_id"]
    assert snapshot["ranking_hash"] == gate["ranking_hash"] == reconciliation["ranking_hash"]
    assert len(rows) == gate["ranked"] == reconciliation["ranked_company_count"] == 165
    assert len({row["company_id"] for row in rows}) == 165
    assert all(
        all(
            key in row
            for key in (
                "earnings_yield",
                "return_on_capital",
                "earnings_yield_rank",
                "return_on_capital_rank",
                "global_rank",
            )
        )
        and row["combined_score"] == row["earnings_yield_rank"] + row["return_on_capital_rank"]
        for row in rows
    )
    assert reconciliation["canonical_result_sha256"] == (
        "162c1b2f8856ae7d88cf5809d9418395464d0b2042bf6177fb48141e5b4fcf6a"
    )


def test_prospective_baseline_matches_current_engine_and_generator() -> None:
    from scripts.generate_magic_formula_frozen_engine_baseline import build_document

    document = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    payload = document["payload"]
    assert payload["baseline_id"] == "MF_BR_2027_V1_FROZEN_ENGINE_BASELINE_V2"
    first = build_document(ROOT, generated_at="2026-10-20T00:00:00+00:00")
    second = build_document(ROOT, generated_at="2026-10-20T00:00:00+00:00")
    assert first == second
    assert first["payload"] == payload
    assert first["payload_sha256"] == document["payload_sha256"]
    for item in payload["protected_files"]:
        actual = hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
        assert actual == item["sha256"], item["path"]
