"""Lifecycle endpoints for local, single-user portfolios."""

import time
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError

from income_analytics.application.auth_context import current_principal
from income_analytics.application.portfolio_context import (
    MAIN_PORTFOLIO_ID,
    reset_active_portfolio_id,
    reset_request_session,
    set_active_portfolio_id,
    set_request_session,
)
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.entities.portfolio import Portfolio
from income_analytics.infrastructure.auth_config import saas_enabled
from income_analytics.infrastructure.sqlite_repositories import SqlitePortfolioRepository

router = APIRouter(prefix="/api/portfolios", tags=["Portfolios"])


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    base_currency: str = Field(default="BRL", min_length=3, max_length=3)


class PortfolioUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


def _payload(portfolio: Portfolio) -> dict[str, str]:
    return {
        "id": str(portfolio.id),
        "name": portfolio.name,
        "base_currency": portfolio.base_currency,
        "status": portfolio.status,
        "created_at": portfolio.created_at.isoformat(),
        "updated_at": portfolio.updated_at.isoformat(),
    }


def _name(value: str) -> str:
    value = value.strip()
    if not value:
        raise HTTPException(status_code=422, detail="Informe um nome para a carteira.")
    if len(value) > 100:
        raise HTTPException(status_code=422, detail="O nome pode ter até 100 caracteres.")
    return value


def _ensure_unique_name(
    repository: SqlitePortfolioRepository, name: str, *, exclude: UUID | None = None
) -> None:
    normalized = name.casefold()
    if any(
        item.id != exclude and item.status == "ACTIVE" and item.name.casefold() == normalized
        for item in repository.list()
    ):
        raise HTTPException(status_code=409, detail="Já existe uma carteira ativa com esse nome.")


def _initialize_portfolio_dashboard(portfolio_id: UUID) -> None:
    """Create the portfolio-scoped dashboard projection before exposing the wallet."""
    from income_analytics.api.routers.dashboard import rebuild_portfolio_dashboard_snapshot

    portfolio_token = set_active_portfolio_id(portfolio_id)
    session_token = set_request_session(
        PortfolioSession(portfolio_id=portfolio_id, persistent=True)
    )
    try:
        rebuild_portfolio_dashboard_snapshot()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A carteira foi criada, mas sua visão consolidada não pôde ser preparada.",
        ) from error
    finally:
        reset_request_session(session_token)
        reset_active_portfolio_id(portfolio_token)


