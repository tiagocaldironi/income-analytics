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
ALLOCATION_SOURCES = [
    {
        "type": "ALLOCATION",
        "title": "Synthetic test source",
        "supports": "Test fixture only; not a real allocation basis.",
        "url": "https://example.org/test-only",
    }
]


def submit_to_review(repository, allocations=None, allocation_sources=None):
    return repository.submit_for_review(
        "conservadora",
        1,
        actor_id="Reviewer",
        allocations=allocations or {"FIXED_INCOME": "1"},
        allocation_sources=allocation_sources or ALLOCATION_SOURCES,
    )


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
                template_type="ALLOCATION_MODEL",
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
                methodology_sources_json='[{"type":"CONCEPTUAL","title":"Test method"}]',
                allocation_sources_json="[]",
                allocations_json=None,
                allocations_validated=False,
                financial_review_status="PENDING",
                regulatory_review_status="PENDING",
                created_at=now,
            )
        )
    yield IncomeStarterRepository(
        sessions,
        initialize=lambda: None,
        transition_authorizer=lambda action, actor_id: (
            actor_id
            in {
                "Reviewer",
                "FinancialReviewer",
                "RegulatoryReviewer",
            }
        ),
    )
    engine.dispose()


def test_draft_persists_without_any_allocation(repository):
    model = repository.get_version("conservadora", 1)

    assert model is not None
    assert model["status"] == "DRAFT"
    assert model["allocations"] is None
    assert model["adoption_available"] is False
    assert repository.list_catalog()[0]["name"] == "Conservadora"


def test_draft_cannot_enter_review_without_complete_supported_proposal(repository):
    with pytest.raises(IncomeStarterError, match="totalizar exatamente 100%"):
        submit_to_review(repository, {"FIXED_INCOME": ".8"})
    with pytest.raises(IncomeStarterError, match="classe ou percentual inválido"):
        submit_to_review(repository, {"UNKNOWN_CLASS": "1"})
    with pytest.raises(IncomeStarterError, match="fontes específicas de alocação"):
        submit_to_review(repository, {"FIXED_INCOME": "1"}, [{"type": "CONCEPTUAL"}])

    assert repository.get_version("conservadora", 1)["status"] == "DRAFT"

    submitted = submit_to_review(repository)
    assert submitted["status"] == "IN_REVIEW"
    assert submitted["adoption_available"] is False


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


def test_state_transitions_fail_closed_without_an_admin_authorizer(repository):
    locked = IncomeStarterRepository(repository._session_factory, initialize=lambda: None)

    with pytest.raises(IncomeStarterError, match="AUTHENTICATION_UNAVAILABLE"):
        locked.submit_for_review(
            "conservadora",
            1,
            actor_id="Reviewer",
            allocations={"FIXED_INCOME": "1"},
            allocation_sources=ALLOCATION_SOURCES,
        )
    with pytest.raises(IncomeStarterError, match="AUTHENTICATION_UNAVAILABLE"):
        locked.publish(
            "conservadora",
            1,
            allocations={"FIXED_INCOME": "1"},
            allocation_sources=ALLOCATION_SOURCES,
            publisher_id="Reviewer",
        )

    assert locked.get_version("conservadora", 1)["status"] == "DRAFT"


