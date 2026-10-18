import logging
import os
from pathlib import Path
from threading import Thread
from time import perf_counter
from uuid import UUID

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

from income_analytics.api.routers.dashboard import (
    b3_import_router,
    ensure_portfolio_dashboard_snapshot_current,
    run_daily_market_data_refresh,
    run_daily_paid_income_sync,
    run_daily_recurring_rule_execution,
    run_reference_data_bootstrap,
    run_scheduled_historical_market_refresh,
)
from income_analytics.api.routers.dashboard import (
    router as dashboard_router,
)
from income_analytics.api.routers.health import router as health_router
from income_analytics.api.routers.portfolios import router as portfolios_router
from income_analytics.application.portfolio_context import (
    current_portfolio_id,
    reset_active_portfolio_id,
    reset_request_session,
    set_active_portfolio_id,
    set_request_session,
)
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.infrastructure.database import engine, initialize_database
from income_analytics.infrastructure.request_profiling import (
    current_request_metrics,
    install_sql_timing,
)
from income_analytics.infrastructure.sqlite_repositories import SqlitePortfolioRepository

app = FastAPI(
    title="Income Analytics",
    description="API para análise de investimentos",
    version="0.1.0",
)
logger = logging.getLogger(__name__)
performance_logger = logging.getLogger("uvicorn.error")

if os.environ.get("INCOME_ANALYTICS_PERF_LOG", "").strip().lower() in {"1", "true", "yes"}:
    install_sql_timing(engine)
    logging.getLogger().setLevel(logging.INFO)


@app.middleware("http")
async def portfolio_request_context(request, call_next):
    if request.url.path.startswith("/api/portfolios"):
        return await call_next(request)
    explicit_id = request.headers.get("x-portfolio-id")
    if explicit_id:
        try:
            portfolio_id = UUID(explicit_id)
        except ValueError:
            return JSONResponse({"detail": "Identificador de carteira inválido."}, status_code=400)
    else:
        portfolio_id = current_portfolio_id()
    portfolio = SqlitePortfolioRepository().get(portfolio_id)
    if portfolio is None:
        return JSONResponse({"detail": "Carteira não encontrada."}, status_code=404)
    if portfolio.status != "ACTIVE" and request.method not in {"GET", "HEAD", "OPTIONS"}:
        return JSONResponse({"detail": "Restaure a carteira antes de alterá-la."}, status_code=409)
    portfolio_token = set_active_portfolio_id(portfolio_id)
    session_token = set_request_session(
        PortfolioSession(portfolio_id=portfolio_id, persistent=True)
    )
    try:
        return await call_next(request)
    finally:
        reset_request_session(session_token)
        reset_active_portfolio_id(portfolio_token)


@app.middleware("http")
async def profile_request(request, call_next):
    enabled = os.environ.get("INCOME_ANALYTICS_PERF_LOG", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if not enabled:
        return await call_next(request)
    metrics = {"query_count": 0, "db_time_ms": 0.0, "query_started": []}
    token = current_request_metrics.set(metrics)
    started = perf_counter()
    try:
        response = await call_next(request)
    finally:
        current_request_metrics.reset(token)
    duration_ms = (perf_counter() - started) * 1000
    response_bytes = response.headers.get("content-length")
    try:
        response_size = int(response_bytes) if response_bytes is not None else None
    except ValueError:
        response_size = None
    route = getattr(request.scope.get("route"), "path", request.url.path)
    performance_logger.info(
        "request_perf route=%s method=%s status=%s total_ms=%.2f db_query_count=%s "
        "db_ms=%.2f response_bytes=%s other_ms=%.2f",
        route,
        request.method,
        response.status_code,
        duration_ms,
        metrics["query_count"],
        metrics["db_time_ms"],
        response_size,
        max(0.0, duration_ms - metrics["db_time_ms"]),
    )
    return response


initialize_database()

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(b3_import_router)
app.include_router(portfolios_router)


class NoCacheStaticFiles(StaticFiles):
    """Avoid stale frontend modules after a local backend update."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, max-age=0"
        return response


@app.on_event("startup")
def start_daily_data_refresh() -> None:
    # Rebuild only when the persisted read-model schema changes; ordinary restarts
    # should not replay the financial ledger or recalculate all-time performance.
    try:
        ensure_portfolio_dashboard_snapshot_current()
    except ValueError:
        # A damaged legacy portfolio projection must be observable without
        # preventing independent read-only product routes from starting.
        logger.exception(
            "Portfolio dashboard rebuild failed during startup; "
            "continuing with the last persisted projection."
        )
    if os.environ.get("INCOME_ANALYTICS_DISABLE_BACKGROUND_JOBS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        logger.info("Startup background jobs disabled for controlled performance run.")
        return
    Thread(target=run_daily_market_data_refresh, daemon=True).start()
    Thread(target=run_daily_recurring_rule_execution, daemon=True).start()
    Thread(target=run_daily_paid_income_sync, daemon=True).start()
    Thread(target=run_reference_data_bootstrap, daemon=True).start()
    Thread(target=run_scheduled_historical_market_refresh, daemon=True).start()


static_directory = Path(__file__).parent / "api" / "static"
app.mount("/static", NoCacheStaticFiles(directory=static_directory), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(static_directory / "index.html", headers={"Cache-Control": "no-store"})
