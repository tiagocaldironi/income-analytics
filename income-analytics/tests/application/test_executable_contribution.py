from datetime import date, timedelta
from decimal import Decimal as D
from types import SimpleNamespace as NS

import pytest

from income_analytics.application.executable_contribution import (
    Instrument,
    allocate_quantities,
    build_executable_plan,
)
from income_analytics.domain.enums.asset_class import AssetClass

TODAY = date(2026, 10, 24)


def instrument(ticker="A", price="34.50", **kwargs):
    values = dict(
        ticker=ticker,
        label=ticker,
        asset_class="FII",
        market="BR",
        currency="BRL",
        price=D(price),
        price_date=TODAY,
        price_source="test",
        price_timestamp=None,
        fx=D(1),
        fx_date=None,
        current=D(0),
        target=D(1),
        ideal=D(50),
    )
    values.update(kwargs)
    return Instrument(**values)


def fake_session(items, *, complete=True, class_weights=None, asset_weights=None, fx=()):
    # items: ticker, class, price or None, current value, quote age, currency
    assets, quotes, positions, valuations = {}, [], [], []
    for ticker, name, price, current, age, currency in items:
        kind = AssetClass(name)
        asset = NS(
            ticker=ticker,
            name=ticker,
            asset_class=kind,
            country="US" if currency == "USD" else "BR",
            currency=NS(code=currency),
        )
        assets[ticker] = asset
        positions.append(NS(asset=asset))
        valuations.append(
            NS(ticker=ticker, market_value_base=None if current is None else D(current))
        )
        if price is not None:
            quotes.append(
                NS(
                    asset=asset,
                    price=NS(amount=D(price)),
                    effective_date=TODAY - timedelta(days=age),
                    provider="test",
                    price_timestamp=None,
                )
            )
    if class_weights is None:
        classes = set(asset.asset_class for asset in assets.values())
        class_weights = {kind: D(1) / len(classes) for kind in classes}
    if asset_weights is None:
        asset_weights = {}
        for kind in class_weights:
            tickers = [ticker for ticker, asset in assets.items() if asset.asset_class == kind]
            asset_weights[kind] = {ticker: D(1) / len(tickers) for ticker in tickers}
    return NS(
        _assets=assets,
        _allocation_policy=NS(targets=class_weights),
        _asset_allocation_policy=NS(targets=asset_weights),
        projection=lambda **kw: NS(positions=positions),
        base_currency_valuation=lambda **kw: NS(
            positions=valuations, complete=complete, base_currency="BRL"
        ),
        _market_prices_for_projection=lambda **kw: quotes,
        _fx_rates=lambda *args: fx,
    )


def plan(items, budget="50", **kwargs):
    return build_executable_plan(fake_session(items), amount=D(budget), as_of=TODAY, **kwargs)


def test_50_at_34_50_buys_one_and_keeps_residual():
    result = plan([("A", "FII", "34.50", "0", 0, "BRL")])
    assert result["orders"][0]["quantity"] == 1
    assert result["total_estimated"] == D("34.50")
    assert result["residual_amount"] == D("15.50")


def test_50_at_60_cannot_buy_half_unit():
    result = plan([("A", "FII", "60", "0", 0, "BRL")])
    assert result["orders"] == []
    assert result["residual_amount"] == 50


def test_reallocates_rounded_residual_between_two_prices():
    result = plan([("A", "FII", "34.5", "0", 0, "BRL"), ("B", "FII", "15.5", "0", 0, "BRL")])
    assert {item["ticker"]: item["quantity"] for item in result["orders"]} == {"A": D(1), "B": D(1)}
    assert result["residual_amount"] == 0
    assert result["iterations"] >= 1


@pytest.mark.parametrize("kind", ["BRAZILIAN_STOCK", "BRAZILIAN_ETF", "FII"])
def test_brazilian_rules_reject_fractional_quantities(kind):
    with pytest.raises(ValueError, match="inteiras"):
        plan([("A", kind, "34.5", "0", 0, "BRL")], rules={"A": {"quantity_step": D(".5")}})


