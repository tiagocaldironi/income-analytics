"""Domain entity for a broker that intermediates financial operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True, eq=False)
class Broker:
    """Financial intermediary; it is never the issuer of an asset."""

    name: str
    country: str
    website: str | None = None
    id: UUID = field(default_factory=uuid4)
    active: bool = True
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        self._validate_required_text(self.name, "Broker name")
        self._validate_required_text(self.country, "Broker country")
        self._validate_optional_text(self.website, "Broker website")
        if not isinstance(self.id, UUID):
            raise TypeError("Broker id must be a UUID.")
        if not isinstance(self.active, bool):
            raise TypeError("Broker active flag must be a bool.")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("Broker timestamps must be timezone-aware.")
        if self.updated_at < self.created_at:
            raise ValueError("Broker updated_at cannot be before created_at.")

    def rename(self, name: str) -> None:
        """Rename the broker while preserving its identity."""

        self._validate_required_text(name, "Broker name")
        if self.name != name:
            self.name = name
            self._touch()

    def deactivate(self) -> None:
        """Deactivate the broker without deleting its historical data."""

        if self.active:
            self.active = False
            self._touch()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Broker):
            return NotImplemented
        return self.id == other.id

    @staticmethod
    def _validate_required_text(value: str, field_name: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string.")
        if not value:
            raise ValueError(f"{field_name} cannot be empty.")
        if value != value.strip():
            raise ValueError(f"{field_name} cannot have leading or trailing spaces.")

    @staticmethod
    def _validate_optional_text(value: str | None, field_name: str) -> None:
        if value is None:
            return
        Broker._validate_required_text(value, field_name)

    def _touch(self) -> None:
        self.updated_at = _now_utc()
