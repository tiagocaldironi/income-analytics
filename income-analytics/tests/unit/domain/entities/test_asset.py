from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from income_analytics.domain.enums.asset_type import AssetType
from income_analytics.domain.value_objects.ticker import Ticker
from tests.unit.domain.builders import build_asset


def test_creates_asset_with_normalized_data_and_generated_metadata() -> None:
    asset = build_asset(
        name="  Petrobras PN  ",
        isin="  brpetracnpr6 ",
    )

    assert asset.ticker == Ticker("PETR4")
    assert asset.name == "Petrobras PN"
    assert asset.isin == "BRPETRACNPR6"
    assert asset.asset_type is AssetType.STOCK
    assert asset.active is True
    assert asset.id.version == 4
    assert asset.created_at.tzinfo is UTC
    assert asset.updated_at.tzinfo is UTC


def test_generates_different_ids_for_each_asset() -> None:
    assert build_asset().id != build_asset().id


def test_deactivate_marks_asset_inactive_and_updates_timestamp() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    asset = build_asset(created_at=timestamp, updated_at=timestamp)

    asset.deactivate()

    assert asset.active is False
    assert asset.updated_at >= timestamp


def test_deactivate_is_idempotent() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    asset = build_asset(active=False, created_at=timestamp, updated_at=timestamp)

    asset.deactivate()

    assert asset.active is False
    assert asset.updated_at == timestamp


@pytest.mark.parametrize(
    ("field", "value", "exception", "message"),
    [
        ("ticker", "PETR4", TypeError, "must be a Ticker"),
        ("name", 1, TypeError, "must be a string"),
        ("name", "   ", ValueError, "cannot be empty"),
        ("name", "A" * 201, ValueError, "more than 200"),
        ("asset_type", "STOCK", TypeError, "must be an AssetType"),
        ("currency", None, ValueError, "currency is required"),
        ("institution", None, ValueError, "institution is required"),
        ("isin", "   ", ValueError, "non-empty string"),
        ("isin", 123, ValueError, "non-empty string"),
        ("id", "not-a-uuid", TypeError, "must be a UUID"),
        ("active", 1, TypeError, "must be a bool"),
    ],
)
def test_rejects_invalid_asset_invariants(
    field: str, value: object, exception: type[Exception], message: str
) -> None:
    with pytest.raises(exception, match=message):
        build_asset(**{field: value})


def test_rejects_naive_timestamps() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        build_asset(created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1))


def test_rejects_timestamp_before_creation() -> None:
    created_at = datetime(2026, 1, 2, tzinfo=UTC)

    with pytest.raises(ValueError, match="cannot be before"):
        build_asset(created_at=created_at, updated_at=created_at - timedelta(seconds=1))


def test_accepts_a_caller_supplied_uuid() -> None:
    identifier = uuid4()

    assert build_asset(id=identifier).id == identifier
