from decimal import Decimal
from itertools import product

from income_analytics.domain.projectors.contribution_target_allocator import (
    ContributionTargetAllocator,
)


def _distance(values: dict[str, Decimal], targets: dict[str, Decimal]) -> Decimal:
    total = sum(values.values(), Decimal("0"))
    return sum((abs(values[key] / total - targets[key]) for key in targets), Decimal("0")) / 2


def _after(current: dict[str, Decimal], allocations: dict[str, Decimal]) -> dict[str, Decimal]:
    return {key: value + allocations.get(key, Decimal("0")) for key, value in current.items()}


def test_intraclass_guided_beats_naive_split_when_misaligned() -> None:
    current = {"A": Decimal("70"), "B": Decimal("20"), "C": Decimal("10")}
    targets = {"A": Decimal(".5"), "B": Decimal(".3"), "C": Decimal(".2")}
    result = ContributionTargetAllocator.allocate(current, targets, Decimal("20"), key=str)
    assert result.allocations.get("A", Decimal("0")) == 0
    guided = _distance(_after(current, result.allocations), targets)
    naive = _distance(
        _after(current, {key: Decimal("20") * target for key, target in targets.items()}),
        targets,
    )
    assert guided <= naive


def test_aligned_intraclass_remains_aligned() -> None:
    current = {"A": Decimal("50"), "B": Decimal("30"), "C": Decimal("20")}
    targets = {"A": Decimal(".5"), "B": Decimal(".3"), "C": Decimal(".2")}
    result = ContributionTargetAllocator.allocate(current, targets, Decimal("10"), key=str)
    assert result.allocations == {
        "A": Decimal("5.00"),
        "B": Decimal("3.00"),
        "C": Decimal("2.00"),
    }
    assert _distance(_after(current, result.allocations), targets) == 0


def test_above_and_zero_target_assets_receive_nothing_and_new_asset_can_receive() -> None:
    current = {"A": Decimal("80"), "B": Decimal("20"), "C": Decimal("0")}
    targets = {"A": Decimal("0"), "B": Decimal(".5"), "C": Decimal(".5")}
    result = ContributionTargetAllocator.allocate(current, targets, Decimal("20"), key=str)
    assert result.allocations.get("A", Decimal("0")) == 0
    assert result.allocations["C"] > 0


def test_exhaustive_two_class_oracle_matches_allocator_minimum() -> None:
    current = {"A": Decimal("8"), "B": Decimal("2")}
    targets = {"A": Decimal(".5"), "B": Decimal(".5")}
    contribution = Decimal("2")
    result = ContributionTargetAllocator.allocate(current, targets, contribution, key=str)
    actual = _distance(_after(current, result.allocations), targets)
    exhaustive = min(
        _distance(
            _after(current, {"A": Decimal(step) / 10, "B": contribution - Decimal(step) / 10}),
            targets,
        )
        for step in range(21)
    )
    assert actual == exhaustive


def test_exhaustive_three_class_oracle_matches_allocator_minimum() -> None:
    current = {"A": Decimal("6"), "B": Decimal("3"), "C": Decimal("1")}
    targets = {"A": Decimal(".4"), "B": Decimal(".35"), "C": Decimal(".25")}
    contribution = Decimal("5")
    result = ContributionTargetAllocator.allocate(current, targets, contribution, key=str)
    actual = _distance(_after(current, result.allocations), targets)
    candidates = []
    for first, second in product(range(101), repeat=2):
        if first + second > 100:
            continue
        allocation = {
            "A": Decimal(first) / 20,
            "B": Decimal(second) / 20,
            "C": Decimal(100 - first - second) / 20,
        }
        candidates.append(_distance(_after(current, allocation), targets))
    assert actual == min(candidates)


def test_tie_break_and_rounding_are_deterministic() -> None:
    args = (
        {"B": Decimal("0"), "A": Decimal("0")},
        {"A": Decimal(".5"), "B": Decimal(".5")},
        Decimal(".01"),
    )
    results = [ContributionTargetAllocator.allocate(*args, key=str) for _ in range(5)]
    assert all(result == results[0] for result in results)
    assert results[0].allocations == {"A": Decimal(".01"), "B": Decimal("0.00")}
