from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from income_analytics.domain.entities.institution import Institution


def test_creates_institution_with_optional_fields_and_utc_timestamps() -> None:
    institution = Institution(
        name="Itaú Unibanco",
        country="BR",
        website="https://www.itau.com.br",
    )

    assert institution.name == "Itaú Unibanco"
    assert institution.country == "BR"
    assert institution.website == "https://www.itau.com.br"
    assert institution.active is True
    assert institution.id.version == 4
    assert institution.created_at.tzinfo is UTC
    assert institution.updated_at.tzinfo is UTC


@pytest.mark.parametrize("name", ["", " Itaú", "Itaú "])
def test_rejects_empty_or_untrimmed_name(name: str) -> None:
    with pytest.raises(ValueError):
        Institution(name=name)


def test_deactivate_marks_institution_inactive_and_updates_timestamp() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    institution = Institution(name="BlackRock", created_at=timestamp, updated_at=timestamp)

    institution.deactivate()

    assert institution.active is False
    assert institution.updated_at >= timestamp


def test_rename_updates_name_and_timestamp() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    institution = Institution(name="Itaú", created_at=timestamp, updated_at=timestamp)

    institution.rename("Itaú Unibanco")

    assert institution.name == "Itaú Unibanco"
    assert institution.updated_at >= timestamp


def test_change_website_sets_and_clears_optional_website() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    institution = Institution(name="Vanguard", created_at=timestamp, updated_at=timestamp)

    institution.change_website("https://investor.vanguard.com")

    assert institution.website == "https://investor.vanguard.com"
    assert institution.updated_at >= timestamp

    institution.change_website(None)

    assert institution.website is None


def test_entities_with_the_same_id_are_equal_regardless_of_other_state() -> None:
    identifier = uuid4()
    first = Institution(name="Banco do Brasil", id=identifier)
    second = Institution(name="BB", country="BR", active=False, id=identifier)

    assert first == second
    assert first != Institution(name="Banco do Brasil")
    assert first != "Banco do Brasil"


@pytest.mark.parametrize(
    ("field", "value", "exception"),
    [
        ("name", 1, TypeError),
        ("country", "   ", ValueError),
        ("website", "   ", ValueError),
        ("website", 1, TypeError),
        ("id", "invalid", TypeError),
        ("active", 1, TypeError),
    ],
)
def test_rejects_invalid_fields(field: str, value: object, exception: type[Exception]) -> None:
    with pytest.raises(exception):
        Institution(name="Tesouro Nacional", **{field: value})


def test_rejects_invalid_timestamps() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Institution(
            name="Tesouro Nacional",
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

    created_at = datetime(2026, 1, 2, tzinfo=UTC)
    with pytest.raises(ValueError, match="cannot be before"):
        Institution(
            name="Tesouro Nacional",
            created_at=created_at,
            updated_at=created_at - timedelta(seconds=1),
        )


def test_mutations_with_the_same_value_do_not_change_timestamp() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    institution = Institution(
        name="Vanguard",
        website="https://investor.vanguard.com",
        active=False,
        created_at=timestamp,
        updated_at=timestamp,
    )

    institution.deactivate()
    institution.rename("Vanguard")
    institution.change_website("https://investor.vanguard.com")

    assert institution.updated_at == timestamp
