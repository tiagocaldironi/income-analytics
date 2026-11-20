"""SQLite contention must not prevent the HTTP loop from releasing a reader."""

import asyncio
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request
from starlette.responses import Response

from income_analytics.api.saas_security import authorize_request
from income_analytics.infrastructure import auth_repository
from income_analytics.infrastructure.models import SecurityRateLimitRecord


def test_http_rate_limit_allows_concurrent_reader_to_finish(tmp_path, monkeypatch):
    path = tmp_path / "contention.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}", connect_args={"timeout": 1})
    SecurityRateLimitRecord.__table__.create(engine)
    monkeypatch.setattr(auth_repository, "SessionFactory", sessionmaker(bind=engine))
    monkeypatch.setenv("INCOME_APP_ORIGIN", "https://income.test")
    reader = sqlite3.connect(path)
    reader.execute("BEGIN")
    reader.execute("SELECT * FROM security_rate_limits").fetchall()

    async def exercise():
        request = Request({
            "type": "http", "method": "GET", "scheme": "https", "path": "/health",
            "headers": [(b"host", b"income.test")], "server": ("income.test", 443),
            "client": ("127.0.0.1", 1234), "query_string": b"",
        })

        async def finish_reader():
            await asyncio.sleep(0.05)
            reader.rollback()

        async def next_handler(_request):
            return Response(status_code=200)

        async def unexpected_portfolio(_portfolio):
            raise AssertionError("Public health must not access a portfolio")

        release = asyncio.create_task(finish_reader())
        try:
            response = await authorize_request(
                request, next_handler, portfolio_handler=unexpected_portfolio,
            )
            assert response.status_code == 200
        finally:
            await release

    try:
        asyncio.run(exercise())
        assert reader.execute("SELECT count FROM security_rate_limits").fetchone() == (1,)
    finally:
        reader.close()
        engine.dispose()
