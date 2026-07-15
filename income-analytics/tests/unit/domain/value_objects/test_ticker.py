from dataclasses import FrozenInstanceError

import pytest

from income_analytics.domain.value_objects.ticker import Ticker


def test_normalizes_ticker_and_returns_its_value_as_text() -> None:
    ticker = Ticker("  petr4  ")

    assert ticker.value == "PETR4"
    assert str(ticker) == "PETR4"


@pytest.mark.parametrize("value", ["", "   "])
def test_rejects_empty_ticker(value: str) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        Ticker(value)


@pytest.mark.parametrize("value", ["PETR 4", "PETR/4", "A" * 21])
def test_rejects_ticker_outside_the_supported_format(value: str) -> None:
    with pytest.raises(ValueError, match="1 to 20"):
        Ticker(value)


def test_rejects_non_string_ticker() -> None:
    with pytest.raises(TypeError, match="must be a string"):
        Ticker(123)  # type: ignore[arg-type]


def test_is_immutable() -> None:
    ticker = Ticker("IVVB11")

    with pytest.raises(FrozenInstanceError):
        ticker.value = "PETR4"  # type: ignore[misc]