@router.get("")
def list_portfolios() -> dict[str, object]:
    return {"portfolios": [_payload(item) for item in SqlitePortfolioRepository().list()]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_portfolio(body: PortfolioCreate) -> dict[str, str]:
    repository = SqlitePortfolioRepository()
    name = _name(body.name)
    _ensure_unique_name(repository, name)
    currency = body.base_currency.strip().upper()
    if not currency.isalpha():
        raise HTTPException(status_code=422, detail="Moeda inválida.")
    now = datetime.now(UTC)
    portfolio = Portfolio(
        id=uuid4(),
        name=name,
        base_currency=currency,
        created_at=now,
        updated_at=now,
        owner_user_id=current_principal().user_id if saas_enabled() else None,
    )
    try:
        repository.save(portfolio)
    except IntegrityError as error:
        raise HTTPException(
            status_code=409, detail="Já existe uma carteira ativa com esse nome."
        ) from error
    _initialize_portfolio_dashboard(portfolio.id)
    return _payload(portfolio)


@router.patch("/{portfolio_id}")
def rename_portfolio(portfolio_id: UUID, body: PortfolioUpdate) -> dict[str, str]:
    repository = SqlitePortfolioRepository()
    current = repository.get(portfolio_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Carteira não encontrada.")
    if current.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Restaure a carteira antes de renomeá-la.")
    name = _name(body.name)
    _ensure_unique_name(repository, name, exclude=portfolio_id)
    updated = Portfolio(
        id=current.id,
        owner_user_id=current.owner_user_id,
        name=name,
        base_currency=current.base_currency,
        status=current.status,
        created_at=current.created_at,
        updated_at=datetime.now(UTC),
    )
    try:
        repository.save(updated)
    except IntegrityError as error:
        raise HTTPException(
            status_code=409, detail="Já existe uma carteira ativa com esse nome."
        ) from error
    return _payload(updated)


def _change_status(portfolio_id: UUID, target_status: str) -> dict[str, str]:
    repository = SqlitePortfolioRepository()
    current = repository.get(portfolio_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Carteira não encontrada.")
    if target_status == "ARCHIVED":
        if portfolio_id == MAIN_PORTFOLIO_ID:
            raise HTTPException(
                status_code=409, detail="A carteira principal não pode ser arquivada."
            )
        if current.status == "ACTIVE" and not any(
            item.status == "ACTIVE" and item.id != portfolio_id for item in repository.list()
        ):
            raise HTTPException(status_code=409, detail="Mantenha ao menos uma carteira ativa.")
    updated = Portfolio(
        id=current.id,
        owner_user_id=current.owner_user_id,
        name=current.name,
        base_currency=current.base_currency,
        status=target_status,
        created_at=current.created_at,
        updated_at=datetime.now(UTC),
    )
    repository.save(updated)
    return _payload(updated)


@router.post("/{portfolio_id}/archive")
def archive_portfolio(portfolio_id: UUID) -> dict[str, str]:
    return _change_status(portfolio_id, "ARCHIVED")


@router.post("/{portfolio_id}/restore")
def restore_portfolio(portfolio_id: UUID) -> dict[str, str]:
    return _change_status(portfolio_id, "ACTIVE")


class PortfolioOnboardingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_step: int = Field(ge=1, le=4)
    status: Literal["ACTIVE", "SKIPPED", "COMPLETED"]


def _onboarding_key(portfolio_id: UUID) -> tuple[str, str]:
    if SqlitePortfolioRepository().get(portfolio_id) is None:
        raise HTTPException(404, "Carteira não encontrada.")
    viewer = str(current_principal().user_id) if saas_enabled() else "local"
    return viewer, str(portfolio_id)


@router.get("/{portfolio_id}/onboarding")
def get_portfolio_onboarding(portfolio_id: UUID):
    from income_analytics.infrastructure.database import SessionFactory
    from income_analytics.infrastructure.models import PortfolioOnboardingRecord

    key = _onboarding_key(portfolio_id)
    with SessionFactory() as db:
        row = db.get(PortfolioOnboardingRecord, key)
        return {
            "current_step": row.current_step if row else 1,
            "status": row.status if row else "ACTIVE",
        }


@router.put("/{portfolio_id}/onboarding")
def update_portfolio_onboarding(portfolio_id: UUID, body: PortfolioOnboardingUpdate):
    from income_analytics.infrastructure.database import SessionFactory
    from income_analytics.infrastructure.models import PortfolioOnboardingRecord

    viewer, wallet_id = _onboarding_key(portfolio_id)
    from sqlalchemy.dialects.sqlite import insert

    values = dict(
        viewer_key=viewer,
        portfolio_id=wallet_id,
        current_step=body.current_step,
        status=body.status,
        updated_at=int(time.time()),
    )
    with SessionFactory.begin() as db:
        statement = insert(PortfolioOnboardingRecord).values(**values)
        db.execute(
            statement.on_conflict_do_update(
                index_elements=["viewer_key", "portfolio_id"],
                set_={k: values[k] for k in ("current_step", "status", "updated_at")},
            )
        )
    return {"current_step": body.current_step, "status": body.status}


class ContextualOnboardingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal[
        "START",
        "INTENT",
        "DEFER_INTENT",
        "CLASS",
        "CONFIRM_ASSET",
        "EXPLORE",
        "SKIP",
        "DISMISS",
        "RESUME",
        "STEP",
    ]
    intent: Literal["STARTING", "EXISTING", "ORGANIZE"] | None = None
    asset_class: str | None = None
    analysis: Literal["composition", "evolution"] | None = None
    step: int | None = None


@router.get("/{portfolio_id}/onboarding-v2")
def get_contextual_onboarding(portfolio_id: UUID):
    from income_analytics.api.onboarding_v2 import read

    viewer, wallet = _onboarding_key(portfolio_id)
    portfolio = SqlitePortfolioRepository().get(portfolio_id)
    return read(viewer, wallet, portfolio.name)


@router.put("/{portfolio_id}/onboarding-v2")
def update_contextual_onboarding(portfolio_id: UUID, body: ContextualOnboardingUpdate):
    from income_analytics.api.onboarding_v2 import update

    viewer, wallet = _onboarding_key(portfolio_id)
    portfolio = SqlitePortfolioRepository().get(portfolio_id)
    return update(
        viewer,
        wallet,
        portfolio.name,
        str(current_principal().user_id) if saas_enabled() else None,
        body,
    )
