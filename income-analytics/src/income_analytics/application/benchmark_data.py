"""Normalized boundary for public benchmark observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, Protocol

BenchmarkNature = Literal["PERIODIC_RATE", "INDEX_LEVEL", "INFLATION_RATE"]


@dataclass(frozen=True, slots=True, kw_only=True)
class BenchmarkObservation:
    benchmark: str
    effective_date: date
    value: Decimal
    nature: BenchmarkNature
    source: str


class BenchmarkDataUnavailable(Exception):
    pass


class BenchmarkDataProvider(Protocol):
    def observations(
        self, benchmark: str, *, start_date: date, end_date: date
    ) -> tuple[BenchmarkObservation, ...]: ...
