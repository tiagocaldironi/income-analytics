"""Historical price contract and disjoint coverage arithmetic."""

import json
from decimal import Decimal

import pytest

from income_analytics.application.historical_price import POLICY_VERSION, gap_analysis, resolve


def security(**changes):
    return dict(
        issuer_id="issuer",
        security_id="security",
        ticker="OLD3",
        share_class="ON",
        valid_from="2020-01-01",
        valid_to=None,
        source_reference="FCA|line=1",
        **changes,
    )


def quote(day="2025-12-30", **changes):
    return (
        dict(
            ticker="OLD3",
            effective_date=day,
            price="32.57",
            raw_price="0000000003257",
            currency="R$",
            source_reference="archive.ZIP|source.TXT|line=10",
        )
        | changes
    )


def test_previous_day_keeps_identity_decimal_and_lineage():
    result = resolve(security(), [quote()], "2025-12-31")
    assert result["requested_date"] == "2025-12-31"
    assert result["effective_date"] == "2025-12-30"
    assert Decimal(result["price"]) == Decimal("32.57")
    assert result["resolution_method"] == "PREVIOUS_TRADING_DAY_BY_POLICY"
    assert result["source_reference"] == quote()["source_reference"]
    assert result["policy_version"] == POLICY_VERSION


def test_exact_date_and_input_order():
    records = [quote("2025-12-29"), quote()]
    assert resolve(security(), records, "2025-12-30") == resolve(
        security(), records[::-1], "2025-12-30"
    )
    assert resolve(security(), records, "2025-12-30")["resolution_method"] == "EXACT_COTAHIST_DATE"


@pytest.mark.parametrize("record", [quote("2026-01-02"), quote("2025-12-23"), quote(ticker="NEW3")])
def test_no_future_stale_or_current_ticker_proxy(record):
    result = resolve(security(), [record], "2025-12-31")
    assert result["status"] == "DATA_GAP"
    assert result["price"] is None


@pytest.mark.parametrize("field,value", [("valid_from", "2026-01-01"), ("valid_to", "2025-12-29")])
def test_temporal_security_contract(field, value):
    result = resolve(security() | {field: value}, [quote()], "2025-12-31")
    assert result["reason_code"] == "SECURITY_NOT_ACTIVE_AT_REFERENCE_DATE"


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity", "invalid", None])
def test_invalid_price_does_not_resolve(value):
    assert resolve(security(), [quote(price=value)], "2025-12-31")["status"] != "RESOLVED"


def test_ambiguous_records_fail_closed():
    result = resolve(security(), [quote(), quote(price="42")], "2025-12-31")
    assert result["reason_code"] == "AMBIGUOUS_REFERENCE_PRICE"


def test_reversed_validity_requires_review():
    result = resolve(
        security() | {"valid_from": "2025-12-30", "valid_to": "2025-12-29"},
        [quote()],
        "2025-12-31",
    )
    assert result["reason_code"] == "TEMPORAL_CONFLICT"


def test_missing_source_distinct_from_missing_record():
    assert (
        resolve(security(), [], "2025-12-31", source_available=False)["reason_code"]
        == "SOURCE_FILE_UNAVAILABLE"
    )
    assert resolve(security(), [], "2025-12-31")["reason_code"] == "PRICE_RECORD_NOT_FOUND"


def test_gap_intersections_and_marginal_gain_are_distinct():
    def issuer(price=True, accounting=True, capital=True):
        full = price and accounting and capital
        return dict(
            methodology_eligibility="ELIGIBLE",
            identity_status="RESOLVED",
            accounting_readiness={"ready": accounting},
            market_readiness=dict(price_ready=price, security_ready=True, capital_ready=capital),
            data_readiness_status="FULL_DATA_READY" if full else "DATA_GAP",
        )

    result = gap_analysis(
        [
            issuer(),
            issuer(False),
            issuer(False, False),
            issuer(False, True, False),
            issuer(True, False),
        ]
    )
    assert sum(result["intersections"].values()) == 5
    assert result["price_only_blockers"] == 1
    assert result["max_full_data_ready_after_price"] == 2
    assert result["intersections"]["PRICE + ACCOUNTING"] == 1
    assert json.loads(json.dumps(result)) == result


def test_security_classes_do_not_borrow_each_others_price():
    on = resolve(security(), [quote()], "2025-12-31")
    pn = resolve(
        security() | {"security_id": "pn", "ticker": "OLD4", "share_class": "PN"},
        [quote()],
        "2025-12-31",
    )
    assert on["status"] == "RESOLVED"
    assert pn["price"] is None
    assert pn["status"] == "DATA_GAP"
    assert on["security_id"] != pn["security_id"]


def test_required_preferred_class_without_price_blocks_issuer_readiness():
    from tests.application.test_magic_formula_universe import evaluate, synthetic

    sources = synthetic()
    sources[1].append(
        dict(sources[1][0], Codigo_Negociacao="EXMP4", Valor_Mobiliario="Ações Preferenciais")
    )
    sources[3][0]["QT_ACAO_PREF_CAP_INTEGR"] = "5"
    issuer = evaluate(sources)[0]
    assert issuer["market_readiness"]["price_ready"] is False
    assert "NO_REFERENCE_PRICE" in issuer["data_reason_codes"]
    sources[4].append(dict(sources[4][0], ticker="EXMP4"))
    assert evaluate(sources)[0]["market_readiness"]["price_ready"] is True


def test_price_policy_and_lineage_survive_new_database_connection(tmp_path):
    from income_analytics.application.magic_formula_universe import coverage
    from income_analytics.infrastructure.magic_formula_universe_repository import (
        MagicFormulaUniverseRepository,
    )

    issuers = []
    resolution = resolve(security(), [quote()], "2025-12-31")
    document = dict(
        universe_snapshot_id="price-contract",
        reference_date="2025-12-31",
        universe_policy_version="test",
        created_at="test",
        universe_type="CANDIDATE_PUBLISHABLE_UNIVERSE",
        issuers=issuers,
        coverage=coverage(issuers),
        price_resolution=resolution,
        tool_status="VALIDATION_REQUIRED",
        ranking_status="INACTIVE",
    )
    database = tmp_path / "prices.db"
    repository = MagicFormulaUniverseRepository(database)
    repository.initialize()
    repository.save(document)
    del repository
    result = MagicFormulaUniverseRepository(database).read("price-contract")
    assert result == document
    assert result["price_resolution"]["policy_version"] == POLICY_VERSION
    assert result["price_resolution"]["source_reference"] == quote()["source_reference"]
    assert result["ranking_status"] == "INACTIVE"
