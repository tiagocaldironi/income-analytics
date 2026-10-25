"""Deterministic, bounded search over executable purchases in one frozen snapshot.

Only planning state changes. Quotes, ledger, policy and certified projectors are
never written. The primary objective is the official global class TV distance.
"""

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_DOWN, Decimal, localcontext

from income_analytics.domain.projectors.contribution_target_allocator import (
    ContributionTargetAllocator,
)

ZERO = Decimal(0)


@dataclass
class _State:
    quantities: dict
    values: dict
    principal: Decimal
    spent: Decimal
    objective: tuple


def allocate_quantities(
    instruments,
    class_values,
    class_targets,
    budget,
    unavailable=ZERO,
    *,
    strategy_assets=None,
    diagnostics=None,
    lookahead_depth=3,
    beam_width=12,
    max_evaluations=20000,
    max_iterations=None,
):
    """Re-evaluate ALL classes after every accepted candidate or bounded purchase bundle.

    Lexical objective: class TV, configured-asset TV, negative invested principal,
    costs. Thus no accepted state worsens global class distance; neutral distance
    may fund a perfectly aligned portfolio. Ties use sorted ticker/quantity pairs.

    An exploratory intermediate state may be worse; it is never committed alone.
    A bounded purchase bundle is accepted only when its combined objective improves. This
    escapes indivisible-lot traps without claiming an unbounded knapsack optimum.
    ``unavailable`` is a legacy reference amount, NOT a hard reservation.
    """
    with localcontext() as context:
        context.prec = 50
        return _allocate(
            instruments,
            class_values,
            class_targets,
            budget,
            strategy_assets=strategy_assets,
            diagnostics=diagnostics,
            lookahead_depth=lookahead_depth,
            beam_width=beam_width,
            max_evaluations=max_evaluations,
            max_iterations=max_iterations,
        )


