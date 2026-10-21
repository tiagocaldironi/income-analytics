"""Read-only Income Starter catalog and gated template adoption API."""

from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from income_analytics.application.income_starter import (
    IncomeStarterError,
    catalog,
    reserve_journey,
)
from income_analytics.application.portfolio_context import current_portfolio_id
from income_analytics.domain.allocation_policy import AllocationPolicy
from income_analytics.domain.enums.asset_class import AssetClass

router = APIRouter(prefix="/api/income-starter", tags=["Income Starter"])


class AdoptModelInput(BaseModel):
    version: int
    allocations: dict[str, Decimal] | None = None


class ReserveJourneyProgressInput(BaseModel):
    essential_monthly_expenses: Decimal | None = None
    coverage_months: int = 6
    declared_reserved_amount: Decimal = Decimal(0)
    current_step: int = 1


@router.get("/catalog")
def list_income_starter_models() -> dict[str, object]:
    return {"models": catalog.list_catalog()}


@router.get("/journey/reserve")
def get_reserve_journey_progress() -> dict[str, object]:
    return reserve_journey.get(current_portfolio_id())


@router.put("/journey/reserve")
def save_reserve_journey_progress(body: ReserveJourneyProgressInput) -> dict[str, object]:
    try:
        return reserve_journey.save(
            current_portfolio_id(),
            essential_monthly_expenses=body.essential_monthly_expenses,
            coverage_months=body.coverage_months,
            declared_reserved_amount=body.declared_reserved_amount,
            current_step=body.current_step,
        )
    except IncomeStarterError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/active-strategy")
def get_active_strategy_metadata() -> dict[str, object]:
    return {"strategy": catalog.get_portfolio_strategy(current_portfolio_id())}


@router.get("/models/{template_key}")
def get_income_starter_model(template_key: str, version: int | None = None) -> dict[str, object]:
    model = catalog.get_version(template_key, version)
    if model is None:
        raise HTTPException(status_code=404, detail="Modelo não encontrado.")
    return model


@router.post("/models/{template_key}/adopt")
def adopt_income_starter_model(template_key: str, body: AdoptModelInput) -> dict[str, object]:
    model = catalog.get_version(template_key, body.version)
    if model is None:
        raise HTTPException(status_code=404, detail="Modelo não encontrado.")
    allocations = body.allocations or model["allocations"] or {}
    try:
        catalog.validate_for_adoption(template_key, body.version, allocations)
        policy = AllocationPolicy(
            targets={AssetClass(key): Decimal(value) for key, value in allocations.items()}
        )
        from income_analytics.api.routers.dashboard import (
            rebuild_portfolio_dashboard_snapshot,
            session,
        )

        session.set_allocation_policy(policy)
        adoption = catalog.adopt(current_portfolio_id(), template_key, body.version, allocations)
        rebuild_portfolio_dashboard_snapshot()
    except IncomeStarterError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"status": "adopted", "strategy": adoption}
