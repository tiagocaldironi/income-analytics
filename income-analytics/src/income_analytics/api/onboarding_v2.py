"""Presentation state only; financial facts are read from the existing persisted model."""

import json
import time
from decimal import Decimal, InvalidOperation
from typing import Protocol, TypedDict

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from income_analytics.infrastructure.database import SessionFactory
from income_analytics.infrastructure.models import FinancialEventRecord as FinancialEvent
from income_analytics.infrastructure.models import OnboardingEventV2Record as Event
from income_analytics.infrastructure.models import OnboardingJourneyV2Record as Journey
from income_analytics.infrastructure.models import OnboardingPreferenceV2Record as Preference
from income_analytics.infrastructure.models import PortfolioDashboardSnapshotRecord as Snapshot

CLASSES = {
    "BRAZILIAN_STOCK": "Ações brasileiras",
    "FII": "Fundos imobiliários",
    "BRAZILIAN_ETF": "ETFs brasileiros",
    "FIXED_INCOME": "Renda fixa",
    "INTERNATIONAL": "Ações internacionais",
    "INTERNATIONAL_ETF": "ETFs internacionais",
    "US_REIT": "REITs",
    "CRYPTO": "Criptomoedas",
    "OTHER": "Outros investimentos",
    "PENSION": "Previdência",
    "REAL_ESTATE": "Imóveis",
}
INTENTS = {"STARTING", "EXISTING", "ORGANIZE"}


class OnboardingFacts(TypedDict):
    has_current_investments: bool
    confirmed_investment: bool
    available_analyses: list[str]


class OnboardingAction(Protocol):
    @property
    def action(self) -> str: ...
    @property
    def intent(self) -> str | None: ...
    @property
    def asset_class(self) -> str | None: ...
    @property
    def analysis(self) -> str | None: ...
    @property
    def step(self) -> int | None: ...


def positive(value: object) -> bool:
    try:
        return Decimal(str(value)).is_finite() and Decimal(str(value)) > 0
    except InvalidOperation, ValueError:
        return False


def facts(db: Session, wallet: str) -> OnboardingFacts:
    row = db.scalar(select(Snapshot).where(Snapshot.portfolio_id == wallet))
    data = json.loads(row.payload) if row and row.status == "VALID" else {}
    assets = [
        a
        for g in data.get("holdings", {}).get("classes", [])
        for a in g.get("assets", [])
        if not a.get("target_only") and positive(a.get("quantity"))
    ]
    eligible = (
        db.scalar(
            select(FinancialEvent.id)
            .where(
                FinancialEvent.portfolio_id == wallet,
                FinancialEvent.asset_id.is_not(None),
                FinancialEvent.event_type == "BUY",
            )
            .limit(1)
        )
        is not None
    )
    analyses = []
    if (
        eligible
        and assets
        and all(a.get("market_value") is not None for a in assets)
        and positive(data.get("portfolio", {}).get("total_market_value"))
    ):
        analyses.append("composition")
    history = data.get("history", {})
    if (
        eligible
        and any(positive(point.get("market_value")) for point in history.get("snapshots", []))
        and history.get("history_boundary", {}).get("source") != "NO_OBSERVED_FINANCIAL_EVENTS"
    ):
        analyses.append("evolution")
    return {
        "has_current_investments": bool(assets),
        "confirmed_investment": eligible and bool(assets),
        "available_analyses": analyses,
    }


def emit(db: Session, viewer: str, wallet: str, name: str, now: int) -> None:
    db.execute(
        insert(Event)
        .values(viewer_key=viewer, portfolio_id=wallet, version=2, event_name=name, occurred_at=now)
        .on_conflict_do_nothing()
    )


def response(db: Session, viewer: str, wallet: str, name: str) -> dict[str, object]:
    pref = db.get(Preference, viewer)
    journey = db.get(Journey, (viewer, wallet))
    f = facts(db, wallet)
    intent = pref.intent if pref else None
    ask = not intent and not (pref and pref.deferred_at) and not f["confirmed_investment"]
    stage = journey.last_step if journey else (6 if f["confirmed_investment"] else 1 if ask else 2)
    if f["confirmed_investment"] and stage < 4:
        stage = 6
    if f["confirmed_investment"] and stage == 4:
        stage = 5
    if not f["confirmed_investment"] and stage >= 5:
        stage = 3
    analysis = bool(journey and journey.analysis_at)
    return {
        "version": 2,
        "portfolio_id": wallet,
        "portfolio_name": name,
        "intent": intent,
        "ask_intent": ask,
        "status": journey.status if journey else "ACTIVE",
        "last_step": stage,
        "selected_class": journey.selected_class if journey else None,
        "completed_at": journey.completed_at if journey else None,
        "dismissed_at": journey.dismissed_at if journey else None,
        "first_asset_earned_at": journey.first_asset_at if journey else None,
        "facts": f,
        "classes": [{"code": k, "label": v} for k, v in CLASSES.items()],
        "achievements": [
            {
                "id": "wallet_created",
                "title": "Carteira criada",
                "description": "Sua carteira está pronta para receber seus investimentos.",
                "state": "COMPLETED",
            },
            {
                "id": "first_investment",
                "title": "Primeiro investimento registrado",
                "description": "Um investimento confirmado na carteira atual.",
                "state": "COMPLETED"
                if f["confirmed_investment"]
                else "IN_PROGRESS"
                if stage == 4
                else "NOT_STARTED",
            },
            {
                "id": "analysis_explored",
                "title": "Primeira análise explorada",
                "description": "Uma interação com uma análise disponível.",
                "state": "COMPLETED"
                if analysis
                else "IN_PROGRESS"
                if f["confirmed_investment"]
                else "NOT_STARTED",
            },
        ],
    }


