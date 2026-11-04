"""Rebuild committed dashboard revisions without holding up ledger writes."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar, copy_context
from logging import getLogger
from threading import RLock
from typing import TypedDict
from uuid import UUID

snapshot_revision: ContextVar[int | None] = ContextVar("snapshot_revision", default=None)
logger = getLogger(__name__)


class DashboardState(TypedDict):
    status: str
    version: int


class DashboardRefreshQueue:
    """Bounded workers, portfolio isolation and database compare-and-swap publication.

    Pending state is durable. The read/status endpoint resumes work after restart.
    A failed calculation never rolls back an already committed deletion.
    """

    def __init__(
        self, *, state: Callable[[UUID], DashboardState],
        build: Callable[[UUID], dict[str, object]],
        save: Callable[[UUID, dict[str, object], int], bool],
        fail: Callable[[UUID, int], bool],
    ) -> None:
        self._state, self._build, self._save, self._fail = state, build, save, fail
        self._lock = RLock()
        self._running: set[UUID] = set()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dashboard-refresh")

    def request(self, portfolio_id: UUID) -> None:
        with self._lock:
            if portfolio_id in self._running:
                return
            self._running.add(portfolio_id)
            try:
                self._executor.submit(copy_context().run, self._work, portfolio_id)
            except RuntimeError:
                self._running.discard(portfolio_id)
                raise

    def _work(self, portfolio_id: UUID) -> None:
        failed = False
        try:
            while True:
                state = self._state(portfolio_id)
                if state["status"] != "UPDATING":
                    return
                revision = state["version"]
                try:
                    payload = self._build(portfolio_id)
                    if self._save(portfolio_id, payload, revision):
                        return
                except Exception:
                    logger.exception("Dashboard refresh failed; committed ledger preserved")
                    if self._fail(portfolio_id, revision):
                        failed = True
                        return
                    # A newer committed revision superseded this failed build.
        finally:
            with self._lock:
                self._running.discard(portfolio_id)
                # Close the race between the last CAS and a newly queued deletion.
                if not failed and self._state(portfolio_id)["status"] == "UPDATING":
                    self.request(portfolio_id)
