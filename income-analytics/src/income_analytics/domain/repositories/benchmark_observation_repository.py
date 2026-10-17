"""Persistence boundary for benchmark observations with explicit semantics."""

from __future__ import annotations

from typing import Protocol

from income_analytics.application.benchmark_data import BenchmarkObservation


class BenchmarkObservationRepository(Protocol):
    def save(self, observation: BenchmarkObservation) -> None: ...

    def list(self, benchmark: str) -> tuple[BenchmarkObservation, ...]: ...