def read(viewer: str, wallet: str, name: str) -> dict[str, object]:
    with SessionFactory() as db:
        return response(db, viewer, wallet, name)


def update(
    viewer: str,
    wallet: str,
    name: str,
    owner: str | None,
    body: OnboardingAction,
) -> dict[str, object]:
    now = int(time.time())
    with SessionFactory.begin() as db:
        db.execute(
            insert(Journey)
            .values(
                viewer_key=viewer,
                portfolio_id=wallet,
                owner_user_id=owner,
                version=2,
                status="ACTIVE",
                last_step=1,
                updated_at=now,
            )
            .on_conflict_do_nothing()
        )
        journey = db.get(Journey, (viewer, wallet))
        assert journey is not None, "Onboarding insert did not persist its journey"
        f = facts(db, wallet)
        action = body.action
        if action == "START":
            emit(db, viewer, wallet, "onboarding_started", now)
            if f["confirmed_investment"] and journey.last_step < 4:
                journey.last_step = 6
        elif action in {"INTENT", "DEFER_INTENT"}:
            if action == "INTENT" and body.intent not in INTENTS:
                raise HTTPException(422, "Escolha uma intenção válida.")
            values = dict(
                viewer_key=viewer,
                owner_user_id=owner,
                version=2,
                intent=body.intent if action == "INTENT" else None,
                chosen_at=now if action == "INTENT" else None,
                deferred_at=now if action == "DEFER_INTENT" else None,
            )
            db.execute(
                insert(Preference)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=["viewer_key"],
                    set_={k: v for k, v in values.items() if k != "viewer_key"},
                )
            )
            journey.last_step = 6 if f["confirmed_investment"] else 2
            journey.status = "ACTIVE"
            if action == "INTENT":
                emit(db, viewer, wallet, "onboarding_intent_selected", now)
        elif action == "CLASS":
            if body.asset_class not in CLASSES:
                raise HTTPException(422, "Classe não suportada pelo cadastro.")
            journey.selected_class = body.asset_class
            journey.last_step = 4
            emit(db, viewer, wallet, "onboarding_first_asset_started", now)
        elif action == "CONFIRM_ASSET":
            if not f["confirmed_investment"]:
                raise HTTPException(409, "O investimento ainda não foi confirmado.")
            journey.first_asset_at = journey.first_asset_at or now
            journey.last_step = 5
            emit(db, viewer, wallet, "onboarding_first_asset_completed", now)
        elif action == "EXPLORE":
            if body.analysis not in f["available_analyses"]:
                raise HTTPException(409, "Esta análise ainda não está disponível.")
            journey.analysis_at = journey.analysis_at or now
            journey.first_asset_at = journey.first_asset_at or now
            journey.status = "COMPLETED"
            journey.completed_at = journey.completed_at or now
            journey.last_step = 6
            emit(db, viewer, wallet, "onboarding_analysis_explored", now)
            emit(db, viewer, wallet, "onboarding_completed", now)
        elif action in {"SKIP", "DISMISS", "RESUME"}:
            journey.status = {"SKIP": "SKIPPED", "DISMISS": "DISMISSED", "RESUME": "ACTIVE"}[action]
            if action == "DISMISS":
                journey.dismissed_at = now
            if action == "SKIP":
                emit(db, viewer, wallet, "onboarding_skipped", now)
            if action == "RESUME":
                journey.last_step = 6 if f["confirmed_investment"] else 2
        elif action == "STEP":
            if body.step not in {2, 3, 6}:
                raise HTTPException(422, "Etapa inválida.")
            if body.step == 6 and not f["confirmed_investment"]:
                raise HTTPException(409, "Cadastre um investimento primeiro.")
            journey.last_step = body.step
        journey.updated_at = now
        if f["confirmed_investment"]:
            journey.first_asset_at = journey.first_asset_at or now
        db.flush()
        db.expire_all()
        return response(db, viewer, wallet, name)
