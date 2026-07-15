from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from income_analytics.domain.value_objects.money import Money


def test_should_create_money() -> None:
    """Should create a Money object."""

    money = Money(Decimal("100.50"))

    assert money.amount == Decimal("100.50")


def test_should_raise_error_when_amount_is_not_decimal() -> None:
    """Should raise TypeError when amount is not Decimal."""

    with pytest.raises(TypeError):
        Money(100.50)


def test_money_should_be_immutable() -> None:
    """Money should be immutable."""

    money = Money(Decimal("100"))

    with pytest.raises(FrozenInstanceError):
        money.amount = Decimal("200")


def test_two_money_objects_with_same_amount_should_be_equal() -> None:
    """Money objects with same amount should be equal."""

    first = Money(Decimal("100"))
    second = Money(Decimal("100"))

    assert first == second