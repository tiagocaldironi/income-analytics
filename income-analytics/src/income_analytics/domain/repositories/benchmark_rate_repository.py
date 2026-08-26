"""Benchmark-rate persistence contract."""

from typing import Protocol

from income_analytics.domain.benchmark_rate import BenchmarkRate


class BenchmarkRateRepository(Protocol):
    def save(self, rate: BenchmarkRate) -> None: ...

    def list(self) -> tuple[BenchmarkRate, ...]: ...
