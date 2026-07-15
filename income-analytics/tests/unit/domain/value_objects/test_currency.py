from dataclasses import FrozenInstanceError

import pytest

from income_analytics.domain.value_objects.currency import Currency


def test_should_create_currency() -> None:
    """
    Should create a Currency value object.
    """

    currency = Currency(
        code="BRL",
        name="Real Brasileiro",
        symbol="R$",
        decimal_places=2,
    )

    assert currency.code == "BRL"
    assert currency.name == "Real Brasileiro"
    assert currency.symbol == "R$"
    assert currency.decimal_places == 2


def test_should_raise_error_when_code_is_empty() -> None:
    """
    Should raise ValueError when currency code is empty.
    """

    with pytest.raises(ValueError):
        Currency(
            code="",
            name="Real Brasileiro",
            symbol="R$",
            decimal_places=2,
        )


def test_should_raise_error_when_name_is_empty() -> None:
    """
    Should raise ValueError when currency name is empty.
    """

    with pytest.raises(ValueError):
        Currency(
            code="BRL",
            name="",
            symbol="R$",
            decimal_places=2,
        )


def test_should_raise_error_when_symbol_is_empty() -> None:
    """
    Should raise ValueError when currency symbol is empty.
    """

    with pytest.raises(ValueError):
        Currency(
            code="BRL",
            name="Real Brasileiro",
            symbol="",
            decimal_places=2,
        )


def test_should_raise_error_when_decimal_places_is_negative() -> None:
    """
    Should raise ValueError when decimal places is negative.
    """

    with pytest.raises(ValueError):
        Currency(
            code="BRL",
            name="Real Brasileiro",
            symbol="R$",
            decimal_places=-1,
        )


def test_currency_should_be_immutable() -> None:
    """
    Currency must be immutable.
    """

    currency = Currency(
        code="BRL",
        name="Real Brasileiro",
        symbol="R$",
        decimal_places=2,
    )

    with pytest.raises(FrozenInstanceError):
        currency.code = "USD"


def test_two_currency_objects_with_same_values_should_be_equal() -> None:
    """
    Currency objects with same values should be equal.
    """

    first = Currency(
        code="BRL",
        name="Real Brasileiro",
        symbol="R$",
        decimal_places=2,
    )

    second = Currency(
        code="BRL",
        name="Real Brasileiro",
        symbol="R$",
        decimal_places=2,
    )

    assert first == second