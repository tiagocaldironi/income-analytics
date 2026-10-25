from copy import deepcopy
from decimal import Decimal as D

from income_analytics.application.executable_contribution import Instrument
from income_analytics.application.global_contribution_allocator import allocate_quantities


def item(ticker, kind, price, current=0, target=".5", **kwargs):
    from datetime import date

    values = dict(
        ticker=ticker,
        label=ticker,
        asset_class=kind,
        market="BR",
        currency="BRL",
        price=D(price),
        price_date=date(2026, 10, 25),
        price_source="fixture",
        price_timestamp=None,
        fx=D(1),
        fx_date=None,
        current=D(current),
        target=D(target),
        ideal=D(0),
    )
    values.update(kwargs)
    return Instrument(**values)


def test_global_reallocation_between_classes_and_recomputed_denominator():
    instruments = [item("A", "STOCK", "34.5"), item("B", "ETF", "15.5")]
    trace = {}
    quantities, remaining, iterations = allocate_quantities(
        instruments,
        {"STOCK": D(0), "ETF": D(0)},
        {"STOCK": D(".5"), "ETF": D(".5")},
        D(50),
        diagnostics=trace,
    )
    assert quantities == {"A": D(1), "B": D(1)}
    assert remaining == 0
    assert iterations >= 1
    assert trace["final_class_distance"] == D(".19")
    assert all(
        step["class_distance_after"] <= step["class_distance_before"]
        for step in trace["iterations"]
    )


def test_bounded_two_buy_search_beats_greedy_trap():
    instruments = [item("A", "STOCK", "40", 60), item("B", "ETF", "20", 40)]
    values, targets = {"STOCK": D(60), "ETF": D(40)}, {"STOCK": D(".5"), "ETF": D(".5")}
    greedy_trace, global_trace = {}, {}
    greedy, leftover, _ = allocate_quantities(
        instruments, values, targets, D(100), lookahead_depth=1, diagnostics=greedy_trace
    )
    assert greedy == {"A": D(0), "B": D(1)}
    assert leftover == 80
    quantities, remaining, _ = allocate_quantities(
        instruments, values, targets, D(100), diagnostics=global_trace
    )
    assert quantities == {"A": D(1), "B": D(3)}
    assert remaining == 0
    assert global_trace["final_class_distance"] == greedy_trace["final_class_distance"] == 0
    assert len(global_trace["iterations"][0]["purchases"]) == 2
    assert all(
        step["class_distance_after"] <= step["class_distance_before"]
        for step in global_trace["iterations"]
    )


def test_full_budget_available_despite_unavailable_monetary_reference():
    instruments = [
        item("ETF_A", "ETF", "112.84", 1000, ".075", ideal=D("493.41")),
        item("ETF_B", "ETF", "151.60", 500, ".025", ideal=D("33.78")),
        item("FOREIGN", "FOREIGN", "990", 1000, ".025", ideal=D("201.49")),
    ]
    values = {
        "ETF": D(1500),
        "FOREIGN": D(2000),
        "FIXED": D(30000),
        "CRYPTO": D(10000),
        "STOCK": D(25000),
        "FII": D(19500),
        "INT_ETF": D(12100),
    }
    targets = {
        "ETF": D(".1"),
        "FOREIGN": D(".05"),
        "FIXED": D(".2"),
        "CRYPTO": D(".05"),
        "STOCK": D(".25"),
        "FII": D(".2"),
        "INT_ETF": D(".15"),
    }
    trace = {}
    quantities, remaining, _ = allocate_quantities(
        instruments, values, targets, D(1000), D("271.32"), diagnostics=trace
    )
    assert quantities["FOREIGN"] == 1
    assert remaining == 10
    assert trace["final_class_distance"] < trace["initial_class_distance"]


def test_independent_of_input_and_class_presentation_order():
    instruments = [item("A", "STOCK", "40", 60), item("B", "ETF", "20", 40)]
    values = {"STOCK": D(60), "ETF": D(40)}
    targets = {"STOCK": D(".5"), "ETF": D(".5")}
    original = deepcopy((values, targets))
    first = {}
    second = {}
    result = allocate_quantities(instruments, values, targets, D(100), diagnostics=first)
    reversed_result = allocate_quantities(
        list(reversed(instruments)),
        dict(reversed(list(values.items()))),
        dict(reversed(list(targets.items()))),
        D(100),
        diagnostics=second,
    )
    assert result == reversed_result
    assert first == second
    assert (values, targets) == original


