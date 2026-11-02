"""Local, bounded operational signals. Never collect request or financial payloads."""

from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
import time
from collections import Counter
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from income_analytics.infrastructure.auth_config import validate_database_path
from income_analytics.infrastructure.security_logging import redact

EVENTS = frozenset({
    "application_started", "application_startup_failed", "application_stopped",
    "database_unavailable", "schema_incompatible", "authentication_failed",
    "authorization_denied", "provider_unavailable", "import_failed", "backup_started",
    "backup_completed", "backup_failed", "restore_validation_failed", "health_degraded",
    "readiness_recovered", "monitoring_failed",
})


class Signals:
    """Fixed-cardinality counters and aggregates, process-local, no user labels."""

    def __init__(self) -> None:
        self.lock = Lock()
        self.counts: Counter[str] = Counter()
        self.duration_seconds = 0.0
        self.dependency_seconds = 0.0
        self.started_at = time.monotonic()
        self.started = False
        self.ready: bool | None = None

    def event(self, event: str, *, duration: float = 0.0) -> None:
        if event not in EVENTS or not 0 <= duration < 86400:
            raise ValueError("INVALID_OPERATIONAL_EVENT")
        with self.lock:
            self.counts[event] += 1
            count = self.counts[event]
        if event in {"authentication_failed", "authorization_denied", "import_failed"}:
            if count % 100 != 1:
                return
        record = {
            "timestamp": datetime.now(UTC).isoformat(), "severity": "INFO",
            "event_id": event, "component": "operations", "request_id": uuid4().hex,
            "duration_seconds": round(duration, 6),
            "aggregate_count": count,
        }
        # Reuse PR8 credential sanitization in addition to a strict field allowlist.
        logging.getLogger("income.operations").info(redact(json.dumps(record, sort_keys=True)))

    def request(self, status: int, duration: float, *, importing: bool = False) -> None:
        with self.lock:
            self.counts["requests"] += 1
            self.counts["http_5xx"] += int(status >= 500)
            self.duration_seconds += max(0.0, duration)
        event = {401: "authentication_failed", 403: "authorization_denied"}.get(status)
        if event:
            self.event(event)
        if importing and status >= 400:
            self.event("import_failed")

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            count = self.counts["requests"]
            return {
                "process_up": int(self.started),
                "uptime_seconds": round(time.monotonic() - self.started_at, 3),
                "counts": dict(self.counts),
                "http_5xx_rate": self.counts["http_5xx"] / count if count else 0.0,
                "request_mean_seconds": self.duration_seconds / count if count else 0.0,
                "dependency_mean_seconds": (
                    self.dependency_seconds / self.counts["dependency_checks"]
                    if self.counts["dependency_checks"] else 0.0
                ),
            }

    def dependency(self, duration: float) -> None:
        with self.lock:
            self.counts["dependency_checks"] += 1
            self.dependency_seconds += max(0.0, duration)


signals = Signals()


def readiness(database: Path, expected_revision: str, *, started: bool) -> str:
    """Read-only, bounded probe; never create a database, migrate or checkpoint WAL."""
    if not started:
        return "NOT_STARTED"
    try:
        database = validate_database_path(database)
        if not database.is_file():
            return "DATABASE_UNAVAILABLE"
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=0.1)) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("SELECT 1").fetchone()
            rows = db.execute("SELECT version_num FROM alembic_version").fetchall()
            if rows != [(expected_revision,)]:
                return "SCHEMA_INCOMPATIBLE"
        return "READY"
    except (OSError, RuntimeError, sqlite3.Error):
        return "DATABASE_UNAVAILABLE"


def expected_schema() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(Path(__file__).parents[3] / "alembic.ini"))
    head = ScriptDirectory.from_config(config).get_current_head()
    if not head:
        raise RuntimeError("SCHEMA_CONTRACT_UNAVAILABLE")
    return head


class OperationalMiddleware:
    """Public minimal health; detailed metrics require a separate operator credential.

    Installed outermost, so probes never open a financial portfolio session.
    Does not trust forwarded headers, paths, client request IDs or arbitrary labels.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        logger = logging.getLogger("income.operations")
        logger.setLevel(logging.INFO)
        if not logger.handlers and not logging.getLogger().handlers:
            logger.addHandler(logging.StreamHandler())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            async def lifecycle(message: Message) -> None:
                kind = message["type"]
                if kind == "lifespan.startup.complete":
                    signals.started = True
                    signals.event("application_started")
                elif kind == "lifespan.startup.failed":
                    signals.event("application_startup_failed")
                elif kind == "lifespan.shutdown.complete":
                    signals.started = False
                    signals.event("application_stopped")
                await send(message)
            await self.app(scope, receive, lifecycle)
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path in {"/health/live", "/health/ready", "/health/status"}:
            if scope.get("method") != "GET":
                await JSONResponse({"status": "method_not_allowed"}, status_code=405)(
                    scope, receive, send
                )
                return
            if path == "/health/status":
                key = os.getenv("INCOME_OPERATIONAL_TOKEN", "")
                headers = dict(scope.get("headers", []))
                supplied = headers.get(b"authorization", b"")
                if len(key) < 32 or not secrets.compare_digest(
                    supplied, ("Bearer " + key).encode("utf-8")
                ):
                    await JSONResponse({"status": "unauthorized"}, status_code=401)(
                        scope, receive, send
                    )
                    return
                await JSONResponse(signals.snapshot(), headers={"Cache-Control": "no-store"})(
                    scope, receive, send
                )
                return
            state = "LIVE"
            if path == "/health/ready":
                try:
                    state = readiness(
                        Path(os.getenv("INCOME_ANALYTICS_DATABASE", "income_analytics.db")),
                        expected_schema(), started=signals.started,
                    )
                except Exception:
                    state = "CONFIGURATION_UNAVAILABLE"
                ready = state == "READY"
                if ready != signals.ready:
                    signals.event("readiness_recovered" if ready else "health_degraded")
                    if state == "DATABASE_UNAVAILABLE":
                        signals.event("database_unavailable")
                    elif state == "SCHEMA_INCOMPATIBLE":
                        signals.event("schema_incompatible")
                    signals.ready = ready
            await JSONResponse(
                {"status": "ok" if state in {"LIVE", "READY"} else "unavailable"},
                status_code=200 if state in {"LIVE", "READY"} else 503,
                headers={"Cache-Control": "no-store"},
            )(scope, receive, send)
            return
        started, status = time.monotonic(), 500

        async def observe(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, observe)
        finally:
            try:
                signals.request(status, time.monotonic() - started, importing="/imports/" in path)
            except Exception:
                # A broken local collector must not interrupt a financial operation.
                logging.getLogger("income.operations").error("OPERATIONAL_MONITORING_FAILED")
