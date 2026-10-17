from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.infrastructure.brapi_asset_discovery import BrapiAssetDiscoveryProvider


def test_brapi_adapter_normalizes_partial_metadata_without_inventing_sector() -> None:
    candidate = BrapiAssetDiscoveryProvider._candidate(
        {"symbol": "PETR4", "name": "Petrobras PN", "assetType": "stock"}
    )

    assert candidate is not None
    assert candidate.symbol == "PETR4"
    assert candidate.currency_code == "BRL"
    assert candidate.sector is None


def test_brapi_adapter_preserves_a_trusted_etf_classification() -> None:
    candidate = BrapiAssetDiscoveryProvider._candidate(
        {"symbol": "BOVA11", "name": "iShares Ibovespa", "assetType": "ETF"}
    )

    assert candidate is not None
    assert candidate.suggested_asset_class is AssetClass.BRAZILIAN_ETF


def test_brapi_adapter_classifies_fundo_de_indice_metadata_as_brazilian_etf() -> None:
    candidate = BrapiAssetDiscoveryProvider._candidate(
        {
            "symbol": "IVVB11",
            "name": "iShares S&P 500",
            "assetType": "Fundo de Índice",
        }
    )

    assert candidate is not None
    assert candidate.suggested_asset_class is AssetClass.BRAZILIAN_ETF


def test_brapi_adapter_classifies_provider_name_fundo_de_indice_as_etf() -> None:
    candidate = BrapiAssetDiscoveryProvider._candidate(
        {
            "symbol": "AUPO11",
            "name": "BTG Pactual Fundo de Índice",
            "assetType": "fund",
        }
    )

    assert candidate is not None
    assert candidate.suggested_asset_class is AssetClass.BRAZILIAN_ETF


def test_brapi_adapter_keeps_fii_priority_over_fundo_de_indice_metadata() -> None:
    candidate = BrapiAssetDiscoveryProvider._candidate(
        {
            "symbol": "MXRF11",
            "name": "Maxi Renda",
            "assetType": "Fundo de Índice",
            "subType": "FII",
        }
    )

    assert candidate is not None
    assert candidate.suggested_asset_class is AssetClass.FII


def test_brapi_adapter_classifies_fiagro_and_infrastructure_funds_as_fii() -> None:
    fiagro = BrapiAssetDiscoveryProvider._candidate(
        {"symbol": "SNAG11", "name": "Suno Agro Fiagro Imobiliario", "assetType": "fund"}
    )
    infrastructure = BrapiAssetDiscoveryProvider._candidate(
        {
            "symbol": "INFRA",
            "name": "Fundo de Investimento em Direitos Creditorios de Infraestrutura",
            "assetType": "fund",
        }
    )

    assert fiagro is not None
    assert infrastructure is not None
    assert fiagro.suggested_asset_class is AssetClass.FII
    assert infrastructure.suggested_asset_class is AssetClass.FII


def test_brapi_adapter_classifies_provider_figaro_variant_as_fii() -> None:
    candidate = BrapiAssetDiscoveryProvider._candidate(
        {
            "symbol": "RURA11",
            "name": "Itau Asset Rural Figaro Imobiliario",
            "assetType": "fund",
        }
    )

    assert candidate is not None
    assert candidate.suggested_asset_class is AssetClass.FII