@pytest.mark.parametrize("kind", ["INTERNATIONAL", "INTERNATIONAL_ETF", "US_REIT"])
def test_foreign_fraction_requires_explicit_broker_support(kind):
    rate = NS(rate=D(5), effective_date=TODAY)
    session = fake_session([("A", kind, "20", "0", 0, "USD")], fx=[rate])
    result = build_executable_plan(session, amount=D(50), as_of=TODAY)
    assert result["orders"] == []
    result = build_executable_plan(
        session,
        amount=D(50),
        as_of=TODAY,
        rules={"A": {"fractional_supported": True, "quantity_precision": 3}},
    )
    order = result["orders"][0]
    assert order["quantity"] == D(".5")
    assert order["fx_rate"] == 5
    assert order["fx_date"] == TODAY
    assert order["estimated_total"] == 50


def test_crypto_decimal_precision_finishes_in_bounded_iterations():
    result = plan(
        [("BTC", "CRYPTO", "350000", "0", 0, "BRL")], rules={"BTC": {"quantity_precision": 10}}
    )
    quantity = result["orders"][0]["quantity"]
    assert quantity % D("1e-10") == 0
    assert result["total_estimated"] <= 50
    assert result["iterations"] <= 5


def test_fixed_income_minimum_increment_and_observed_quote():
    items = [("RDB", "FIXED_INCOME", "1", "0", 0, "BRL")]
    assert plan(items)["blocked"][0]["reason"] == "NEEDS_APPLICATION_TERMS"
    rules = {"RDB": {"minimum_amount": D(100), "amount_increment": D(25)}}
    result = plan(items, budget="130", rules=rules)
    assert result["total_estimated"] == 125
    assert result["residual_amount"] == 5
    assert plan(items, budget="50", rules=rules)["orders"] == []


@pytest.mark.parametrize("price,age,reason", [(None, 0, "MISSING_PRICE"), ("10", 8, "STALE_PRICE")])
def test_unavailable_quote_does_not_reserve_money_against_eligible_global_buys(price, age, reason):
    result = plan([("A", "FII", price, "0", age, "BRL"), ("B", "FII", "10", "0", 0, "BRL")])
    assert result["blocked"][0]["reason"] == reason
    assert result["unavailable_budget"] == 0
    assert result["blocked"][0]["reference_amount"] == 25
    assert result["total_estimated"] == 50
    assert result["orders"][0]["ticker"] == "B"
    assert (
        result["total_estimated"] + result["residual_amount"] + result["unavailable_budget"] == 50
    )


def test_stale_crypto_and_fx_never_create_orders():
    assert plan([("BTC", "CRYPTO", "10", "0", 2, "BRL")])["blocked"][0]["reason"] == "STALE_PRICE"
    session = fake_session(
        [("US", "INTERNATIONAL", "1", "0", 0, "USD")],
        fx=[NS(rate=D(5), effective_date=TODAY - timedelta(days=6))],
    )
    assert (
        build_executable_plan(session, amount=D(50), as_of=TODAY)["blocked"][0]["reason"]
        == "STALE_FX"
    )


def test_known_costs_and_rounding_never_exceed_budget():
    result = plan(
        [("A", "FII", "24", "0", 0, "BRL")],
        rules={"A": {"fixed_fee_base": D(3), "fee_rate": D(".01"), "costs_known": True}},
    )
    assert result["orders"][0]["quantity"] == 1
    assert result["total_estimated"] == D("27.24")
    assert result["estimated_costs"] == D("3.24")


def test_zero_budget_and_foreign_ticker_rejected():
    with pytest.raises(ValueError):
        plan([("A", "FII", "10", "0", 0, "BRL")], budget="0")
    with pytest.raises(ValueError, match="fora desta carteira"):
        plan([("A", "FII", "10", "0", 0, "BRL")], rules={"PRIVATE": {}})


def test_overweight_asset_not_bought_and_policy_not_mutated():
    session = fake_session(
        [("A", "FII", "1", "80", 0, "BRL"), ("B", "FII", "1", "20", 0, "BRL")],
        asset_weights={AssetClass.FII: {"A": D(".2"), "B": D(".8")}},
    )
    before = repr(session._asset_allocation_policy.targets)
    result = build_executable_plan(session, amount=D(20), as_of=TODAY)
    assert [item["ticker"] for item in result["orders"]] == ["B"]
    assert repr(session._asset_allocation_policy.targets) == before


