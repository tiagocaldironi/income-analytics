import json
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from income_analytics.application.income_starter import (
    IncomeStarterError,
    IncomeStarterRepository,
)
from income_analytics.infrastructure.database import Base
from income_analytics.infrastructure.models import (
    IncomeStarterTemplateVersionRecord,
    PortfolioRecord,
    PortfolioStrategyMetadataRecord,
)

PORTFOLIO_A = "7a54eeb7-542a-5832-8544-8be7dcb0237e"
PORTFOLIO_B = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def repository(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'starter.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    now = datetime.now(UTC)
    with sessions.begin() as session:
        for portfolio_id in (PORTFOLIO_A, PORTFOLIO_B):
            session.add(
                PortfolioRecord(
                    id=portfolio_id,
                    name=portfolio_id,
                    base_currency="BRL",
                    status="ACTIVE",
                    created_at=now,
                    updated_at=now,
                )
            )
        session.add(
            IncomeStarterTemplateVersionRecord(
                id="conservadora@1",
                template_key="conservadora",
                version=1,
                name="Conservadora",
                status="DRAFT",
                description="Em elaboração.",
                objective="Objetivo educacional.",
                risk_profile="Em revisão",
                horizon="Em revisão",
                volatility_tolerance="Em revisão",
                knowledge="Em revisão",
                typical_profile="Em revisão",
                characteristics_json="[]",
                not_suitable_json="[]",
                author="Income Analytics",
                methodology="Sem alocações definidas.",
                methodology_sources_json="[]",
                allocation_sources_json="[]",
                allocations_json=None,
                allocations_validated=False,
                financial_review_status="PENDING",
                regulatory_review_status="PENDING",
                created_at=now,
            )
        )
    yield IncomeStarterRepository(sessions, initialize=lambda: None)
    engine.dispose()


def test_draft_persists_without_any_allocation(repository):
    model = repository.get_version("conservadora", 1)

    assert model is not None
    assert model["status"] == "DRAFT"
    assert model["allocations"] is None
    assert model["adoption_available"] is False
    assert repository.list_catalog()[0]["name"] == "Conservadora"


def test_new_version_is_independent_and_returns_to_draft(repository):
    second = repository.create_next_draft_version("conservadora")
    revised = repository.update_draft_metadata(
        "conservadora", 2, {"description": "Texto revisado para a próxima versão."}
    )
    first = repository.get_version("conservadora", 1)

    assert second["version"] == 2
    assert second["id"] == "conservadora@2"
    assert second["status"] == "DRAFT"
    assert second["allocations"] is None
    assert revised["description"] == "Texto revisado para a próxima versão."
    assert revised["allocations"] is None
    assert first["version"] == 1
    assert first["description"] == "Em elaboração."
    assert first["status"] == "DRAFT"


def test_draft_adoption_is_blocked_before_any_portfolio_metadata_is_written(repository):
    with pytest.raises(IncomeStarterError, match="não foi publicado"):
        repository.adopt(UUID(PORTFOLIO_A), "conservadora", 1, {"FIXED_INCOME": "1"})

    with repository._session_factory() as session:
        assert session.get(PortfolioStrategyMetadataRecord, PORTFOLIO_A) is None


def test_publication_requires_sources_100_percent_and_both_reviews(repository):
    repository.submit_for_review("conservadora", 1)
    with pytest.raises(IncomeStarterError, match="fontes específicas"):
        repository.publish(
            "conservadora",
            1,
            allocations={"FIXED_INCOME": "1"},
            allocation_sources=[],
            financial_review_status="APPROVED",
            regulatory_review_status="APPROVED",
            reviewed_by="Reviewer",
        )
    with pytest.raises(IncomeStarterError, match="totalizar exatamente 100%"):
        repository.publish(
            "conservadora",
            1,
            allocations={"FIXED_INCOME": ".8"},
            allocation_sources=[
                {
                    "type": "ALLOCATION",
                    "title": "Metodologia",
                    "supports": "Faixas e critério de alocação.",
                    "url": "https://example.org/method",
                }
            ],
            financial_review_status="APPROVED",
            regulatory_review_status="APPROVED",
            reviewed_by="Reviewer",
        )
    with pytest.raises(IncomeStarterError, match="financeira e regulatória"):
        repository.publish(
            "conservadora",
            1,
            allocations={"FIXED_INCOME": "1"},
            allocation_sources=[
                {
                    "type": "ALLOCATION",
                    "title": "Metodologia",
                    "supports": "Faixas e critério de alocação.",
                    "url": "https://example.org/method",
                }
            ],
            financial_review_status="PENDING",
            regulatory_review_status="APPROVED",
            reviewed_by="Reviewer",
        )


def test_adoption_metadata_is_isolated_per_portfolio_and_keeps_catalog_version(repository):
    repository.submit_for_review("conservadora", 1)
    published = repository.publish(
        "conservadora",
        1,
        allocations={"FIXED_INCOME": ".7", "BRAZILIAN_STOCK": ".3"},
        allocation_sources=[
            {
                "type": "ALLOCATION",
                "title": "Approved allocation basis",
                "supports": "Critério documentado de alocação.",
                "url": "https://example.org/model",
            }
        ],
        financial_review_status="APPROVED",
        regulatory_review_status="APPROVED",
        reviewed_by="Reviewer",
    )
    assert published["status"] == "PUBLISHED"
    assert published["adoption_available"] is True

    first = repository.adopt(
        UUID(PORTFOLIO_A), "conservadora", 1, {"FIXED_INCOME": ".6", "BRAZILIAN_STOCK": ".4"}
    )
    second = repository.adopt(
        UUID(PORTFOLIO_B), "conservadora", 1, {"FIXED_INCOME": ".7", "BRAZILIAN_STOCK": ".3"}
    )

    assert first["customized"] is True
    assert second["customized"] is False
    with repository._session_factory() as session:
        rows = (
            session.execute(
                select(PortfolioStrategyMetadataRecord).order_by(
                    PortfolioStrategyMetadataRecord.portfolio_id
                )
            )
            .scalars()
            .all()
        )
    by_portfolio = {row.portfolio_id: row for row in rows}
    assert set(by_portfolio) == {PORTFOLIO_A, PORTFOLIO_B}
    assert json.loads(by_portfolio[PORTFOLIO_A].target_allocations_json) == {
        "BRAZILIAN_STOCK": "0.4",
        "FIXED_INCOME": "0.6",
    }
    assert json.loads(by_portfolio[PORTFOLIO_B].target_allocations_json) == {
        "BRAZILIAN_STOCK": "0.3",
        "FIXED_INCOME": "0.7",
    }
    assert (
        by_portfolio[PORTFOLIO_A].template_version
        == by_portfolio[PORTFOLIO_B].template_version
        == 1
    )
    personalized = repository.record_manual_update(
        UUID(PORTFOLIO_A), {"FIXED_INCOME": ".5", "BRAZILIAN_STOCK": ".5"}
    )
    assert personalized["source"] == "TEMPLATE"
    assert personalized["customized"] is True


def test_manual_editor_records_its_strategy_as_manual(repository):
    strategy = repository.record_manual_update(
        UUID(PORTFOLIO_A), {"FIXED_INCOME": ".8", "BRAZILIAN_STOCK": ".2"}
    )

    assert strategy["source"] == "MANUAL"
    assert strategy["strategy_name"] == "Minha estratégia"
    assert strategy["template_key"] is None
    assert strategy["customized"] is False
