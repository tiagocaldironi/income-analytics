"""Distribute a class-level simulated amount among existing assets only."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from income_analytics.domain.asset_allocation_policy import AssetAllocationPolicy
from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.domain.read_models.allocation_projection import AllocationProjection
from income_analytics.domain.read_models.asset_rebalancing_plan import (
    AssetRebalancingAllocation,
    AssetRebalancingPlan,
)
from income_analytics.domain.value_objects.money import Money


class AssetAllocationStrategy(StrEnum):
    PROPORTIONAL_TO_CURRENT_WEIGHT = "PROPORTIONAL_TO_CURRENT_WEIGHT"
    EQUAL_WEIGHT_WITHIN_CLASS = "EQUAL_WEIGHT_WITHIN_CLASS"
    TARGET_WEIGHT_WITHIN_CLASS = "TARGET_WEIGHT_WITHIN_CLASS"


class AssetRebalancingProjector:
    @classmethod
    def distribute(
        cls,
        allocation: AllocationProjection,
        asset_class: AssetClass,
        amount: Money,
        strategy: AssetAllocationStrategy,
        policy: AssetAllocationPolicy | None = None,
    ) -> tuple[tuple[str, Money], ...]:
        plan = cls.plan(allocation, asset_class, amount, strategy, policy)
        return tuple((item.ticker, item.allocated_amount) for item in plan.allocations)

    @classmethod
    def plan(
        cls,
        allocation: AllocationProjection,
        asset_class: AssetClass,
        amount: Money,
        strategy: AssetAllocationStrategy,
        policy: AssetAllocationPolicy | None = None,
    ) -> AssetRebalancingPlan:
        assets = [
            item
            for item in allocation.assets
            if not item.position.is_empty
            and item.position.asset.asset_class is asset_class
            and item.position.current_price
        ]
        if not assets or amount.is_zero:
            return AssetRebalancingPlan(
                asset_class=asset_class,
                class_amount=amount,
                strategy=strategy.value,
                allocations=(),
                unallocated_amount=amount,
            )
        if strategy is AssetAllocationStrategy.EQUAL_WEIGHT_WITHIN_CLASS:
            weights = [Decimal("1") / Decimal(len(assets))] * len(assets)
        elif strategy is AssetAllocationStrategy.TARGET_WEIGHT_WITHIN_CLASS:
            if policy is None:
                raise ValueError("A estratégia por alvo exige uma política-alvo por ativo.")
            policy_weights = [policy.target_for(item.position.asset) for item in assets]
            if any(weight is None for weight in policy_weights):
                raise ValueError("Todos os ativos da classe precisam ter peso-alvo.")
            weights = [weight for weight in policy_weights if weight is not None]
        else:
            total = sum((item.position.market_value.amount for item in assets), Decimal("0"))
            weights = [item.position.market_value.amount / total for item in assets]
        typed_weights = weights
        cents = amount.amount.quantize(Decimal("0.01"))
        provisional = [
            (cents * weight).quantize(Decimal("0.01"), rounding="ROUND_DOWN")
            for weight in typed_weights
        ]
        residual_cents = int((cents - sum(provisional, Decimal("0"))) * 100)
        for index in range(residual_cents):
            provisional[index % len(provisional)] += Decimal("0.01")
        class_value = sum((item.position.market_value.amount for item in assets), Decimal("0"))
        return AssetRebalancingPlan(
            asset_class=asset_class,
            class_amount=amount,
            strategy=strategy.value,
            allocations=tuple(
                AssetRebalancingAllocation(
                    ticker=str(item.position.asset.ticker),
                    allocated_amount=Money(value),
                    current_weight_within_class=item.position.market_value.amount / class_value,
                    simulated_weight_within_class=(item.position.market_value.amount + value)
                    / (class_value + cents),
                )
                for item, value in zip(assets, provisional, strict=True)
            ),
            unallocated_amount=Money(cents - sum(provisional, Decimal("0"))),
        )
