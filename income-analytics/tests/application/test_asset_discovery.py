from income_analytics.application.asset_discovery import AssetCandidate
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.asset_class import AssetClass


def test_asset_candidate_can_be_confirmed_and_persisted_in_the_session() -> None:
    candidate = AssetCandidate(
        external_id="PETR4",
        symbol="PETR4",
        name="Petrobras PN",
        instrument_type="stock",
        suggested_asset_class=AssetClass.BRAZILIAN_STOCK,
        country="BR",
        currency_code="BRL",
        sector=None,
        source="test",
    )
    session = PortfolioSession()

    asset = session.register_asset(
        ticker=candidate.symbol,
        name=candidate.name,
        asset_class=candidate.suggested_asset_class or AssetClass.OTHER,
        country=candidate.country or "BR",
        currency_code=candidate.currency_code or "BRL",
        sector=candidate.sector,
    )

    assert str(asset.ticker) == "PETR4"
    assert asset.name == "Petrobras PN"
    assert session.register_asset(
        ticker="PETR4", name="Outro nome", asset_class=AssetClass.OTHER
    ) == asset
