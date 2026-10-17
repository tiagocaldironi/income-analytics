"""User-defined target allocation policy by asset class."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from income_analytics.domain.enums.asset_class import AssetClass


@dataclass(frozen=True, slots=True, kw_only=True)
class AllocationPolicy:
    targets: dict[AssetClass, Decimal]

    def __post_init__(self) -> None:
        if AssetClass.CASH in self.targets:
            raise ValueError("CASH não participa da política de ativos investidos.")
        if any(weight < 0 or weight > 1 for weight in self.targets.values()):
            raise ValueError("Cada peso-alvo deve estar entre 0 e 1.")
        if abs(sum(self.targets.values(), Decimal("0")) - Decimal("1")) > Decimal("0.000001"):
            raise ValueError("A soma dos pesos-alvo deve ser 100%.")
