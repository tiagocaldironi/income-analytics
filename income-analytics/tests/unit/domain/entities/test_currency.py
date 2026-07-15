from datetime import UTC, datetime
from uuid import uuid4

import pytest

from income_analytics.domain.entities.currency import Currency


def test_creates_normalized_currency_with_utc_metadata() -> None:
    currency = Currency(code=" brl ", name="Brazilian Real", symbol="R$", decimal_places=2)

    assert currency.code == "BRL"
    assert currency.name == "Brazilian Real"
    assert currency.symbol == "R$"
    assert currency.decimal_places == 2
    assert currency.id.version == 4
    assert currency.active is True
    assert currency.created_at.tzinfo is UTC
    assert currency.updated_at.tzinfo is UTC


@pytest.mark.parametrize("code", ["", "BR", "BRLL", "12A", "B R"])
def test_rejects_invalid_currency_code(code: str) -> None:
    with pytest.raises(ValueError, match="exactly three letters"):
        Currency(code=code, name="Brazilian Real", symbol="R$", decimal_places=2)


@pytest.mark.parametrize(
    ("field", "value", "exception"),
    [
        ("code", 1, TypeError),
        ("name", "", ValueError),
        ("name", " Real", ValueError),
        ("symbol", "", ValueError),
        ("symbol", " $", ValueError),
        ("decimal_places", -1, ValueError),
        ("decimal_places", 1.0, TypeError),
        ("decimal_places", True, TypeError),
    ],
)
def test_rejects_invalid_currency_data(
    field: str, value: object, exception: type[Exception]
) -> None:
    with pytest.raises(exception):
        data = {
            "code": "BRL",
            "name": "Brazilian Real",
            "symbol": "R$",
            "decimal_places": 2,
        }

        data[field] = value

        Currency(**data)


def test_deactivate_updates_state_and_timestamp() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    currency = Currency(
        code="USD",
        name="US Dollar",
        symbol="$",
        decimal_places=2,
        created_at=timestamp,
        updated_at=timestamp,
    )

    currency.deactivate()

    assert currency.active is False
    assert currency.updated_at >= timestamp


def test_currency_equality_is_based_on_identity() -> None:
    identifier = uuid4()

    assert Currency("USD", "US Dollar", "$", 2, id=identifier) == Currency(
        "BRL", "Brazilian Real", "R$", 2, id=identifier
    )


def test_inactive_currency_deactivation_is_idempotent() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    currency = Currency(
        "USD",
        "US Dollar",
        "$",
        2,
        active=False,
        created_at=timestamp,
        updated_at=timestamp,
    )

    currency.deactivate()

    assert currency.updated_at == timestamp