def test_tie_is_lexical_and_input_order_independent():
    assets = [
        instrument("B", price="30", target=D(".5"), ideal=D(25)),
        instrument("A", price="30", target=D(".5"), ideal=D(25)),
    ]
    quantities, residual, _ = allocate_quantities(assets, {"FII": D(0)}, {"FII": D(1)}, D(50))
    assert quantities == {"A": D(1), "B": D(0)}
    assert residual == 20
    assert (
        allocate_quantities(list(reversed(assets)), {"FII": D(0)}, {"FII": D(1)}, D(50))[0]
        == quantities
    )


def test_missing_position_valuation_blocks_entire_objective():
    session = fake_session([("A", "FII", None, None, 0, "BRL")], complete=False)
    result = build_executable_plan(session, amount=D(50), as_of=TODAY)
    assert result["status"] == "INSUFFICIENT"
    assert result["orders"] == []
    assert result["unavailable_budget"] == 50


@pytest.mark.parametrize("budget", [".01", "1", "50", "1000", "1000000"])
def test_budget_invariant_across_price_and_fee_scales(budget):
    for price in [".00003451", ".99", "34.50", "100000"]:
        result = plan(
            [("A", "CRYPTO", price, "0", 0, "BRL")],
            budget=budget,
            rules={
                "A": {"quantity_precision": 8, "fixed_fee_base": D(".15"), "fee_rate": D(".002")}
            },
        )
        assert result["total_estimated"] <= D(budget)
        assert result["total_estimated"] + result["residual_amount"] + result[
            "unavailable_budget"
        ] == D(budget)
        for item in result["orders"]:
            assert item["quantity"] > 0
            assert item["quantity"] % item["quantity_step"] == 0


def test_timestamp_and_future_observations_are_not_accepted_as_fresh():
    from datetime import UTC, datetime

    session = fake_session([("A", "FII", "10", "0", 0, "BRL")])
    quotes = session._market_prices_for_projection()
    quotes[0].price_timestamp = datetime(2026, 10, 1, tzinfo=UTC)
    assert (
        build_executable_plan(session, amount=D(50), as_of=TODAY)["blocked"][0]["reason"]
        == "STALE_PRICE"
    )
    quotes[0].price_timestamp = None
    quotes[0].effective_date = TODAY + timedelta(days=1)
    assert (
        build_executable_plan(session, amount=D(50), as_of=TODAY)["blocked"][0]["reason"]
        == "FUTURE_PRICE"
    )


def test_no_asset_policy_does_not_invent_equal_weight_targets():
    session = fake_session([("A", "FII", "10", "0", 0, "BRL")], asset_weights={})
    result = build_executable_plan(session, amount=D(50), as_of=TODAY)
    assert result["orders"] == []
    assert result["blocked"][0]["reason"] == "NEEDS_ASSET_STRATEGY"
    assert result["unavailable_budget"] == 0
    assert result["residual_amount"] == 50


def test_missing_fx_and_inactive_asset_remain_non_simulable():
    session = fake_session([("A", "INTERNATIONAL", "10", "0", 0, "USD")])
    assert (
        build_executable_plan(session, amount=D(50), as_of=TODAY)["blocked"][0]["reason"]
        == "MISSING_FX"
    )
    session = fake_session([("A", "FII", "10", "0", 0, "BRL")])
    session._assets["A"].active = False
    assert (
        build_executable_plan(session, amount=D(50), as_of=TODAY)["blocked"][0]["reason"]
        == "INACTIVE_ASSET"
    )


def test_fixed_income_never_uses_a_derived_curve_as_purchase_quote():
    session = fake_session([("RDB", "FIXED_INCOME", None, "100", 0, "BRL")])
    observed = []

    def quotes(**kwargs):
        observed.append(kwargs)
        return []

    session._market_prices_for_projection = quotes
    result = build_executable_plan(
        session,
        amount=D(130),
        as_of=TODAY,
        rules={"RDB": {"minimum_amount": D(100), "amount_increment": D(25)}},
    )
    assert observed == [{"as_of": TODAY, "include_fixed_income": False}]
    assert result["orders"] == []
    assert result["blocked"][0]["reason"] == "MISSING_PRICE"
