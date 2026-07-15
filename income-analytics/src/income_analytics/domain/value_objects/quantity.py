"""
Immutable value object representing an asset quantity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Quantity:
    """
    Represents an immutable asset quantity.

    Quantities are always non-negative and preserve decimal precision.
    """

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError("Quantity value must be a Decimal.")

        if self.value < Decimal("0"):
            raise ValueError("Quantity cannot be negative.")

    def __add__(self, other: Quantity) -> Quantity:
        if not isinstance(other, Quantity):
            return NotImplemented

        return Quantity(self.value + other.value)

    def __sub__(self, other: Quantity) -> Quantity:
        if not isinstance(other, Quantity):
            return NotImplemented

        result = self.value - other.value

        if result < Decimal("0"):
            raise ValueError("Resulting quantity cannot be negative.")

        return Quantity(result)

    def __lt__(self, other: Quantity) -> bool:
        return self.value < other.value

    def __le__(self, other: Quantity) -> bool:
        return self.value <= other.value

    def __gt__(self, other: Quantity) -> bool:
        return self.value > other.value

    def __ge__(self, other: Quantity) -> bool:
        return self.value >= other.value

    def __str__(self) -> str:
        return str(self.value)