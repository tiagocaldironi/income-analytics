import pytest

from income_analytics.domain.enums.asset_type import AssetType


def test_asset_type_is_serialized_as_its_domain_value() -> None:
    assert AssetType.STOCK == "STOCK"
    assert AssetType("ETF") is AssetType.ETF


def test_rejects_an_unknown_asset_type() -> None:
    with pytest.raises(ValueError):
        AssetType("BOND")
