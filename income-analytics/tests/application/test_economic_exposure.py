from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from income_analytics.application.economic_exposure import EconomicExposureRepository
from income_analytics.application.income_starter import IncomeStarterError
from income_analytics.infrastructure.database import Base
from income_analytics.infrastructure.models import AssetRecord

ASSET_ID = UUID("84dd0d6d-65e0-4832-b62a-5cbeac99ff20")


@pytest.fixture
def repository(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'exposure.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions.begin() as session:
        session.add(
            AssetRecord(
                id=str(ASSET_ID),
                ticker="ETF1",
                name="ETF de teste",
                asset_class="ETF",
                asset_type="ETF",
                valuation_method="MARKET_PRICE",
                currency_code="BRL",
                country="BR",
                sector=None,
                created_at=datetime.now(UTC),
            )
        )
    yield EconomicExposureRepository(sessions, initialize=lambda: None)
    engine.dispose()


def test_absent_classification_is_unknown_and_mixed_sources_are_normalized(repository):
    assert repository.get(ASSET_ID) == {
        "asset_id": str(ASSET_ID),
        "status": "UNKNOWN",
        "exposures": [],
    }
    result = repository.replace(
        ASSET_ID,
        [
            {
                "category": "BRAZIL_EQUITY",
                "exposure_share": ".7",
                "classification_status": "CONFIRMED",
                "source": "Index factsheet",
                "source_reference_date": "2026-10-01",
                "source_url": "https://example.org/factsheet",
            },
            {
                "category": "FIXED_INCOME",
                "exposure_share": ".3",
                "classification_status": "CONFIRMED",
                "source": "Index factsheet",
                "source_reference_date": "2026-10-01",
                "source_url": "https://example.org/factsheet",
            },
        ],
    )
    assert result["status"] == "CLASSIFIED"
    assert sum(float(item["exposure_share"]) for item in result["exposures"]) == pytest.approx(1)


def test_unclassified_is_explicit_and_mixed_shares_cannot_double_count(repository):
    unknown = repository.replace(
        ASSET_ID, [{"category": "UNCLASSIFIED", "classification_status": "UNKNOWN"}]
    )
    assert unknown["status"] == "UNKNOWN"
    with pytest.raises(IncomeStarterError, match="somar 100%"):
        repository.replace(
            ASSET_ID,
            [
                {
                    "category": "BRAZIL_EQUITY",
                    "exposure_share": ".8",
                    "classification_status": "CONFIRMED",
                    "source": "Source",
                    "source_reference_date": "2026-10-01",
                    "source_url": "https://example.org",
                },
                {
                    "category": "UNCLASSIFIED",
                    "exposure_share": ".3",
                    "classification_status": "UNKNOWN",
                },
            ],
        )
