"""Opt-in request and SQL timing for reproducible local performance audits."""

from __future__ import annotations

from contextvars import ContextVar
from time import perf_counter
from typing import TypedDict

from sqlalchemy import Engine, event


class RequestMetrics(TypedDict):
    query_count: int
    db_time_ms: float
    query_started: list[float]


current_request_metrics: ContextVar[RequestMetrics | None] = ContextVar(
    "income_analytics_request_metrics", default=None
)
_profiled_engines: set[int] = set()


def install_sql_timing(engine: Engine) -> None:
    """Attach SQL timing once; listeners are inert when no request is profiled."""
    if id(engine) in _profiled_engines:
        return
    _profiled_engines.add(id(engine))

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(*_args: object) -> None:
        metrics = current_request_metrics.get()
        if metrics is None:
            return
        metrics["query_count"] += 1
        metrics["query_started"].append(perf_counter())

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(*_args: object) -> None:
        metrics = current_request_metrics.get()
        if metrics is None or not metrics["query_started"]:
            return
        metrics["db_time_ms"] += (perf_counter() - metrics["query_started"].pop()) * 1000
