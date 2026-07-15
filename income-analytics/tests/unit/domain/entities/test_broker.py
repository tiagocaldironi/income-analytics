from datetime import UTC, datetime
from uuid import uuid4

import pytest

from income_analytics.domain.entities.broker import Broker


def test_creates_broker_with_its_own_identity_and_utc_timestamps() -> None:
    broker = Broker(name="XP", country="BR", website="https://www.xpi.com.br")

    assert broker.name == "XP"
    assert broker.country == "BR"
    assert broker.website == "https://www.xpi.com.br"
    assert broker.active is True
    assert broker.id.version == 4
    assert broker.created_at.tzinfo is UTC
    assert broker.updated_at.tzinfo is UTC


@pytest.mark.parametrize(
    ("field", "value", "exception"),
    [
        ("name", "", ValueError),
        ("name", " XP", ValueError),
        ("country", "", ValueError),
        ("country", 1, TypeError),
        ("website", "   ", ValueError),
    ],
)
def test_rejects_invalid_broker_data(field: str, value: object, exception: type[Exception]) -> None:
    with pytest.raises(exception):
        data = {
            "name": "XP",
            "country": "BR",
        }

        data[field] = value

        Broker(**data)


def test_rename_updates_name_and_timestamp() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    broker = Broker(name="Nu Invest", country="BR", created_at=timestamp, updated_at=timestamp)

    broker.rename("Nubank")

    assert broker.name == "Nubank"
    assert broker.updated_at >= timestamp


def test_deactivate_updates_state_and_timestamp() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    broker = Broker(name="BTG", country="BR", created_at=timestamp, updated_at=timestamp)

    broker.deactivate()

    assert broker.active is False
    assert broker.updated_at >= timestamp


def test_broker_equality_is_based_only_on_identity() -> None:
    identifier = uuid4()

    assert Broker(name="XP", country="BR", id=identifier) == Broker(
        name="Clear", country="BR", active=False, id=identifier
    )
    assert Broker(name="XP", country="BR") != Broker(name="XP", country="BR")


def test_rename_and_deactivate_are_idempotent() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    broker = Broker(
        name="Inter",
        country="BR",
        active=False,
        created_at=timestamp,
        updated_at=timestamp,
    )

    broker.rename("Inter")
    broker.deactivate()

    assert broker.updated_at == timestamp
