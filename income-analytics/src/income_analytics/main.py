from fastapi import FastAPI

from income_analytics.api.routers.health import router as health_router

app = FastAPI(
    title="Income Analytics",
    description="API para análise de investimentos",
    version="0.1.0",
)

app.include_router(health_router)
