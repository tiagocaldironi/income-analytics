"""A committed delete must not wait for consolidation or load market history."""

from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from income_analytics import main
from income_analytics.api.routers import dashboard
from income_analytics.application.dashboard_refresh import DashboardRefreshQueue
from income_analytics.infrastructure.database import SessionFactory, engine
from income_analytics.infrastructure.models import FinancialEventRecord, SecurityAuditRecord
from income_analytics.infrastructure.sqlite_repositories import (
    SqlitePortfolioDashboardSnapshotRepository,
)


@pytest.fixture
def deletion_case(monkeypatch):
    client = TestClient(main.app)
    created = client.post("/api/portfolios", json={"name": "Delete latency " + uuid4().hex})
    assert created.status_code == 201
    portfolio_id = created.json()["id"]
    headers = {"X-Portfolio-Id": portfolio_id}
    response = client.post("/api/trades", headers=headers, json={
        "event_type": "BUY", "ticker": "FASTDEL", "quantity": "2", "unit_price": "10",
        "effective_date": "2026-07-13", "asset_class": "BRAZILIAN_STOCK",
    })
    assert response.status_code == 201, response.text
    with SessionFactory() as db:
        event_id = db.query(FinancialEventRecord).filter_by(portfolio_id=portfolio_id).one().id
    requests = []
    monkeypatch.setattr(dashboard._dashboard_refresh, "request", requests.append)
    return client, headers, UUID(portfolio_id), event_id, requests