def test_publication_requires_sources_100_percent_and_both_reviews(repository):
    submit_to_review(repository)
    with pytest.raises(IncomeStarterError, match="fontes específicas"):
        repository.publish(
            "conservadora",
            1,
            allocations={"FIXED_INCOME": "1"},
            allocation_sources=[],
            publisher_id="Reviewer",
        )
    with pytest.raises(IncomeStarterError, match="totalizar exatamente 100%"):
        repository.publish(
            "conservadora",
            1,
            allocations={"FIXED_INCOME": ".8"},
            allocation_sources=ALLOCATION_SOURCES,
            publisher_id="Reviewer",
        )
    with pytest.raises(IncomeStarterError, match="aprovações financeira e regulatória"):
        repository.publish(
            "conservadora",
            1,
            allocations={"FIXED_INCOME": "1"},
            allocation_sources=ALLOCATION_SOURCES,
            publisher_id="Reviewer",
        )

    repository.record_review_approval(
        "conservadora", 1, review_type="FINANCIAL", actor_id="FinancialReviewer"
    )
    with pytest.raises(IncomeStarterError, match="aprovações financeira e regulatória"):
        repository.publish(
            "conservadora",
            1,
            allocations={"FIXED_INCOME": "1"},
            allocation_sources=ALLOCATION_SOURCES,
            publisher_id="Reviewer",
        )


def test_adoption_metadata_is_isolated_per_portfolio_and_keeps_catalog_version(repository):
    proposal = {"FIXED_INCOME": ".7", "BRAZILIAN_STOCK": ".3"}
    submit_to_review(repository, proposal)
    repository.record_review_approval(
        "conservadora", 1, review_type="FINANCIAL", actor_id="FinancialReviewer"
    )
    repository.record_review_approval(
        "conservadora", 1, review_type="REGULATORY", actor_id="RegulatoryReviewer"
    )
    published = repository.publish(
        "conservadora",
        1,
        allocations=proposal,
        allocation_sources=ALLOCATION_SOURCES,
        publisher_id="Reviewer",
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
    with pytest.raises(IncomeStarterError, match="Somente um rascunho pode ser editado"):
        repository.update_draft_metadata(
            "conservadora", 1, {"description": "Edição retroativa proibida."}
        )

    next_version = repository.create_next_draft_version("conservadora")
    assert next_version["version"] == 2
    assert next_version["status"] == "DRAFT"
    assert next_version["allocations"] is None
    assert next_version["financial_approved_by"] is None
    assert next_version["regulatory_approved_by"] is None
    assert repository.get_portfolio_strategy(UUID(PORTFOLIO_B))["template_version"] == 1
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


def test_guided_journey_type_cannot_be_adopted_or_submitted_for_allocation_review(repository):
    from income_analytics.infrastructure.models import IncomeStarterTemplateVersionRecord

    with repository._session_factory.begin() as session:
        session.add(
            IncomeStarterTemplateVersionRecord(
                id="primeiros-passos@1",
                template_key="primeiros-passos",
                version=1,
                template_type="GUIDED_JOURNEY",
                name="Primeiros Passos",
                status="DRAFT",
                description="Jornada",
                objective="Reserva",
                risk_profile="Educacional",
                horizon="Variável",
                volatility_tolerance="Não é perfil",
                knowledge="Inicial",
                typical_profile="Iniciante",
                characteristics_json="[]",
                not_suitable_json="[]",
                author="Income",
                methodology="Educacional",
                methodology_sources_json="[]",
                allocation_sources_json="[]",
                allocations_json=None,
                allocations_validated=False,
                financial_review_status="PENDING",
                regulatory_review_status="PENDING",
                created_at=datetime.now(UTC),
            )
        )
    model = repository.get_version("primeiros-passos", 1)
    assert model["template_type"] == "GUIDED_JOURNEY"
    assert model["allocations"] is None
    with pytest.raises(IncomeStarterError, match="não podem ser adotadas"):
        repository.validate_for_adoption("primeiros-passos", 1, {})
    with pytest.raises(IncomeStarterError, match="não entra na revisão"):
        repository.submit_for_review(
            "primeiros-passos",
            1,
            actor_id="Reviewer",
            allocations={"FIXED_INCOME": "1"},
            allocation_sources=ALLOCATION_SOURCES,
        )
    version_two = repository.create_next_draft_version("primeiros-passos")
    assert version_two["template_type"] == "GUIDED_JOURNEY"
    assert version_two["status"] == "DRAFT"
    assert version_two["allocations"] is None
