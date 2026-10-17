"""Per-asset target persistence contract."""

from typing import Protocol

from income_analytics.domain.asset_allocation_policy import AssetAllocationPolicy


class AssetAllocationPolicyRepository(Protocol):
    def save(self, policy: AssetAllocationPolicy) -> None: ...

    def get(self) -> AssetAllocationPolicy | None: ...
