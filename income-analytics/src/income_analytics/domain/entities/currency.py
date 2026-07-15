"""Domain entity for a currency used by financial assets and events."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

_CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True, eq=False)
class Currency:
    """Currency identified by a stable ID and a unique ISO-style code."""

    code: str
    name: str
    symbol: str
    decimal_places: int
    id: UUID = field(default_factory=uuid4)
    active: bool = True
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        if not isinstance(self.code, str):
            raise TypeError("Currency code must be a string.")
        code = self.code.strip().upper()
        if not _CURRENCY_CODE_PATTERN.fullmatch(code):
            raise ValueError("Currency code must contain exactly three letters.")
        self._validate_required_text(self.name, "Currency name")
        self._validate_required_text(self.symbol, "Currency symbol")
        if not isinstance(self.decimal_places, int) or isinstance(self.decimal_places, bool):
            raise TypeError("Currency decimal_places must be an integer.")
        if self.decimal_places < 0:
            raise ValueError("Currency decimal_places must be greater than or equal to zero.")
        if not isinstance(self.id, UUID):
            raise TypeError("Currency id must be a UUID.")
        if not isinstance(self.active, bool):
            raise TypeError("Currency active flag must be a bool.")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("Currency timestamps must be timezone-aware.")
        if self.updated_at < self.created_at:
            raise ValueError("Currency updated_at cannot be before created_at.")

        self.code = code

    def deactivate(self) -> None:
        """Deactivate a currency while keeping historical records intact."""

        if self.active:
            self.active = False
            self.updated_at = _now_utc()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Currency):
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
