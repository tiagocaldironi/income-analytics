"""Read-model math for targets expressed inside an asset class."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class AssetCompositionInput:
    asset_id: str
    label: str
    is_open: bool
    current_value: Decimal | None
    target_weight: Decimal | None


@dataclass(frozen=True, slots=True)
class AssetCompositionItem:
    asset_id: str
    label: str
    current_value: Decimal | None
    current_weight: Decimal | None
    target_weight: Decimal | None
    gap_pp: Decimal | None


@dataclass(frozen=True, slots=True)
class AssetCompositionProjection:
    items: tuple[AssetCompositionItem, ...]
    current_value: Decimal | None
    distance: Decimal | None
    valuation_quality: str
    unavailable_reason: str | None = None


class AssetCompositionProjector:
    """Calculates current intra-class weights and total-variation distance."""

    @classmethod
    def project(cls, items: tuple[AssetCompositionInput, ...]) -> AssetCompositionProjection:
        held = tuple(item for item in items if item.is_open and item.current_value is not None)
        missing_valuation = any(item.is_open and item.current_value is None for item in items)
        if missing_valuation:
            return cls._unavailable(items, "Parte desta classe não pôde ser avaliada.")
        total = sum((item.current_value or Decimal("0") for item in held), Decimal("0"))
        if held and total <= 0:
            return cls._unavailable(items, "A classe não possui valor avaliável para composição.")
        if not held:
            return cls._unavailable(items, "A classe não possui posição atual avaliável.")
        result = tuple(
            AssetCompositionItem(
                asset_id=item.asset_id,
                label=item.label,
                current_value=item.current_value,
                current_weight=(item.current_value / total) if item.current_value is not None else Decimal("0"),
                target_weight=item.target_weight,
                gap_pp=(item.target_weight - (item.current_value / total if item.current_value is not None else Decimal("0")))
                if item.target_weight is not None
                else None,
            )
            for item in items
        )
        targeted = tuple(item for item in result if item.target_weight is not None)
        distance = (
            sum((abs(item.current_weight - item.target_weight) for item in targeted), Decimal("0"))
            / Decimal("2")
            if targeted and len(targeted) == len(result)
            else None
        )
        return AssetCompositionProjection(result, total, distance, "COMPLETE")

    @staticmethod
    def _unavailable(items: tuple[AssetCompositionInput, ...], reason: str) -> AssetCompositionProjection:
        return AssetCompositionProjection(
            tuple(AssetCompositionItem(item.asset_id, item.label, item.current_value, None, item.target_weight, None) for item in items),
            None,
            None,
            "PARTIAL",
            reason,
        )