def test_affordable_buy_that_worsens_global_strategy_is_rejected():
    trace = {}
    quantities, remaining, _ = allocate_quantities(
        [item("A", "STOCK", "10", 50)],
        {"STOCK": D(50), "ETF": D(50)},
        {"STOCK": D(".5"), "ETF": D(".5")},
        D(10),
        diagnostics=trace,
    )
    assert quantities["A"] == 0
    assert remaining == 10
    assert trace["stop_reason"] == "NO_GLOBAL_IMPROVEMENT"
    assert trace["discarded_candidates"][0]["reason"] == "GLOBAL_STRATEGY_LIMIT"


def test_integer_units_fractional_compatibility_budget_and_known_costs():
    instruments = [
        item("A", "STOCK", "40", 60),
        item(
            "B",
            "ETF",
            "20",
            40,
            step=D(".01"),
            minimum_quantity=D(".01"),
            fixed_fee=D("1.23"),
            fee_rate=D(".003"),
        ),
    ]
    quantities, remaining, _ = allocate_quantities(
        instruments, {"STOCK": D(60), "ETF": D(40)}, {"STOCK": D(".5"), "ETF": D(".5")}, D(100)
    )
    assert quantities["A"] % 1 == 0
    assert quantities["B"] % D(".01") == 0
    total = sum(instrument.cost(quantities[instrument.ticker]) for instrument in instruments)
    assert total <= 100
    assert total + remaining == 100


def test_inevitable_residual_and_deterministic_termination():
    instruments = [item("A", "STOCK", "34.5", target="1")]
    trace = {}
    result = allocate_quantities(
        instruments, {"STOCK": D(0)}, {"STOCK": D(1)}, D("1000000000000"), diagnostics=trace
    )
    assert result[0]["A"] == D(28985507246)
    assert result[1] == D(13)
    assert result[2] <= 2
    assert trace["stop_reason"] == "NO_AFFORDABLE_BUY"
    assert trace["evaluated_candidates"] < 100
    assert result == allocate_quantities(
        instruments, {"STOCK": D(0)}, {"STOCK": D(1)}, D("1000000000000")
    )


def test_search_limit_is_explicit_and_never_called_inevitable_residual():
    trace = {}
    instruments = [item("A", "STOCK", "40", 60), item("B", "ETF", "20", 40)]
    quantities, remaining, _ = allocate_quantities(
        instruments,
        {"STOCK": D(60), "ETF": D(40)},
        {"STOCK": D(".5"), "ETF": D(".5")},
        D(100),
        diagnostics=trace,
        max_evaluations=1,
    )
    assert trace["search_limited"]
    assert trace["stop_reason"] == "SEARCH_LIMIT"
    assert (
        sum(instrument.cost(quantities[instrument.ticker]) for instrument in instruments)
        + remaining
        == 100
    )


def test_zero_target_never_bought_to_use_residual():
    quantities, remaining, _ = allocate_quantities(
        [item("OUTSIDE", "OTHER", "1", target="0")],
        {"OTHER": D(0), "STOCK": D(100)},
        {"OTHER": D(0), "STOCK": D(1)},
        D(50),
    )
    assert quantities["OUTSIDE"] == 0
    assert remaining == 50


def test_balanced_three_class_bundle_funds_without_transient_plan_regression():
    instruments = [
        item("A", "A", "10", 100, target=str(D(1) / 3)),
        item("B", "B", "10", 100, target=str(D(1) / 3)),
        item("C", "C", "10", 100, target=str(D(1) / 3)),
    ]
    values = {key: D(100) for key in "ABC"}
    targets = {key: D(1) / 3 for key in "ABC"}
    trace = {}
    quantities, remaining, _ = allocate_quantities(
        instruments, values, targets, D(30), diagnostics=trace
    )
    assert quantities == {key: D(1) for key in "ABC"}
    assert remaining == 0
    assert trace["final_class_distance"] <= trace["initial_class_distance"]
    assert len(trace["iterations"][0]["purchases"]) == 3


def test_dilution_of_other_classes_is_part_of_global_score():
    trace = {}
    _, remaining, _ = allocate_quantities(
        [item("STOCK", "STOCK", "20", 30)],
        {"FIXED": D(70), "STOCK": D(30)},
        {"FIXED": D(".5"), "STOCK": D(".5")},
        D(20),
        diagnostics=trace,
    )
    assert remaining == 0
    assert trace["initial_class_distance"] == D(".2")
    assert abs(trace["final_class_distance"] - D(1) / 12) < D("1e-25")
    assert trace["initial_candidates"][0]["reason"] == "ELIGIBLE_GLOBAL_IMPROVEMENT"
