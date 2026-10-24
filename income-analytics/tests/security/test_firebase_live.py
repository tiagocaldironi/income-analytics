"""Explicitly opted-in cloud test; only newly created test identities are removed."""

import os
import secrets
from uuid import uuid4

import pytest
import requests
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    os.getenv("INCOME_RUN_FIREBASE_LIVE_TESTS") != "1",
    reason="Requires explicit cloud-test opt-in and fresh Admin credentials",
)


def test_live_password_sessions_and_two_user_isolation(monkeypatch):
    from firebase_admin import auth

    from income_analytics.infrastructure.database import initialize_database
    from income_analytics.infrastructure.firebase_identity import firebase_app
    from income_analytics.main import app

    assert os.environ.get("FIREBASE_PROJECT_ID") == "income-analytics-c0150"
    assert not os.environ.get("FIREBASE_AUTH_EMULATOR_HOST")
    # tests/conftest.py selects a fresh temporary SQLite before any app import.
    assert "income-analytics-pytest-" in os.environ["INCOME_ANALYTICS_DATABASE"]
    monkeypatch.setenv("INCOME_AUTH_MODE", "local")
    initialize_database()
    for key, value in {
        "INCOME_AUTH_MODE": "firebase",
        "INCOME_ENV": "development",
        "INCOME_APP_ORIGIN": "http://localhost:8002",
        "INCOME_PUBLIC_SIGNUP_ENABLED": "1",
    }.items():
        monkeypatch.setenv(key, value)
    created = []
    clients = []

    def session(token):
        client = TestClient(app, base_url="http://localhost:8002")
        clients.append(client)
        csrf = client.get("/api/auth/csrf").json()["csrf_token"]
        client.headers.update({"Origin": "http://localhost:8002", "X-CSRF-Token": csrf})
        response = client.post("/api/auth/session", json={"id_token": token})
        if response.status_code == 200:
            client.headers["X-CSRF-Token"] = client.get("/api/auth/csrf").json()["csrf_token"]
        return client, response

    def login(email, password):
        response = requests.post(
            "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword",
            params={"key": os.environ["FIREBASE_WEB_API_KEY"]},
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=30,
        )
        # Never include response bodies: successful bodies contain bearer tokens.
        assert response.status_code == 200, "Cloud password login failed"
        return response.json()["idToken"]

    try:
        accounts = []
        for _ in range(2):
            email = f"income-auth-test-{uuid4().hex}@example.invalid"
            password = secrets.token_urlsafe(32) + "Aa1!"
            user = auth.create_user(email=email, password=password, app=firebase_app())
            created.append(user.uid)
            _, rejected = session(login(email, password))
            assert rejected.status_code == 403
            # Administrative verification tests the gate; it does NOT test email delivery.
            auth.update_user(user.uid, email_verified=True, app=firebase_app())
            client, response = session(login(email, password))
            assert response.status_code == 200
            assert response.json()["user_id"] != user.uid
            accounts.append((client, user.uid))
        a, b = accounts[0][0], accounts[1][0]
        wallets = []
        for client, name in ((a, "Cloud A"), (b, "Cloud B")):
            response = client.post("/api/portfolios", json={"name": name})
            assert response.status_code == 201
            wallets.append(response.json()["id"])
        for client, own, foreign in ((a, wallets[0], wallets[1]), (b, wallets[1], wallets[0])):
            assert {p["id"] for p in client.get("/api/portfolios").json()["portfolios"]} == {own}
            assert (
                client.get("/api/portfolio", headers={"X-Portfolio-Id": foreign}).status_code == 404
            )
            assert (
                client.post(
                    "/api/portfolio/simulation/contribution",
                    headers={"X-Portfolio-Id": foreign},
                    json={"amount": "100"},
                ).status_code
                == 404
            )
        cookie = a.cookies.get("income_dev_session")
        assert a.post("/api/auth/logout").status_code == 200
        a.cookies.set("income_dev_session", cookie)
        assert a.get("/api/portfolios").status_code == 401
        auth.update_user(accounts[1][1], disabled=True, app=firebase_app())
        assert b.get("/api/portfolios").status_code == 401
    finally:
        for client in clients:
            client.close()
        for uid in created:
            auth.delete_user(uid, app=firebase_app())
