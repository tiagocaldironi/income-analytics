"""A dated manual benchmark return used by the local MVP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class BenchmarkRate:
    """A periodic return for a named benchmark such as CDI."""

    name: str
    effective_date: date
    return_percentage: Decimal

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("O nome do benchmark é obrigatório.")
        if not isinstance(self.effective_date, date):
            raise TypeError("effective_date must be a date instance.")
        if self.return_percentage <= Decimal("-1"):
            raise ValueError("O retorno do benchmark deve ser maior que -100%.")
