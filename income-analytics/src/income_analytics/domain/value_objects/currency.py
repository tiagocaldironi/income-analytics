"""
Currency Value Object.

Represents a currency used by financial assets and monetary values.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Currency:
    """
    Represents a currency.

    Examples
    --------
    Currency(
        code="BRL",
        name="Real Brasileiro",
        symbol="R$",
        decimal_places=2,
    )
    """

    code: str
    name: str
    symbol: str
    decimal_places: int

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("Currency code cannot be empty.")

        if not self.name.strip():
            raise ValueError("Currency name cannot be empty.")

        if not self.symbol.strip():
            raise ValueError("Currency symbol cannot be empty.")

        if self.decimal_places < 0:
            raise ValueError("Decimal places cannot be negative.")