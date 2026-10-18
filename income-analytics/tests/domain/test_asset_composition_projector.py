from decimal import Decimal

from income_analytics.domain.projectors.asset_composition_projector import (
    AssetCompositionInput,
    AssetCompositionProjector,
)


def _item(name: str, value: str | None, target: str | None) -> AssetCompositionInput:
    return AssetCompositionInput(
        asset_id=name,
        label=name,
        is_open=value is not None,
        current_value=Decimal(value) if value is not None else None,
        target_weight=Decimal(target) if target is not None else None,
    )


def test_composition_distance_is_zero_when_current_matches_targets() -> None:
    projection = AssetCompositionProjector.project((_item("A", "50", ".5"), _item("B", "50", ".5")))
    assert projection.distance == Decimal("0")
    assert projection.valuation_quality == "COMPLETE"


def test_composition_distance_uses_total_variation_and_keeps_target_only_asset() -> None:
    projection = AssetCompositionProjector.project(
        (_item("A", "60", ".5"), _item("B", "40", ".25"), _item("C", None, ".25"))
    )
    assert projection.distance == Decimal(".25")
    assert projection.items[-1].current_weight == Decimal("0")
    assert projection.items[-1].gap_pp == Decimal(".25")


def test_partial_valuation_does_not_normalize_known_valued_assets() -> None:
    projection = AssetCompositionProjector.project(
        (_item("A", "50", ".5"), AssetCompositionInput("B", "B", True, None, Decimal(".5")))
    )
    assert projection.distance is None
    assert projection.valuation_quality == "PARTIAL"
