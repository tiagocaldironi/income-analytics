"""Read-only trading feasibility layered over the existing monetary allocator.

No quotes are fetched and no financial events or policies are written here.
"""

from dataclasses import asdict, dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_DOWN, Decimal, localcontext
from math import lcm

from income_analytics.application.base_currency_valuation import MAX_FX_STALE_AGE_DAYS
from income_analytics.application.global_contribution_allocator import allocate_quantities
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.projectors.contribution_target_allocator import (
    ContributionTargetAllocator,
)
from income_analytics.domain.projectors.hypothetical_portfolio_projector import (
    HypotheticalPortfolioProjector,
)

ZERO = Decimal("0")
CENT = Decimal(".01")
B3_CLASSES = {"BRAZILIAN_STOCK", "BRAZILIAN_ETF", "FII"}
FOREIGN_CLASSES = {"INTERNATIONAL", "INTERNATIONAL_ETF", "US_REIT"}
SUPPORTED = B3_CLASSES | FOREIGN_CLASSES | {"CRYPTO", "FIXED_INCOME"}


def floor_units(value, step):
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def ceil_units(value, step):
    return (value / step).to_integral_value(rounding=ROUND_CEILING) * step


def common_increment(left, right):
    """Least common multiple of finite decimal monetary increments."""
    scale = Decimal(10) ** max(0, -left.as_tuple().exponent, -right.as_tuple().exponent)
    return Decimal(lcm(int(left * scale), int(right * scale))) / scale


@dataclass(frozen=True, kw_only=True)
class Instrument:
    ticker: str
    label: str
    asset_class: str
    market: str
    currency: str
    price: Decimal
    price_date: date
    price_source: str
    price_timestamp: str | None
    fx: Decimal
    fx_date: date | None
    current: Decimal
    target: Decimal
    ideal: Decimal
    step: Decimal = Decimal("1")
    minimum_quantity: Decimal = Decimal("1")
    minimum_amount: Decimal = ZERO
    fixed_fee: Decimal = ZERO
    fee_rate: Decimal = ZERO
    costs_known: bool = False

    @property
    def unit_base(self):
        return self.price * self.fx

    def cost(self, quantity):
        if not quantity:
            return ZERO
        return (quantity * self.unit_base * (1 + self.fee_rate) + self.fixed_fee).quantize(
            CENT, rounding=ROUND_CEILING
        )

    def minimum(self):
        return ceil_units(
            max(self.step, self.minimum_quantity, self.minimum_amount / self.price), self.step
        )

    def affordable(self, available):
        if available <= self.fixed_fee:
            return ZERO
        return floor_units(
            (available - self.fixed_fee) / (self.unit_base * (1 + self.fee_rate)), self.step
        )


def build_executable_plan(session, *, amount, rules=None, as_of=None):
    """Adapter to an already owner-scoped PortfolioSession; reads existing data only."""
    with localcontext() as context:
        context.prec = 50
        return _build_executable_plan(session, amount=amount, rules=rules, as_of=as_of)


