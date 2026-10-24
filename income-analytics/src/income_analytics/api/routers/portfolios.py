"""Lifecycle endpoints for local, single-user portfolios."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from income_analytics.application.portfolio_context import (
    MAIN_PORTFOLIO_ID,
    reset_active_portfolio_id,
    reset_request_session,
    set_active_portfolio_id,
    set_request_session,
)
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.entities.portfolio import Portfolio
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
        id=uuid4(), name=name, base_currency=currency, created_at=now, updated_at=now
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
