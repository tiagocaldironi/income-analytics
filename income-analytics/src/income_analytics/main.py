from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from income_analytics.api.routers.dashboard import router as dashboard_router
from income_analytics.api.routers.health import router as health_router
from income_analytics.infrastructure.database import initialize_database

app = FastAPI(
    title="Income Analytics",
    description="API para análise de investimentos",
    version="0.1.0",
)

initialize_database()

app.include_router(health_router)
app.include_router(dashboard_router)

static_directory = Path(__file__).parent / "api" / "static"
app.mount("/static", StaticFiles(directory=static_directory), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(static_directory / "index.html")
