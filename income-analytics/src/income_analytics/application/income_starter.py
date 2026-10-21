"""Versioned educational strategy catalog and controlled publication workflow."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from income_analytics.domain.enums.asset_class import AssetClass
from income_analytics.infrastructure.database import SessionFactory, initialize_database
from income_analytics.infrastructure.models import (
    IncomeStarterTemplateVersionRecord,
    PortfolioRecord,
    PortfolioStrategyMetadataRecord,
)

EDUCATIONAL_NOTICE = (
    "Este modelo apresenta uma proposta educacional entre classes de ativos. Não constitui "
    "recomendação individualizada, avaliação de adequação ao perfil ou promessa de rentabilidade. "
    "A escolha deve considerar seus objetivos, horizonte, liquidez e tolerância a perdas. "
    "A publicação depende de revisão financeira e regulatória."
)


class IncomeStarterError(ValueError):
    """A catalog action does not meet its publication or adoption policy."""


class IncomeStarterRepository:
    """Persistence adapter; the session factory is injectable for isolated tests."""

    def __init__(
        self,
        session_factory: sessionmaker = SessionFactory,
        *,
        initialize=initialize_database,
        transition_authorizer: Callable[[str, str], bool] | None = None,
    ):
        self._session_factory = session_factory
        self._initialize = initialize
        self._transition_authorizer = transition_authorizer

    def _authorize_transition(self, action: str, actor_id: str) -> None:
        if not actor_id or not actor_id.strip() or self._transition_authorizer is None:
            raise IncomeStarterError("PUBLICATION_BLOCKED_AUTHENTICATION_UNAVAILABLE")
        if not self._transition_authorizer(action, actor_id.strip()):
            raise IncomeStarterError("PUBLICATION_BLOCKED_UNAUTHORIZED")

    def _ready(self) -> None:
        self._initialize()

    @staticmethod
    def _view(row: IncomeStarterTemplateVersionRecord) -> dict[str, Any]:
        allocations = json.loads(row.allocations_json) if row.allocations_json else None
        allocation_sources = json.loads(row.allocation_sources_json)
        adoption_available = (
            row.status == "PUBLISHED"
            and row.allocations_validated
            and row.financial_review_status == "APPROVED"
            and row.regulatory_review_status == "APPROVED"
            and bool(row.financial_approved_by and row.financial_approved_at)
            and bool(row.regulatory_approved_by and row.regulatory_approved_at)
            and bool(row.published_by and row.published_at)
            and bool(allocation_sources)
            and all(
                source.get("type") == "ALLOCATION"
                and source.get("title", "").strip()
                and source.get("supports", "").strip()
                and source.get("url", "").startswith("https://")
                for source in allocation_sources
            )
        )
        if adoption_available:
            try:
                IncomeStarterRepository._validate_allocations(allocations or {})
            except IncomeStarterError:
                adoption_available = False
        return {
            "id": row.id,
            "template_key": row.template_key,
            "version": row.version,
            "name": row.name,
            "status": row.status,
            "description": row.description,
            "objective": row.objective,
            "risk_profile": row.risk_profile,
            "horizon": row.horizon,
            "volatility_tolerance": row.volatility_tolerance,
            "knowledge": row.knowledge,
            "typical_profile": row.typical_profile,
            "characteristics": json.loads(row.characteristics_json),
            "not_suitable": json.loads(row.not_suitable_json),
            "author": row.author,
            "methodology": row.methodology,
            "methodology_sources": json.loads(row.methodology_sources_json),
            "allocation_sources": allocation_sources,
            "allocations": allocations,
            "allocations_validated": row.allocations_validated,
            "financial_review_status": row.financial_review_status,
            "financial_approved_by": row.financial_approved_by,
            "financial_approved_at": row.financial_approved_at.isoformat()
            if row.financial_approved_at
            else None,
            "regulatory_review_status": row.regulatory_review_status,
            "regulatory_approved_by": row.regulatory_approved_by,
            "regulatory_approved_at": row.regulatory_approved_at.isoformat()
            if row.regulatory_approved_at
            else None,
            "reviewed_by": row.reviewed_by,
            "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
            "created_at": row.created_at.isoformat(),
            "published_by": row.published_by,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "educational_notice": EDUCATIONAL_NOTICE,
            "adoption_available": adoption_available,
        }

    def list_catalog(self) -> list[dict[str, Any]]:
        self._ready()
        with self._session_factory() as session:
            latest = (
                select(
                    IncomeStarterTemplateVersionRecord.template_key,
                    func.max(IncomeStarterTemplateVersionRecord.version).label("version"),
                )
                .group_by(IncomeStarterTemplateVersionRecord.template_key)
                .subquery()
            )
            rows = (
                session.execute(
                    select(IncomeStarterTemplateVersionRecord)
                    .join(
                        latest,
                        (IncomeStarterTemplateVersionRecord.template_key == latest.c.template_key)
                        & (IncomeStarterTemplateVersionRecord.version == latest.c.version),
                    )
                    .order_by(
                        IncomeStarterTemplateVersionRecord.version,
                        IncomeStarterTemplateVersionRecord.name,
                    )
                )
                .scalars()
                .all()
            )
            return [self._view(row) for row in rows]

    def get_version(self, template_key: str, version: int | None = None) -> dict[str, Any] | None:
        self._ready()
        with self._session_factory() as session:
            statement = select(IncomeStarterTemplateVersionRecord).where(
                IncomeStarterTemplateVersionRecord.template_key == template_key
            )
            if version is not None:
                statement = statement.where(IncomeStarterTemplateVersionRecord.version == version)
            else:
                statement = statement.order_by(IncomeStarterTemplateVersionRecord.version.desc())
            row = session.execute(statement.limit(1)).scalar_one_or_none()
            return self._view(row) if row else None

    def submit_for_review(
        self,
        template_key: str,
        version: int,
        *,
        actor_id: str,
        allocations: dict[str, str | Decimal],
        allocation_sources: list[dict[str, str]],
    ) -> dict[str, Any]:
        self._authorize_transition("SUBMIT_FOR_REVIEW", actor_id)
        parsed = self._validate_proposal(allocations, allocation_sources)
        self._ready()
        with self._session_factory.begin() as session:
            row = self._required(session, template_key, version)
            if row.status != "DRAFT":
                raise IncomeStarterError("Somente um rascunho pode entrar em revisão.")
            if not row.methodology.strip() or not row.author.strip():
                raise IncomeStarterError(
                    "Metodologia e responsável pela elaboração são obrigatórios."
                )
            if not json.loads(row.methodology_sources_json):
                raise IncomeStarterError("Documente as fontes conceituais e metodológicas.")
            row.allocations_json = json.dumps(parsed, ensure_ascii=False, sort_keys=True)
            row.allocation_sources_json = json.dumps(allocation_sources, ensure_ascii=False)
            row.status = "IN_REVIEW"
            return self._view(row)

    def record_review_approval(
        self,
        template_key: str,
        version: int,
        *,
        review_type: str,
        actor_id: str,
        decision: str = "APPROVED",
    ) -> dict[str, Any]:
        action_by_type = {
            "FINANCIAL": "APPROVE_FINANCIAL",
            "REGULATORY": "APPROVE_REGULATORY",
        }
        action = action_by_type.get(review_type)
        if action is None or decision != "APPROVED":
            raise IncomeStarterError("Tipo de revisão ou decisão inválida.")
        self._authorize_transition(action, actor_id)
        self._ready()
        with self._session_factory.begin() as session:
            row = self._required(session, template_key, version)
            if row.status != "IN_REVIEW":
                raise IncomeStarterError("A aprovação exige um modelo em revisão.")
            if review_type == "FINANCIAL":
                row.financial_review_status = "APPROVED"
                row.financial_approved_by = actor_id.strip()
                row.financial_approved_at = datetime.now(UTC)
            else:
                row.regulatory_review_status = "APPROVED"
                row.regulatory_approved_by = actor_id.strip()
                row.regulatory_approved_at = datetime.now(UTC)
            row.reviewed_by = actor_id.strip()
            row.reviewed_at = datetime.now(UTC)
            return self._view(row)

    def publish(
        self,
        template_key: str,
        version: int,
        *,
        allocations: dict[str, str | Decimal],
        allocation_sources: list[dict[str, str]],
        publisher_id: str,
    ) -> dict[str, Any]:
        self._authorize_transition("PUBLISH", publisher_id)
        parsed = self._validate_allocations(allocations)
        self._validate_allocation_sources(allocation_sources)
        self._ready()
        with self._session_factory.begin() as session:
            row = self._required(session, template_key, version)
            if row.status != "IN_REVIEW":
                raise IncomeStarterError("O modelo precisa estar em revisão antes da publicação.")
            if (
                row.financial_review_status != "APPROVED"
                or not row.financial_approved_by
                or not row.financial_approved_at
                or row.regulatory_review_status != "APPROVED"
                or not row.regulatory_approved_by
                or not row.regulatory_approved_at
            ):
                raise IncomeStarterError(
                    "As aprovações financeira e regulatória identificadas são obrigatórias."
                )
            proposed_allocations = self._validate_allocations(
                json.loads(row.allocations_json or "{}")
            )
            proposed_sources = json.loads(row.allocation_sources_json)
            if parsed != proposed_allocations or allocation_sources != proposed_sources:
                raise IncomeStarterError("A publicação deve preservar a proposta revisada.")
            now = datetime.now(UTC)
            row.allocations_json = json.dumps(parsed, ensure_ascii=False, sort_keys=True)
            row.allocations_validated = True
            row.allocation_sources_json = json.dumps(allocation_sources, ensure_ascii=False)
            row.published_by = publisher_id.strip()
            row.published_at = now
            row.status = "PUBLISHED"
            return self._view(row)

    def create_next_draft_version(self, template_key: str) -> dict[str, Any]:
        """Copy the current editorial metadata into a new, unpublished version."""
        self._ready()
        with self._session_factory.begin() as session:
            previous = session.execute(
                select(IncomeStarterTemplateVersionRecord)
                .where(IncomeStarterTemplateVersionRecord.template_key == template_key)
                .order_by(IncomeStarterTemplateVersionRecord.version.desc())
                .limit(1)
            ).scalar_one_or_none()
            if previous is None:
                raise IncomeStarterError("Modelo não encontrado.")
            version = previous.version + 1
            row = IncomeStarterTemplateVersionRecord(
                id=f"{template_key}@{version}",
                template_key=template_key,
                version=version,
                name=previous.name,
                status="DRAFT",
                description=previous.description,
                objective=previous.objective,
                risk_profile=previous.risk_profile,
                horizon=previous.horizon,
                volatility_tolerance=previous.volatility_tolerance,
                knowledge=previous.knowledge,
                typical_profile=previous.typical_profile,
                characteristics_json=previous.characteristics_json,
                not_suitable_json=previous.not_suitable_json,
                author=previous.author,
                methodology=previous.methodology,
                methodology_sources_json=previous.methodology_sources_json,
                allocation_sources_json="[]",
                allocations_json=None,
                allocations_validated=False,
                financial_review_status="PENDING",
                financial_approved_by=None,
                financial_approved_at=None,
                regulatory_review_status="PENDING",
                regulatory_approved_by=None,
                regulatory_approved_at=None,
                reviewed_by=None,
                reviewed_at=None,
                created_at=datetime.now(UTC),
                published_by=None,
                published_at=None,
            )
            session.add(row)
            session.flush()
            return self._view(row)

    def update_draft_metadata(
        self, template_key: str, version: int, changes: dict[str, Any]
    ) -> dict[str, Any]:
        """Edit editorial copy only while a version is a draft; never edit percentages here."""
        text_fields = {
            "name",
            "description",
            "objective",
            "risk_profile",
            "horizon",
            "volatility_tolerance",
            "knowledge",
            "typical_profile",
            "author",
            "methodology",
        }
        list_fields = {
            "characteristics": "characteristics_json",
            "not_suitable": "not_suitable_json",
            "methodology_sources": "methodology_sources_json",
        }
        if not changes or set(changes) - text_fields - set(list_fields):
            raise IncomeStarterError("O rascunho contém campos editoriais não permitidos.")
        self._ready()
        with self._session_factory.begin() as session:
            row = self._required(session, template_key, version)
            if row.status != "DRAFT":
                raise IncomeStarterError("Somente um rascunho pode ser editado.")
            for field, value in changes.items():
                if field in text_fields:
                    if not isinstance(value, str) or not value.strip():
                        raise IncomeStarterError(f"Informe um valor para {field}.")
                    setattr(row, field, value.strip())
                else:
                    if not isinstance(value, list):
                        raise IncomeStarterError(f"O campo {field} deve ser uma lista.")
                    setattr(row, list_fields[field], json.dumps(value, ensure_ascii=False))
            return self._view(row)

    def adopt(
        self,
        portfolio_id: UUID,
        template_key: str,
        version: int,
        allocations: dict[str, str | Decimal],
    ) -> dict[str, Any]:
        model, parsed = self.validate_for_adoption(template_key, version, allocations)
        self._ready()
        with self._session_factory.begin() as session:
            portfolio = session.get(PortfolioRecord, str(portfolio_id))
            if portfolio is None or portfolio.status != "ACTIVE":
                raise IncomeStarterError("A carteira selecionada não está ativa.")
            session.merge(
                PortfolioStrategyMetadataRecord(
                    portfolio_id=str(portfolio_id),
                    source="TEMPLATE",
                    strategy_name=model["name"],
                    template_key=template_key,
                    template_version=version,
                    customized=parsed != model["allocations"],
                    adopted_at=datetime.now(UTC),
                    target_allocations_json=json.dumps(parsed, sort_keys=True),
                )
            )
        return {
            "source": "TEMPLATE",
            "template_key": template_key,
            "template_version": version,
            "strategy_name": model["name"],
            "customized": parsed != model["allocations"],
        }

    def get_portfolio_strategy(self, portfolio_id: UUID) -> dict[str, Any] | None:
        self._ready()
        with self._session_factory() as session:
            row = session.get(PortfolioStrategyMetadataRecord, str(portfolio_id))
            if row is None:
                return None
            return {
                "source": row.source,
                "strategy_name": row.strategy_name,
                "template_key": row.template_key,
                "template_version": row.template_version,
                "customized": row.customized,
                "adopted_at": row.adopted_at.isoformat(),
                "target_allocations": json.loads(row.target_allocations_json),
            }

    def record_manual_update(self, portfolio_id: UUID, allocations) -> dict[str, Any]:
        """Keep strategy source metadata accurate when the existing editor saves changes."""
        # AllocationPolicy owns manual-target validation and retains its existing tolerance.
        parsed = {
            getattr(key, "value", str(key)): str(Decimal(str(value)).normalize())
            for key, value in allocations.items()
        }
        self._ready()
        with self._session_factory.begin() as session:
            row = session.get(PortfolioStrategyMetadataRecord, str(portfolio_id))
            old_allocations = json.loads(row.target_allocations_json) if row else {}
            if row:
                row.customized = (
                    row.customized or row.source == "TEMPLATE" and old_allocations != parsed
                )
                row.target_allocations_json = json.dumps(parsed, sort_keys=True)
            else:
                row = PortfolioStrategyMetadataRecord(
                    portfolio_id=str(portfolio_id),
                    source="MANUAL",
                    strategy_name="Minha estratégia",
                    template_key=None,
                    template_version=None,
                    customized=False,
                    adopted_at=datetime.now(UTC),
                    target_allocations_json=json.dumps(parsed, sort_keys=True),
                )
                session.add(row)
            return {
                "source": row.source,
                "strategy_name": row.strategy_name,
                "template_key": row.template_key,
                "template_version": row.template_version,
                "customized": row.customized,
                "adopted_at": row.adopted_at.isoformat(),
                "target_allocations": json.loads(row.target_allocations_json),
            }

    def validate_for_adoption(self, template_key: str, version: int, allocations):
        self._ready()
        model = self.get_version(template_key, version)
        if model is None:
            raise IncomeStarterError("Modelo não encontrado.")
        if not model["adoption_available"] or model["status"] != "PUBLISHED":
            raise IncomeStarterError(
                "Este modelo ainda não foi publicado e homologado para adoção."
            )
        parsed = self._validate_allocations(allocations)
        if parsed != model["allocations"]:
            # Decimal-equivalent user edits are allowed only after an approved base exists.
            if set(parsed) != set(model["allocations"]):
                raise IncomeStarterError(
                    "A personalização deve manter as classes do modelo publicado."
                )
        return model, parsed

    @staticmethod
    def _required(session, template_key: str, version: int) -> IncomeStarterTemplateVersionRecord:
        row = session.get(IncomeStarterTemplateVersionRecord, f"{template_key}@{version}")
        if row is None:
            raise IncomeStarterError("Modelo não encontrado.")
        return row

    @classmethod
    def _validate_proposal(cls, allocations, sources):
        parsed = cls._validate_allocations(allocations)
        cls._validate_allocation_sources(sources)
        return parsed

    @staticmethod
    def _validate_allocation_sources(sources):
        if (
            not isinstance(sources, list)
            or not sources
            or any(
                not isinstance(item, dict)
                or item.get("type") != "ALLOCATION"
                or not isinstance(item.get("title"), str)
                or not item["title"].strip()
                or not isinstance(item.get("supports"), str)
                or not item["supports"].strip()
                or not isinstance(item.get("url"), str)
                or not item["url"].startswith("https://")
                for item in sources
            )
        ):
            raise IncomeStarterError(
                "Documente fontes específicas de alocação com links verificáveis."
            )

    @staticmethod
    def _validate_allocations(allocations):
        if not allocations:
            raise IncomeStarterError("Informe a distribuição validada do modelo.")
        parsed: dict[str, str] = {}
        try:
            for asset_class, value in allocations.items():
                if AssetClass(asset_class) is AssetClass.CASH:
                    raise IncomeStarterError("CASH não participa da política de ativos investidos.")
                number = Decimal(str(value))
                if not number.is_finite() or number < 0 or number > 1:
                    raise IncomeStarterError("Cada alocação deve estar entre 0 e 100%.")
                parsed[asset_class] = str(number.normalize())
        except (InvalidOperation, ValueError) as error:
            if isinstance(error, IncomeStarterError):
                raise
            raise IncomeStarterError(
                "A alocação contém uma classe ou percentual inválido."
            ) from error
        if sum((Decimal(value) for value in parsed.values()), Decimal(0)) != Decimal("1"):
            raise IncomeStarterError("A distribuição validada deve totalizar exatamente 100%.")
        return parsed


catalog = IncomeStarterRepository()
