from contextvars import ContextVar
from threading import Event, RLock
from uuid import uuid4

from income_analytics.application.dashboard_refresh import DashboardRefreshQueue


def test_consecutive_writes_cannot_publish_old_revision_and_requests_coalesce():
    portfolio = uuid4()
    entered, release, done = Event(), Event(), Event()
    lock = RLock()
    row = {"status": "UPDATING", "version": 1}
    builds, saved = [], []

    def state(_):
        with lock:
            return dict(row)

    def build(_):
        revision = row["version"]
        builds.append(revision)
        if len(builds) == 1:
            entered.set()
            assert release.wait(5)
        return {"ledger_revision": revision}

    def save(_, payload, revision):
        with lock:
            if row["version"] != revision:
                return False
            saved.append(payload)
            row.update(status="VALID", version=revision + 1)
            done.set()
            return True

    queue = DashboardRefreshQueue(state=state, build=build, save=save, fail=lambda *_: False)
    try:
        queue.request(portfolio)
        assert entered.wait(5)
        with lock:
            row["version"] = 2
        for _ in range(20):
            queue.request(portfolio)
        release.set()
        assert done.wait(5)
    finally:
        release.set()
        queue._executor.shutdown(wait=True)
    assert builds == [1, 2]
    assert saved == [{"ledger_revision": 2}]


def test_failed_build_marks_error_and_persisted_pending_resumes_with_new_queue():
    row = {"status": "UPDATING", "version": 3}
    done = Event()

    def fail(_, revision):
        assert revision == row["version"]
        row["status"] = "ERROR"
        done.set()
        return True

    def broken(_):
        raise ValueError("Synthetic projection error")

    queue = DashboardRefreshQueue(
        state=lambda _: dict(row), build=broken, save=lambda *_: False, fail=fail,
    )
    queue.request(uuid4())
    assert done.wait(5)
    queue._executor.shutdown(wait=True)
    assert row["status"] == "ERROR"
    # Simulate another committed write and process restart: no in-memory revision needed.
    row.update(status="UPDATING", version=4)
    saved = Event()

    def publish(_, payload, revision):
        assert payload == "fresh" and revision == 4
        row["status"] = "VALID"
        saved.set()
        return True

    recovered = DashboardRefreshQueue(
        state=lambda _: dict(row), build=lambda _: "fresh", save=publish, fail=fail,
    )
    recovered.request(uuid4())
    assert saved.wait(5)
    recovered._executor.shutdown(wait=True)
    assert row["status"] == "VALID"


def test_two_portfolios_keep_separate_context_and_pending_work():
    identity = ContextVar("synthetic_owner")
    first, second = uuid4(), uuid4()
    rows = {pid: {"status": "UPDATING", "version": 1} for pid in (first, second)}
    both_started, release, both_saved = Event(), Event(), Event()
    contexts, results = {}, {}
    lock = RLock()

    def build(pid):
        with lock:
            contexts[pid] = identity.get()
            if len(contexts) == 2:
                both_started.set()
        assert release.wait(5)
        return {"portfolio": pid}

    def save(pid, payload, revision):
        with lock:
            assert payload == {"portfolio": pid} and revision == 1
            results[pid] = payload
            rows[pid]["status"] = "VALID"
            if len(results) == 2:
                both_saved.set()
        return True

    queue = DashboardRefreshQueue(
        state=lambda pid: dict(rows[pid]), build=build, save=save, fail=lambda *_: False,
    )
    try:
        token = identity.set("owner-a")
        queue.request(first)
        identity.set("owner-b")
        queue.request(second)
        identity.reset(token)
        assert both_started.wait(5)
        release.set()
        assert both_saved.wait(5)
    finally:
        release.set()
        queue._executor.shutdown(wait=True)
    assert contexts == {first: "owner-a", second: "owner-b"}
