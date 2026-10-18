from datetime import date

from fastapi.testclient import TestClient

from income_analytics.main import app


def test_portfolio_lifecycle_and_explicit_request_isolation() -> None:
    client = TestClient(app)
    listed = client.get("/api/portfolios")
    assert listed.status_code == 200
    main = next(
        item for item in listed.json()["portfolios"]
        if item["id"] == "7a54eeb7-542a-5832-8544-8be7dcb0237e"
    )

    created = client.post("/api/portfolios", json={"name": "Household B"})
    assert created.status_code == 201
    portfolio_b = created.json()
    portfolio_b_id = portfolio_b["id"]
    assert portfolio_b["base_currency"] == "BRL"

    main_before = client.get("/api/portfolio", headers={"X-Portfolio-Id": main["id"]})
    assert main_before.status_code == 200

    empty_b = client.get("/api/portfolio", headers={"X-Portfolio-Id": portfolio_b_id})
    assert empty_b.status_code == 200
    assert empty_b.json()["positions"] == []

    trade = client.post(
        "/api/trades",
        headers={"X-Portfolio-Id": portfolio_b_id},
        json={
            "event_type": "BUY",
            "ticker": "MPV2B",
            "name": "Portfolio B test asset",
            "quantity": "3",
            "unit_price": "10",
            "effective_date": date(2026, 10, 18).isoformat(),
            "asset_class": "BRAZILIAN_STOCK",
        },
    )
    assert trade.status_code == 201

    main_after = client.get("/api/portfolio", headers={"X-Portfolio-Id": main["id"]})
    b_after = client.get("/api/portfolio", headers={"X-Portfolio-Id": portfolio_b_id})
    assert main_after.status_code == b_after.status_code == 200
    assert main_before.json()["positions"] == main_after.json()["positions"]
    assert "MPV2B" not in {item["ticker"] for item in main_after.json()["positions"]}
    assert "MPV2B" in {item["ticker"] for item in b_after.json()["positions"]}

    assert client.get("/api/portfolio", headers={"X-Portfolio-Id": "not-a-uuid"}).status_code == 400
    assert client.get(
        "/api/portfolio", headers={"X-Portfolio-Id": "11111111-1111-4111-8111-111111111111"}
    ).status_code == 404


def test_new_empty_portfolio_has_dashboard_and_holdings_read_models() -> None:
    client = TestClient(app)
    main_trade = client.post(
        "/api/trades",
        json={
            "event_type": "BUY",
            "ticker": "MPV2MAIN",
            "name": "Main portfolio only",
            "quantity": "2",
            "unit_price": "10",
            "effective_date": date(2026, 10, 18).isoformat(),
            "asset_class": "BRAZILIAN_STOCK",
        },
    )
    assert main_trade.status_code == 201, main_trade.text

    created = client.post("/api/portfolios", json={"name": "Empty dashboard"})
    assert created.status_code == 201
    headers = {"X-Portfolio-Id": created.json()["id"]}

    dashboard = client.get("/api/portfolio/dashboard", headers=headers)
    holdings = client.get("/api/portfolio/holdings", headers=headers)
    portfolio = client.get("/api/portfolio", headers=headers)

    assert dashboard.status_code == 200, dashboard.text
    assert holdings.status_code == 200, holdings.text
    assert portfolio.status_code == 200, portfolio.text
    assert dashboard.json()["portfolio"]["positions"] == portfolio.json()["positions"]
    assert portfolio.json()["positions"] == []
    assert "MPV2MAIN" not in {
        position["ticker"] for position in dashboard.json()["portfolio"]["positions"]
    }
    assert dashboard.json()["holdings"]["classes"] == []
    assert holdings.json()["classes"] == []


def test_archived_portfolio_is_read_only_and_can_be_restored() -> None:
    client = TestClient(app)
    created = client.post("/api/portfolios", json={"name": "Archive test"})
    portfolio_id = created.json()["id"]
    assert client.post(f"/api/portfolios/{portfolio_id}/archive").status_code == 200
    assert client.post(
        "/api/trades",
        headers={"X-Portfolio-Id": portfolio_id},
        json={
            "event_type": "BUY",
            "ticker": "MPV2A",
            "quantity": "1",
            "unit_price": "1",
            "effective_date": date(2026, 10, 18).isoformat(),
            "asset_class": "BRAZILIAN_STOCK",
        },
    ).status_code == 409
    assert client.post(f"/api/portfolios/{portfolio_id}/restore").status_code == 200


def test_portfolio_names_are_trimmed_and_active_names_are_unique() -> None:
    client = TestClient(app)
    first = client.post("/api/portfolios", json={"name": "  Side Portfolio  "})
    assert first.status_code == 201
    assert first.json()["name"] == "Side Portfolio"
    duplicate = client.post("/api/portfolios", json={"name": "side portfolio"})
    assert duplicate.status_code == 409
    assert client.patch(
        f"/api/portfolios/{first.json()['id']}", json={"name": "Renamed Side"}
    ).json()["name"] == "Renamed Side"