def _allocate(
    instruments,
    class_values,
    class_targets,
    budget,
    *,
    strategy_assets,
    diagnostics,
    lookahead_depth,
    beam_width,
    max_evaluations,
    max_iterations,
):
    ordered = sorted(instruments, key=lambda item: item.ticker)
    by_ticker = {item.ticker: item for item in ordered}
    keys = sorted(set(class_values) | set(class_targets))
    targets = {key: class_targets.get(key, ZERO) for key in keys}
    values = {key: class_values.get(key, ZERO) for key in keys}
    assets = (
        strategy_assets
        if strategy_assets is not None
        else {item.ticker: {"current": item.current, "target": item.target} for item in ordered}
    )
    assets = sorted(assets.items())
    evaluated = 0
    limited = False
    trace = []
    initial_candidates = []
    limit = max_iterations if max_iterations is not None else min(256, max(32, 4 * len(ordered)))

    def objective(class_state, quantities, principal, spent):
        total = sum(class_state.values(), ZERO)
        distance = ContributionTargetAllocator.distance(class_state, targets)
        if distance is None:
            distance = sum(targets.values(), ZERO) / 2
        asset_distance = ZERO
        for ticker, asset in assets:
            item = by_ticker.get(ticker)
            value = asset["current"] + (
                quantities.get(ticker, ZERO) * item.unit_base if item else ZERO
            )
            weight = value / total if total else ZERO
            asset_distance += abs(weight - asset["target"]) / 2
        return distance, asset_distance, -principal, spent - principal

    def signature(state):
        return tuple(
            (ticker, quantity) for ticker, quantity in sorted(state.quantities.items()) if quantity
        )

    def rank(state):
        return state.objective, signature(state)

    def transition(state, item, quantity):
        nonlocal evaluated, limited
        if evaluated >= max_evaluations:
            limited = True
            return None
        evaluated += 1
        previous = state.quantities[item.ticker]
        extra_cost = item.cost(previous + quantity) - item.cost(previous)
        minimum = item.step if previous else item.minimum()
        if (
            quantity < minimum
            or quantity % item.step
            or extra_cost < 0
            or state.spent + extra_cost > budget
        ):
            return None
        quantities = dict(state.quantities)
        quantities[item.ticker] += quantity
        projected = dict(state.values)
        amount = quantity * item.unit_base
        projected[item.asset_class] = projected.get(item.asset_class, ZERO) + amount
        principal, spent = state.principal + amount, state.spent + extra_cost
        return _State(
            quantities,
            projected,
            principal,
            spent,
            objective(projected, quantities, principal, spent),
        )

    def proposals(state, item):
        previous = state.quantities[item.ticker]
        minimum = item.step if previous else item.minimum()
        maximum = item.affordable(budget - state.spent + item.cost(previous)) - previous
        if maximum < minimum or item.target <= 0:
            return ()
        quantities = {minimum, maximum}
        total = sum(state.values.values(), ZERO)
        crossings = []
        # Every class contributes a breakpoint, including dilution of OTHER classes.
        for key, target in targets.items():
            if key == item.asset_class:
                if target < 1:
                    crossings.append((target * total - state.values[key]) / (1 - target))
            elif target > 0:
                crossings.append(state.values[key] / target - total)
        if item.target < 1:
            own_value = item.current + previous * item.unit_base
            crossings.append((item.target * total - own_value) / (1 - item.target))
        crossings.append(max(ZERO, item.ideal - previous * item.unit_base))
        for amount in crossings:
            if amount <= 0:
                continue
            units = amount / item.unit_base / item.step
            for rounding in (ROUND_DOWN, ROUND_CEILING):
                quantity = units.to_integral_value(rounding=rounding) * item.step
                if minimum <= quantity <= maximum:
                    quantities.add(quantity)
        return sorted(quantities)

    def expand(state):
        results = []
        # Minimum proposals for every instrument precede optional quantity batches.
        pending = [(item, proposals(state, item)) for item in ordered]
        for index in range(max((len(quantities) for _, quantities in pending), default=0)):
            for item, quantities in pending:
                if index >= len(quantities):
                    continue
                candidate = transition(state, item, quantities[index])
                if candidate is not None:
                    results.append(candidate)
        return results

    quantities = {item.ticker: ZERO for item in ordered}
    state = _State(quantities, values, ZERO, ZERO, objective(values, quantities, ZERO, ZERO))
    initial = state.objective[0]
    initial_asset = state.objective[1]
    for _ in range(limit):
        if state.spent == budget or limited:
            break
        first = expand(state)
        if not trace:
            best_by_ticker = {}
            for candidate in first:
                ticker = next(
                    ticker
                    for ticker in candidate.quantities
                    if candidate.quantities[ticker] > state.quantities[ticker]
                )
                if ticker not in best_by_ticker or rank(candidate) < rank(best_by_ticker[ticker]):
                    best_by_ticker[ticker] = candidate
            for item in ordered:
                candidate = best_by_ticker.get(item.ticker)
                initial_candidates.append(
                    {
                        "ticker": item.ticker,
                        "asset_class": item.asset_class,
                        "minimum_cost": item.cost(item.minimum()),
                        "best_quantity": candidate.quantities[item.ticker] if candidate else ZERO,
                        "class_distance_after": candidate.objective[0] if candidate else None,
                        "reason": "ELIGIBLE_GLOBAL_IMPROVEMENT"
                        if candidate and candidate.objective < state.objective
                        else "GLOBAL_STRATEGY_LIMIT"
                        if candidate
                        else "MINIMUM_EXCEEDS_BALANCE",
                    }
                )
        choices = [candidate for candidate in first if candidate.objective < state.objective]
        frontier = sorted(first, key=rank)[:beam_width]
        for _depth in range(1, lookahead_depth):
            next_frontier = {}
            for candidate in frontier:
                if limited:
                    break
                for following in expand(candidate):
                    next_frontier[signature(following)] = following
                    if following.objective < state.objective:
                        choices.append(following)
            frontier = sorted(next_frontier.values(), key=rank)[:beam_width]
            if not frontier or limited:
                break
        if not choices:
            break
        best = min(choices, key=rank)
        assert best.objective[0] <= state.objective[0]
        trace.append(
            {
                "class_distance_before": state.objective[0],
                "class_distance_after": best.objective[0],
                "asset_distance_before": state.objective[1],
                "asset_distance_after": best.objective[1],
                "purchases": [
                    {
                        "ticker": ticker,
                        "quantity": best.quantities[ticker] - state.quantities[ticker],
                    }
                    for ticker in sorted(best.quantities)
                    if best.quantities[ticker] > state.quantities[ticker]
                ],
                "spent_after": best.spent,
                "remaining_after": budget - best.spent,
            }
        )
        state = best
    else:
        limited = state.spent < budget

    remaining = budget - state.spent
    discarded = []
    for item in ordered:
        previous = state.quantities[item.ticker]
        minimum = item.step if previous else item.minimum()
        minimum_cost = item.cost(previous + minimum) - item.cost(previous)
        discarded.append(
            {
                "ticker": item.ticker,
                "asset_class": item.asset_class,
                "minimum_additional_quantity": minimum,
                "minimum_additional_cost": minimum_cost,
                "reason": "MINIMUM_EXCEEDS_BALANCE"
                if minimum_cost > remaining
                else "SEARCH_LIMIT"
                if limited
                else "GLOBAL_STRATEGY_LIMIT",
            }
        )
    stop = (
        "FULLY_ALLOCATED"
        if remaining == 0
        else "SEARCH_LIMIT"
        if limited
        else (
            "NO_ELIGIBLE_ASSETS"
            if not ordered
            else "NO_AFFORDABLE_BUY"
            if all(item["minimum_additional_cost"] > remaining for item in discarded)
            else "NO_GLOBAL_IMPROVEMENT"
        )
    )
    if diagnostics is not None:
        diagnostics.update(
            {
                "objective": "CLASS_TV_THEN_ASSET_TV_THEN_PRINCIPAL_THEN_COST",
                "initial_class_distance": initial,
                "final_class_distance": state.objective[0],
                "initial_asset_distance": initial_asset,
                "final_asset_distance": state.objective[1],
                "evaluated_candidates": evaluated,
                "lookahead_depth": lookahead_depth,
                "beam_width": beam_width,
                "search_limited": limited,
                "stop_reason": stop,
                "iterations": trace,
                "discarded_candidates": discarded,
                "initial_candidates": initial_candidates,
            }
        )
    return state.quantities, remaining, len(trace)
