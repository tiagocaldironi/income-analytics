"""Evidence of the local trust model, NOT approval for public multiuser use.

These characterization tests deliberately prove missing authorization in an
isolated test database. Replace them with denial tests in the authorization PR.
"""

from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from income_analytics.main import app


@pytest.fixture
def installations():
    a, b = TestClient(app), TestClient(app)
    headers = []
    for client, label in [(a, "A1"), (a, "A2"), (b, "B1"), (b, "B2")]:
        r = client.post("/api/portfolios", json={"name": f"Audit {label} {uuid4().hex[:8]}"})
        assert r.status_code == 201, r.text
        headers.append({"X-Portfolio-Id": r.json()["id"]})
    return a, b, headers


def add_position(client, headers, ticker):
    r = client.post(
        "/api/trades",
        headers=headers,
        json={
            "event_type": "BUY",
            "ticker": ticker,
            "asset_class": "BRAZILIAN_STOCK",
            "quantity": "2",
            "unit_price": "10",
            "effective_date": date.today().isoformat(),
        },
    )
    assert r.status_code == 201, r.text


def test_no_authentication_and_client_selected_portfolio_are_not_user_authorization(installations):
    a, b, (a1, a2, b1, b2) = installations
    add_position(b, b1, "AUDITAUTH1")
    # No users exist: A/B are separate anonymous clients, not authenticated users.
    listed = a.get("/api/portfolios")
    assert listed.status_code == 200
    assert b1["X-Portfolio-Id"] in {p["id"] for p in listed.json()["portfolios"]}
    foreign = a.get("/api/portfolio", headers=b1)
    assert foreign.status_code == 200
    assert "AUDITAUTH1" in {p["ticker"] for p in foreign.json()["positions"]}
    forged = a.get("/api/portfolio", headers={**b1, "Authorization": "Bearer AUDIT-INVALID-TOKEN"})
    assert forged.status_code == 200, "The current app ignores authentication tokens"
    own = a.get("/api/portfolio", headers=a1)
    assert own.json()["positions"] == [], (
        "Portfolio scoping exists despite missing user authorization"
    )


def test_foreign_writes_delete_and_strategy_access_are_possible_if_portfolio_id_is_known(
    installations,
):
    a, b, (_, _, b1, _) = installations
    add_position(b, b1, "AUDITAUTH2")
    assert (
        a.post(
            "/api/external-flows",
            headers=b1,
            json={
                "event_type": "DEPOSIT",
                "amount": "1",
                "effective_date": date.today().isoformat(),
            },
        ).status_code
        == 201
    )
    assert (
        a.put(
            "/api/allocation-policy", headers=b1, json={"targets": {"BRAZILIAN_STOCK": "1"}}
        ).status_code
        == 200
    )
    assert a.get("/api/portfolio/allocation-analysis", headers=b1).status_code == 200
    assert (
        a.post(
            "/api/portfolio/simulation/contribution",
            headers=b1,
            json={
                "amount": "10",
                "mode": "STRATEGY_GUIDED",
                "include_asset_distribution": True,
            },
        ).status_code
        == 200
    )
    operations = b.get("/api/operations", headers=b1).json()["operations"]
    event_id = operations[0]["id"]
    # The wrong wallet blocks an ID, while a forged wallet header grants access.
    assert a.delete("/api/operations/" + event_id, headers=installations[2][0]).status_code == 404
    assert a.delete("/api/operations/" + event_id, headers=b1).status_code == 200
    assert len(b.get("/api/operations", headers=b1).json()["operations"]) == len(operations) - 1


def test_reserve_journey_private_expenses_are_readable_with_a_forged_portfolio_header(
    installations,
):
    a, b, (_, _, b1, _) = installations
    assert (
        b.put(
            "/api/income-starter/journey/reserve",
            headers=b1,
            json={
                "essential_monthly_expenses": "1000",
                "coverage_months": 6,
                "declared_reserved_amount": "250",
                "current_step": 2,
            },
        ).status_code
        == 200
    )
    read = a.get("/api/income-starter/journey/reserve", headers=b1)
    assert read.status_code == 200
    assert "1000" in str(read.json())


def test_reclassification_of_a_shared_asset_changes_the_other_portfolios_view(installations):
    a, b, (a1, _, b1, _) = installations
    add_position(a, a1, "AUDITSHARED")
    add_position(b, b1, "AUDITSHARED")
    assert (
        a.get("/api/portfolio", headers=a1).json()["positions"][0]["asset_class"]
        == "BRAZILIAN_STOCK"
    )
    changed = b.put("/api/assets/AUDITSHARED/class", headers=b1, json={"asset_class": "FII"})
    assert changed.status_code == 200, changed.text
    assert a.get("/api/portfolio", headers=a1).json()["positions"][0]["asset_class"] == "FII"
