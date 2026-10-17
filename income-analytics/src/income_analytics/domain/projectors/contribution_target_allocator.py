"""Deterministic contribution-only minimisation of total-variation distance."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Generic, TypeVar

Key = TypeVar("Key")


@dataclass(frozen=True, slots=True)
class TargetContributionAllocation(Generic[Key]):
    allocations: dict[Key, Decimal]
    unallocated: Decimal


class ContributionTargetAllocator:
    """Allocate against positive targets on the resulting, not current, wealth.

    The L1 objective has multiple optima whenever the contribution cannot close every
    positive after-target gap.  Proportional allocation is our deterministic tie-break;
    remaining cents go to the lexical key order supplied by ``key``.
    """

    _CENT = Decimal("0.01")

    @staticmethod
    def distance(values: dict[Key, Decimal], targets: dict[Key, Decimal]) -> Decimal | None:
        total = sum(values.values(), Decimal("0"))
        if total <= 0 or set(values) != set(targets):
            return None
        return sum(
            (abs(values[item] / total - targets[item]) for item in targets), Decimal("0")
        ) / Decimal("2")

    @classmethod
    def allocate(
        cls,
        current_values: dict[Key, Decimal],
        target_weights: dict[Key, Decimal],
        contribution: Decimal,
        *,
        key: Callable[[Key], str],
    ) -> TargetContributionAllocation[Key]:
        if contribution < 0:
            raise ValueError("Aporte não pode ser negativo.")
        wealth = sum(current_values.values(), Decimal("0"))
        keys = set(current_values) | set(target_weights)
        gaps = {
            item: target_weights.get(item, Decimal("0")) * (wealth + contribution)
            - current_values.get(item, Decimal("0"))
            for item in keys
        }
        positive = {item: gap for item, gap in gaps.items() if gap > 0}
        total = sum(positive.values(), Decimal("0"))
        if not total:
            return TargetContributionAllocation({}, contribution)
        usable = min(contribution, total).quantize(cls._CENT, rounding=ROUND_DOWN)
        ordered = sorted(positive, key=key)
        allocations = {
            item: (usable * positive[item] / total).quantize(cls._CENT, rounding=ROUND_DOWN)
            for item in ordered
        }
        residual = usable - sum(allocations.values(), Decimal("0"))
        for item in ordered:
            if residual < cls._CENT:
                break
            allocations[item] += cls._CENT
            residual -= cls._CENT
        return TargetContributionAllocation(allocations, contribution - usable)
