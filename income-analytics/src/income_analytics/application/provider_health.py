"""Small persisted health record for public data providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderHealth:
    provider: str
    last_success: datetime | None = None
    last_failure: datetime | None = None
    consecutive_failures: int = 0
    last_error_type: str | None = None

    @property
    def status(self) -> str:
        if self.consecutive_failures >= 3:
            return "UNAVAILABLE"
        if self.consecutive_failures:
            return "DEGRADED"
        return "OK" if self.last_success else "UNKNOWN"


class ProviderHealthRepository(Protocol):
    def get(self, provider: str) -> ProviderHealth | None: ...
    def save(self, health: ProviderHealth) -> None: ...


class ProviderHealthRegistry:
    def __init__(self, repository: ProviderHealthRepository) -> None:
        self._repository = repository

    def success(self, provider: str) -> ProviderHealth:
        health = ProviderHealth(provider=provider, last_success=datetime.now(UTC))
        self._repository.save(health)
        return health

    def failure(self, provider: str, error: Exception) -> ProviderHealth:
        previous = self._repository.get(provider)
        health = ProviderHealth(
            provider=provider,
            last_success=previous.last_success if previous else None,
            last_failure=datetime.now(UTC),
            consecutive_failures=(previous.consecutive_failures if previous else 0) + 1,
            last_error_type=type(error).__name__,
        )
        self._repository.save(health)
        return health

    def statuses(self, providers: tuple[str, ...]) -> tuple[ProviderHealth, ...]:
        return tuple(
            self._repository.get(provider) or ProviderHealth(provider=provider)
            for provider in providers
        )
