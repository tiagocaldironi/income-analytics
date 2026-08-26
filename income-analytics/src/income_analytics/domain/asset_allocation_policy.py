"""Editable target weights for assets inside a portfolio asset class."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from income_analytics.domain.entities.asset import Asset
from income_analytics.domain.enums.asset_class import AssetClass


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetAllocationPolicy:
    """Current (non-versioned) target weights within each configured class."""

    targets: dict[AssetClass, dict[str, Decimal]]

    def __post_init__(self) -> None:
        for asset_class, class_targets in self.targets.items():
            if not class_targets:
                raise ValueError(f"A classe {asset_class.value} precisa ter ao menos um ativo.")
            if any(weight < 0 or weight > 1 for weight in class_targets.values()):
                raise ValueError("Cada peso-alvo por ativo deve estar entre 0 e 1.")
            total = sum(class_targets.values(), Decimal("0"))
            if abs(total - Decimal("1")) > Decimal("0.000001"):
                raise ValueError("Os pesos-alvo dos ativos da classe devem somar 100%.")

    def validate_assets(self, assets: tuple[Asset, ...]) -> None:
        by_ticker = {str(asset.ticker): asset for asset in assets}
        for asset_class, class_targets in self.targets.items():
            eligible = {
                ticker for ticker, asset in by_ticker.items() if asset.asset_class is asset_class
            }
            if set(class_targets) != eligible:
                raise ValueError(
                    f"A política de {asset_class.value} deve incluir todos os ativos da classe."
                )

    def target_for(self, asset: Asset) -> Decimal | None:
        return self.targets.get(asset.asset_class, {}).get(str(asset.ticker))