def test_delete_commits_without_session_or_rebuild_and_invalidates_atomically(
    deletion_case, monkeypatch,
):
    client, headers, portfolio_id, event_id, queued = deletion_case

    def forbidden(*args, **kwargs):
        raise AssertionError("A deletion must not load/project the whole portfolio")

    monkeypatch.setattr(main, "PortfolioSession", forbidden)
    monkeypatch.setattr(dashboard, "rebuild_portfolio_dashboard_snapshot", forbidden)
    response = client.delete(f"/api/operations/{event_id}", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["deleted"] is True
    assert response.json()["dashboard_refresh"] == "UPDATING"
    assert queued == [portfolio_id]
    with SessionFactory() as db:
        assert db.get(FinancialEventRecord, event_id) is None
        assert db.query(SecurityAuditRecord).filter_by(
            action="USER_DELETED_OPERATION", evidence_ref=event_id,
            resource_id=str(portfolio_id),
        ).count() == 1
    repo = SqlitePortfolioDashboardSnapshotRepository(portfolio_id)
    assert repo.state()["status"] == "UPDATING"
    assert client.get("/api/portfolio/dashboard/status", headers=headers).json()[
        "status"
    ] == "UPDATING"
    # Read/status paths must also avoid reconstructing a full financial session.
    assert client.get("/api/portfolio/dashboard", headers=headers).json()["status"] == "UPDATING"


def test_delete_not_found_and_cross_portfolio_do_not_invalidate(deletion_case):
    client, headers, portfolio_id, event_id, queued = deletion_case
    other = client.post("/api/portfolios", json={"name": "Other " + uuid4().hex}).json()["id"]
    assert client.delete(f"/api/operations/{event_id}", headers={
        "X-Portfolio-Id": other,
    }).status_code == 404
    assert client.delete(f"/api/operations/{uuid4()}", headers=headers).status_code == 404
    assert not queued
    assert SqlitePortfolioDashboardSnapshotRepository(portfolio_id).state()["status"] == "VALID"


def test_retry_after_committed_delete_is_404_without_second_audit(deletion_case):
    client, headers, portfolio_id, event_id, queued = deletion_case
    assert client.delete(f"/api/operations/{event_id}", headers=headers).status_code == 200
    revision = SqlitePortfolioDashboardSnapshotRepository(portfolio_id).state()["version"]
    assert client.delete(f"/api/operations/{event_id}", headers=headers).status_code == 404
    assert queued == [portfolio_id]
    assert SqlitePortfolioDashboardSnapshotRepository(portfolio_id).state()["version"] == revision


def test_revision_fence_rejects_old_calculation_and_accepts_fresh_result(deletion_case):
    client, headers, portfolio_id, event_id, _ = deletion_case
    repo = SqlitePortfolioDashboardSnapshotRepository(portfolio_id)
    old_revision = repo.state()["version"]
    assert client.delete(f"/api/operations/{event_id}", headers=headers).status_code == 200
    assert not repo.save_if_version({"stale": True}, old_revision)
    assert not repo.fail_if_version(old_revision)
    revision = repo.state()["version"]
    fresh = dashboard._build_dashboard_for_portfolio(portfolio_id)
    assert repo.save_if_version(fresh, revision)
    assert repo.state()["status"] == "VALID"
    assert repo.get()["portfolio"]["positions"] == []


def test_failed_refresh_requires_explicit_retry_and_keeps_delete_committed(deletion_case):
    client, headers, portfolio_id, event_id, queued = deletion_case
    assert client.delete(f"/api/operations/{event_id}", headers=headers).status_code == 200
    repo = SqlitePortfolioDashboardSnapshotRepository(portfolio_id)
    assert repo.fail_if_version(repo.state()["version"])
    queued.clear()
    assert client.get("/api/portfolio/dashboard/status", headers=headers).json()[
        "status"
    ] == "ERROR"
    assert not queued  # Reading a failure must not start an endless retry loop.
    response = client.post("/api/portfolio/dashboard/status", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "UPDATING"
    assert queued == [portfolio_id]
    with SessionFactory() as db:
        assert db.get(FinancialEventRecord, event_id) is None


def test_schedule_failure_does_not_turn_committed_delete_into_error(deletion_case, monkeypatch):
    client, headers, portfolio_id, event_id, _ = deletion_case

    def unavailable(_):
        raise RuntimeError("Executor stopping")

    monkeypatch.setattr(dashboard._dashboard_refresh, "request", unavailable)
    response = client.delete(f"/api/operations/{event_id}", headers=headers)
    assert response.status_code == 200
    with SessionFactory() as db:
        assert db.get(FinancialEventRecord, event_id) is None
    assert SqlitePortfolioDashboardSnapshotRepository(portfolio_id).state()["status"] == "UPDATING"


def test_http_confirmation_precedes_slow_real_worker_and_final_snapshot_is_fresh(
    deletion_case, monkeypatch,
):
    client, headers, portfolio_id, event_id, _ = deletion_case
    entered, release, published = Event(), Event(), Event()
    repo = SqlitePortfolioDashboardSnapshotRepository(portfolio_id)

    def build(pid):
        entered.set()
        assert release.wait(5)
        return dashboard._build_dashboard_for_portfolio(pid)

    def save(_, payload, revision):
        saved = repo.save_if_version(payload, revision)
        if saved:
            published.set()
        return saved

    queue = DashboardRefreshQueue(
        state=lambda _: repo.state(), build=build, save=save,
        fail=lambda _, revision: repo.fail_if_version(revision),
    )
    monkeypatch.setattr(dashboard, "_dashboard_refresh", queue)
    try:
        response = client.delete(f"/api/operations/{event_id}", headers=headers)
        assert response.status_code == 200
        assert entered.wait(5)
        assert not release.is_set() and not published.is_set()
        assert repo.state()["status"] == "UPDATING"
        release.set()
        assert published.wait(5)
    finally:
        release.set()
        queue._executor.shutdown(wait=True)
    assert repo.get()["portfolio"]["positions"] == []


def test_invalidation_failure_rolls_back_delete_and_audit(deletion_case):
    client, headers, portfolio_id, event_id, queued = deletion_case
    # A real SQLite failure at the final invalidation step must abort the whole write.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TRIGGER deny_pending BEFORE UPDATE ON portfolio_dashboard_snapshot "
            f"WHEN NEW.portfolio_id='{portfolio_id}' AND NEW.status='UPDATING' "
            "BEGIN SELECT RAISE(ABORT,'synthetic write failure'); END"
        )
    try:
        with pytest.raises(IntegrityError, match="synthetic write failure"):
            client.delete(f"/api/operations/{event_id}", headers=headers)
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP TRIGGER deny_pending")
    assert not queued
    with SessionFactory() as db:
        assert db.get(FinancialEventRecord, event_id) is not None
        assert db.query(SecurityAuditRecord).filter_by(evidence_ref=event_id).count() == 0
    assert SqlitePortfolioDashboardSnapshotRepository(portfolio_id).state()["status"] == "VALID"
