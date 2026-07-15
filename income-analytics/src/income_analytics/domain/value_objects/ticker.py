"""Value object that identifies a traded asset."""

from __future__ import annotations

import re
from dataclasses import dataclass

_TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,19}$")


@dataclass(frozen=True, slots=True)
class Ticker:
    """Immutable normalized market ticker."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise TypeError("Ticker value must be a string.")

        value = self.value.strip().upper()
        if not value:
            raise ValueError("Ticker cannot be empty.")
        if not _TICKER_PATTERN.fullmatch(value):
            raise ValueError("Ticker must have 1 to 20 alphanumeric characters, dots, or hyphens.")

        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Ticker('{self.value}')"
