"""
Money Value Object.

Represents a monetary amount.

This object is immutable and always uses Decimal to avoid
floating-point precision issues.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True, order=True)
class Money:
    """
    Immutable Value Object representing a monetary amount.
    """

    amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Money.amount must be a Decimal instance.")

        if self.amount.is_nan():
            raise ValueError("Money.amount cannot be NaN.")

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented

        return Money(self.amount + other.amount)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented

        return Money(self.amount - other.amount)

    def __neg__(self) -> Money:
        return Money(-self.amount)

    @property
    def is_zero(self) -> bool:
        """Returns True if the amount is zero."""
        return self.amount == Decimal("0")

    @property
    def is_positive(self) -> bool:
        """Returns True if the amount is greater than zero."""
        return self.amount > Decimal("0")

    @property
    def is_negative(self) -> bool:
        """Returns True if the amount is less than zero."""
        return self.amount < Decimal("0")

    @classmethod
    def zero(cls) -> Money:
        """Factory method for a zero monetary value."""
        return cls(Decimal("0"))

    def __str__(self) -> str:
        return str(self.amount)