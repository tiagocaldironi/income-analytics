from income_analytics.api.routers import dashboard
from income_analytics.domain.enums.asset_class import AssetClass
from tests.unit.domain.builders import build_asset


def test_us_reit_routes_to_twelve_data() -> None:
    asset = build_asset(asset_class=AssetClass.US_REIT)

    assert dashboard.market_data_provider_for(asset) is dashboard.us_market_data


def test_us_asset_search_only_uses_twelve_data_when_class_is_explicit(monkeypatch) -> None:
    calls: list[str] = []

    def fail_search(*_args, **_kwargs):
        raise AssertionError("non-US provider must not be called")

    def us_search(query: str, *, limit: int):
        calls.append(query)
        return ()

    monkeypatch.setattr(dashboard.asset_discovery, "search", fail_search)
    monkeypatch.setattr(dashboard.crypto_data, "search", fail_search)
    monkeypatch.setattr(dashboard.us_market_data, "search", us_search)

    result = dashboard.search_assets("PLD", asset_class=AssetClass.US_REIT)

    assert result["candidates"] == []
    assert calls == ["PLD"]
