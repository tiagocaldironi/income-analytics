"""Domain entity for an issuer or manager of financial assets."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True, eq=False)
class Institution:
    """Issuer or manager identified by a stable domain identity."""

    name: str
    country: str | None = None
    website: str | None = None
    id: UUID = field(default_factory=uuid4)
    active: bool = True
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        self._validate_name(self.name)
        self._validate_optional_text(self.country, "Institution country")
        self._validate_optional_text(self.website, "Institution website")
        if not isinstance(self.id, UUID):
            raise TypeError("Institution id must be a UUID.")
        if not isinstance(self.active, bool):
            raise TypeError("Institution active flag must be a bool.")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("Institution timestamps must be timezone-aware.")
        if self.updated_at < self.created_at:
            raise ValueError("Institution updated_at cannot be before created_at.")

    def deactivate(self) -> None:
        """Deactivate the institution while preserving its history."""

        if self.active:
            self.active = False
            self._touch()

    def rename(self, name: str) -> None:
        """Replace the institution name after validating its invariant."""

        self._validate_name(name)
        if self.name != name:
            self.name = name
            self._touch()

    def change_website(self, website: str | None) -> None:
        """Set or clear the optional public website."""

        self._validate_optional_text(website, "Institution website")
        if self.website != website:
            self.website = website
            self._touch()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Institution):
            return NotImplemented
        return self.id == other.id

    @staticmethod
    def _validate_name(name: str) -> None:
        if not isinstance(name, str):
            raise TypeError("Institution name must be a string.")
        if not name:
            raise ValueError("Institution name cannot be empty.")
        if name != name.strip():
            raise ValueError("Institution name cannot have leading or trailing spaces.")

    @staticmethod
    def _validate_optional_text(value: str | None, field_name: str) -> None:
        if value is None:
            return
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string when provided.")
        if not value.strip():
            raise ValueError(f"{field_name} cannot be blank when provided.")

    def _touch(self) -> None:
        self.updated_at = _now_utc()
