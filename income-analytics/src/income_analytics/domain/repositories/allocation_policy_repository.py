"""Allocation-policy persistence contract."""

from typing import Protocol

from income_analytics.domain.allocation_policy import AllocationPolicy


class AllocationPolicyRepository(Protocol):
    def save(self, policy: AllocationPolicy) -> None: ...

    def get(self) -> AllocationPolicy | None: ...
