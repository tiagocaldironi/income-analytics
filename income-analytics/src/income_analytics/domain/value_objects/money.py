"""
Money Value Object.

Represents a monetary amount.

This object is immutable and should always use Decimal
to avoid floating-point precision issues.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Money:
    """
    Represents a monetary amount.

    Examples
    --------
    >>> Money(Decimal("100.50"))
    Money(amount=Decimal("100.50"))
    """

    amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Money.amount must be a Decimal instance.")