def _build_executable_plan(session, *, amount, rules=None, as_of=None):
    today = as_of or date.today()
    budget = Decimal(amount)
    if (
        not budget.is_finite()
        or budget <= 0
        or budget > Decimal("1000000000000")
        or budget != budget.quantize(CENT)
    ):
        raise ValueError("Informe um aporte positivo, em centavos, de até um trilhão.")
    policy = session._allocation_policy
    if policy is None:
        raise ValueError("Defina uma política de alocação-alvo primeiro.")
    rules = rules or {}
    if set(rules) - set(session._assets):
        raise ValueError("Regras de negociação incluem ativo fora desta carteira.")
    portfolio = session.projection(as_of=today)
    valuation = session.base_currency_valuation(as_of=today, projection=portfolio)
    base_values = {item.ticker: item.market_value_base for item in valuation.positions}
    class_values = {}
    for position in portfolio.positions:
        key = position.asset.asset_class.value
        value = base_values.get(str(position.asset.ticker))
        if value is not None:
            class_values[key] = class_values.get(key, ZERO) + value
    targets = {key.value: weight for key, weight in policy.targets.items()}
    monetary = ContributionTargetAllocator.allocate(class_values, targets, budget, key=str)
    quotes = {
        str(item.asset.ticker): item
        for item in session._market_prices_for_projection(as_of=today, include_fixed_income=False)
    }
    asset_policies = (
        session._asset_allocation_policy.targets if session._asset_allocation_policy else {}
    )
    candidates, blocked, options = [], [], []
    strategy_assets = {}
    unavailable = ZERO
    for asset_class, target in sorted(policy.targets.items(), key=lambda item: item[0].value):
        if target <= 0:
            continue
        class_budget = monetary.allocations.get(asset_class.value, ZERO)
        weights = asset_policies.get(asset_class)
        eligible = {
            ticker: asset
            for ticker, asset in session._assets.items()
            if asset.asset_class == asset_class
        }
        if not weights or set(weights) != set(eligible):
            blocked.append(
                {
                    "asset_class": asset_class.value,
                    "ticker": None,
                    "reason": "NEEDS_ASSET_STRATEGY",
                    "reserved_amount": ZERO,
                    "reference_amount": class_budget,
                }
            )
            unavailable += class_budget
            continue
        current = {ticker: base_values.get(ticker, ZERO) or ZERO for ticker in weights}
        seed = ContributionTargetAllocator.allocate(current, weights, class_budget, key=str)
        for ticker, weight in sorted(weights.items()):
            strategy_assets[ticker] = {"current": current[ticker], "target": target * weight}
            if weight <= 0:
                continue
            asset = eligible[ticker]
            name = asset_class.value
            rule = rules.get(ticker, {})
            fractional = rule.get("fractional_supported", False)
            precision = rule.get("quantity_precision", 8 if name == "CRYPTO" else 6)
            step = Decimal(
                rule.get("quantity_step")
                or (
                    "1"
                    if name in B3_CLASSES or name in FOREIGN_CLASSES and not fractional
                    else str(Decimal(10) ** -precision)
                )
            )
            minimum = Decimal(rule.get("minimum_quantity") or step)
            minimum_amount = Decimal(rule.get("minimum_amount") or "0")
            increment = Decimal(rule.get("amount_increment") or "0")
            fee = Decimal(rule.get("fixed_fee_base") or "0")
            rate = Decimal(rule.get("fee_rate") or "0")
            if (
                any(
                    not value.is_finite()
                    for value in (step, minimum, minimum_amount, increment, fee, rate)
                )
                or step <= 0
                or minimum < 0
                or min(minimum_amount, increment, fee, rate) < 0
                or rate > 1
            ):
                raise ValueError("Regras de negociação inválidas.")
            if not 0 <= precision <= 12 or step < Decimal("1e-12"):
                raise ValueError("Precisão de negociação inválida.")
            if (name == "CRYPTO" or name in FOREIGN_CLASSES and fractional) and step % (
                Decimal(10) ** -precision
            ):
                raise ValueError("O incremento não respeita a precisão informada.")
            if name in B3_CLASSES and (
                step != step.to_integral_value()
                or minimum != minimum.to_integral_value()
                or fractional
            ):
                raise ValueError("Ações, FIIs e ETFs brasileiros exigem unidades inteiras.")
            if (
                name in FOREIGN_CLASSES
                and not fractional
                and (step != step.to_integral_value() or minimum != minimum.to_integral_value())
            ):
                raise ValueError(
                    "Confirme o suporte a frações antes de usar quantidades decimais no exterior."
                )
            option = {
                "ticker": ticker,
                "label": asset.name,
                "asset_class": name,
                "currency": asset.currency.code,
                "fractional_supported": fractional,
                "quantity_precision": precision,
                "quantity_step": step,
                "minimum_quantity": minimum,
                "minimum_amount": minimum_amount,
                "amount_increment": increment,
                "fixed_fee_base": fee,
                "fee_rate": rate,
                "costs_known": rule.get("costs_known", False),
            }
            options.append(option)
            quote = quotes.get(ticker)
            reference_date = (
                min(quote.effective_date, quote.price_timestamp.date())
                if quote and quote.price_timestamp
                else quote.effective_date
                if quote
                else None
            )
            reason = None
            fx, fx_date = Decimal("1"), None
            if asset.currency.code != valuation.base_currency:
                observations = [
                    item
                    for item in session._fx_rates(asset.currency.code, valuation.base_currency)
                    if item.effective_date <= today and item.rate > 0
                ]
                observation = max(observations, key=lambda item: item.effective_date, default=None)
                if observation is None:
                    reason = "MISSING_FX"
                elif (today - observation.effective_date).days > MAX_FX_STALE_AGE_DAYS:
                    reason = "STALE_FX"
                else:
                    fx, fx_date = observation.rate, observation.effective_date
            if name not in SUPPORTED:
                reason = "UNSUPPORTED_MARKET"
            elif not getattr(asset, "active", True):
                reason = "INACTIVE_ASSET"
            elif name == "FIXED_INCOME" and (minimum_amount <= 0 or increment <= 0):
                reason = "NEEDS_APPLICATION_TERMS"
            elif quote is None:
                reason = "MISSING_PRICE"
            elif (today - reference_date).days > (1 if name == "CRYPTO" else 7):
                reason = "STALE_PRICE"
            elif (
                quote.effective_date > today
                or quote.price_timestamp
                and quote.price_timestamp.date() > today
            ):
                reason = "FUTURE_PRICE"
            if quote:
                option.update(
                    price=quote.price.amount,
                    price_date=quote.effective_date,
                    price_source=quote.provider,
                )
            if reason:
                reserved = seed.allocations.get(ticker, ZERO)
                unavailable += reserved
                blocked.append(
                    {
                        "ticker": ticker,
                        "asset_class": name,
                        "reason": reason,
                        "reserved_amount": ZERO,
                        "reference_amount": reserved,
                    }
                )
                continue
            if increment:
                step = common_increment(step * quote.price.amount, increment) / quote.price.amount
            candidates.append(
                Instrument(
                    ticker=ticker,
                    label=asset.name,
                    asset_class=name,
                    market="B3"
                    if name in B3_CLASSES
                    else "Cripto"
                    if name == "CRYPTO"
                    else asset.country,
                    currency=asset.currency.code,
                    price=quote.price.amount,
                    price_date=quote.effective_date,
                    price_source=quote.provider,
                    price_timestamp=quote.price_timestamp.isoformat()
                    if quote.price_timestamp
                    else None,
                    fx=fx,
                    fx_date=fx_date,
                    current=current[ticker],
                    target=target * weight,
                    ideal=seed.allocations.get(ticker, ZERO),
                    step=step,
                    minimum_quantity=minimum,
                    minimum_amount=minimum_amount,
                    fixed_fee=fee,
                    fee_rate=rate,
                    costs_known=rule.get("costs_known", False),
                )
            )
    if not valuation.complete:
        return {
            "kind": "EXECUTABLE_CONTRIBUTION",
            "status": "INSUFFICIENT",
            "issues": ["INCOMPLETE_VALUATION"],
            "budget": budget,
            "base_currency": valuation.base_currency,
            "orders": [],
            "blocked": blocked,
            "instruments": options,
            "unavailable_budget": budget,
            "residual_amount": ZERO,
            "total_estimated": ZERO,
        }
    diagnostics = {"initial_unavailable_reference": unavailable}
    quantities, residual, iterations = allocate_quantities(
        candidates,
        class_values,
        targets,
        budget,
        strategy_assets=strategy_assets,
        diagnostics=diagnostics,
    )
    # Missing inputs constrain eligibility, not an immutable slice of the budget.
    unavailable = ZERO
    principal = sum((quantities[item.ticker] * item.unit_base for item in candidates), ZERO)
    total = sum((item.cost(quantities[item.ticker]) for item in candidates), ZERO)
    wealth = sum(class_values.values(), ZERO)
    orders = []
    for item in candidates:
        quantity = quantities[item.ticker]
        if not quantity:
            continue
        value = quantity * item.unit_base
        orders.append(
            {
                "ticker": item.ticker,
                "label": item.label,
                "asset_class": item.asset_class,
                "market": item.market,
                "unit_price": item.price,
                "currency": item.currency,
                "price_date": item.price_date,
                "price_timestamp": item.price_timestamp,
                "price_source": item.price_source,
                "price_age_days": (
                    today - min(item.price_date, date.fromisoformat(item.price_timestamp[:10]))
                ).days
                if item.price_timestamp
                else (today - item.price_date).days,
                "quantity": quantity,
                "quantity_step": item.step,
                "native_amount": quantity * item.price,
                "estimated_principal": value,
                "estimated_total": item.cost(quantity),
                "estimated_costs": item.cost(quantity) - value,
                "costs_known": item.costs_known,
                "fx_rate": item.fx,
                "fx_date": item.fx_date,
                "weight_before": item.current / wealth if wealth else None,
                "weight_after": (item.current + value) / (wealth + principal)
                if wealth + principal
                else None,
                "target_weight": item.target,
                "reason": (
                    "GLOBAL_DISTANCE_REDUCED"
                    if diagnostics["final_class_distance"] < diagnostics["initial_class_distance"]
                    else "ASSET_DISTANCE_REDUCED"
                    if diagnostics["final_asset_distance"] < diagnostics["initial_asset_distance"]
                    else "GLOBAL_STRATEGY_PRESERVED"
                ),
            }
        )
    assert total + residual + unavailable == budget
    # Reuse the official scenario comparison, now with realizable purchase values.
    keys = tuple(
        sorted(
            set(policy.targets) | {AssetClass(key) for key in class_values},
            key=lambda key: key.value,
        )
    )
    before_values = {key: class_values.get(key.value, ZERO) for key in keys}
    after_values = dict(before_values)
    for order in orders:
        key = AssetClass(order["asset_class"])
        after_values[key] = after_values.get(key, ZERO) + order["estimated_principal"]
    before = HypotheticalPortfolioProjector._state(
        today, valuation.base_currency, before_values, policy, keys, "COMPLETE", ()
    )
    after = HypotheticalPortfolioProjector._state(
        today, valuation.base_currency, after_values, policy, keys, "COMPLETE", ()
    )
    comparison = asdict(HypotheticalPortfolioProjector._comparison(before, after, keys))
    return {
        "kind": "EXECUTABLE_CONTRIBUTION",
        "status": "PARTIAL" if blocked else "COMPLETE",
        "as_of": today,
        "base_currency": valuation.base_currency,
        "budget": budget,
        "orders": orders,
        "blocked": blocked,
        "instruments": options,
        "total_estimated": total,
        "invested_amount": principal,
        "estimated_costs": total - principal,
        "unavailable_budget": unavailable,
        "residual_amount": residual,
        "remaining_amount": budget - total,
        "iterations": iterations,
        "allocation_diagnostics": diagnostics,
        "residual_reasons": sorted(
            (
                {item["reason"] for item in diagnostics["discarded_candidates"]}
                | {item["reason"] for item in blocked}
            )
            if residual > 0
            else set()
        ),
        "comparison": comparison,
        "price_policy": {
            "listed_max_age_days": 7,
            "crypto_max_age_days": 1,
            "fx_max_age_days": MAX_FX_STALE_AGE_DAYS,
        },
        "limitations": [
            "EDUCATIONAL_ONLY",
            "DATED_PRICES_NOT_REALTIME",
            "BROKER_TERMS_NOT_VERIFIED",
            "UNKNOWN_COSTS_EXCLUDED"
            if any(not item.costs_known for item in candidates)
            else "USER_ESTIMATED_COSTS",
        ],
    }
