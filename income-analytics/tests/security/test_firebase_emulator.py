"""Real Firebase Auth emulator + Admin SDK. Never connects to a paid project."""

import os
import time
from uuid import uuid4

import pytest
import requests
from fastapi.testclient import TestClient

from income_analytics.infrastructure.database import SessionFactory, initialize_database
from income_analytics.infrastructure.firebase_identity import firebase_app
from income_analytics.infrastructure.models import SecurityRateLimitRecord
from income_analytics.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("INCOME_RUN_FIREBASE_EMULATOR_TESTS") != "1",
    reason="Start official Auth emulator at 127.0.0.1:9099, then opt in",
)
EMULATOR = "http://127.0.0.1:9099"
ORIGIN = "http://localhost:8002"


def api(operation, payload):
    response = requests.post(
        f"{EMULATOR}/identitytoolkit.googleapis.com/v1/accounts:{operation}?key=emulator",
        json=payload,
        timeout=10,
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def emulator(monkeypatch):
    initialize_database()
    for key, value in {
        "INCOME_AUTH_MODE": "firebase",
        "INCOME_ENV": "development",
        "INCOME_APP_ORIGIN": ORIGIN,
        "FIREBASE_PROJECT_ID": "demo-income-saas",
        "FIREBASE_AUTH_EMULATOR_HOST": "127.0.0.1:9099",
        "INCOME_PUBLIC_SIGNUP_ENABLED": "1",
    }.items():
        monkeypatch.setenv(key, value)
    firebase_app.cache_clear()
    with SessionFactory.begin() as db:
        db.query(SecurityRateLimitRecord).delete()
    yield
    import firebase_admin

    firebase_admin.delete_app(firebase_app())
    firebase_app.cache_clear()


def start_client(token):
    client = TestClient(app, base_url=ORIGIN)
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": csrf})
    response = client.post("/api/auth/session", json={"id_token": token})
    if response.status_code == 200:
        client.headers["X-CSRF-Token"] = client.get("/api/auth/csrf").json()["csrf_token"]
    return client, response


def password_account():
    email, password = f"{uuid4().hex}@example.invalid", "Emulator-Test-Only-123!"
    account = api("signUp", {"email": email, "password": password, "returnSecureToken": True})
    return account, email, password


def verify_email_and_login(account, email, password):
    from firebase_admin import auth

    auth.update_user(account["localId"], email_verified=True, app=firebase_app())
    return api(
        "signInWithPassword", {"email": email, "password": password, "returnSecureToken": True}
    )


def test_real_two_firebase_users_register_verify_authenticate_and_isolate(emulator):
    aa, ae, ap = password_account()
    _, denied = start_client(aa["idToken"])
    assert denied.status_code == 403
    aa = verify_email_and_login(aa, ae, ap)
    ba, be, bp = password_account()
    ba = verify_email_and_login(ba, be, bp)
    a, ra = start_client(aa["idToken"])
    b, rb = start_client(ba["idToken"])
    assert ra.status_code == rb.status_code == 200, (ra.text, rb.text)
    assert ra.json()["user_id"] != rb.json()["user_id"]
    assert ra.json()["user_id"] != aa["localId"]
    wallets = []
    for client, name in ((a, "A1"), (a, "A2"), (b, "B1"), (b, "B2")):
        response = client.post("/api/portfolios", json={"name": name})
        assert response.status_code == 201, response.text
        wallets.append(response.json()["id"])
    a1, a2, b1, b2 = wallets
    for client, owned in ((a, {a1, a2}), (b, {b1, b2})):
        assert {p["id"] for p in client.get("/api/portfolios").json()["portfolios"]} == owned
    headers = {"X-Portfolio-Id": b1}
    trade = {
        "event_type": "BUY",
        "ticker": "EMUT3",
        "quantity": "2",
        "unit_price": "12",
        "asset_class": "BRAZILIAN_STOCK",
        "effective_date": "2026-10-01",
    }
    assert b.post("/api/trades", headers=headers, json=trade).status_code == 201
    for method, path, body in (
        ("GET", "/api/portfolio", None),
        ("POST", "/api/trades", trade),
        ("PUT", "/api/allocation-policy", {}),
        ("POST", "/api/portfolio/simulation/contribution", {"amount": "100"}),
        ("POST", f"/imports/b3/{uuid4()}/apply", None),
        ("POST", f"/api/imports/b3/{uuid4()}/apply", None),
    ):
        assert a.request(method, path, headers=headers, json=body).status_code == 404
    assert a.get("/api/portfolio").status_code == 400
    assert a.get("/api/portfolio", headers={"X-Portfolio-Id": a1}).json()["positions"] == []
    saved_cookie = a.cookies.get("income_dev_session")
    assert a.post("/api/auth/logout").status_code == 200
    a.cookies.set("income_dev_session", saved_cookie)
    assert a.get("/api/portfolios").status_code == 401
    from firebase_admin import auth

    auth.update_user(ba["localId"], disabled=True, app=firebase_app())
    assert b.get("/api/portfolios").status_code == 401


def test_real_google_provider_and_explicit_linking(emulator):
    # Emulator supports synthetic Google credentials. No real Google account is created.
    import json

    email = f"{uuid4().hex}@example.invalid"
    credential = json.dumps({"sub": uuid4().hex, "email": email, "email_verified": True})
    google = api(
        "signInWithIdp",
        {
            "postBody": "providerId=google.com&id_token=" + requests.utils.quote(credential),
            "requestUri": ORIGIN,
            "returnSecureToken": True,
        },
    )
    client, response = start_client(google["idToken"])
    assert response.status_code == 200, response.text
    assert client.get("/api/auth/me").status_code == 200
    assert (
        client.post("/api/auth/confirm-method", json={"id_token": google["idToken"]}).status_code
        == 200
    )
    linked = api(
        "update",
        {
            "idToken": google["idToken"],
            "email": email,
            "password": "Emulator-Link-123!",
            "returnSecureToken": True,
        },
    )
    # The server confirms Firebase's actual provider_data, not a browser-provided list.
    response = client.post("/api/auth/authorize-method", json={"id_token": linked["idToken"]})
    assert response.status_code == 200, response.text
    password = api(
        "signInWithPassword",
        {"email": email, "password": "Emulator-Link-123!", "returnSecureToken": True},
    )
    _, response = start_client(password["idToken"])
    assert response.status_code == 200, response.text


def test_real_sdk_revocation(emulator):
    from firebase_admin import auth

    account, email, password = password_account()
    account = verify_email_and_login(account, email, password)
    client, response = start_client(account["idToken"])
    assert response.status_code == 200
    # Firebase revocation compares whole seconds with auth_time.
    time.sleep(1.1)
    auth.revoke_refresh_tokens(account["localId"], app=firebase_app())
    assert client.get("/api/auth/me").status_code == 401


def test_real_email_verification_and_password_recovery_actions(emulator):
    account, email, password = password_account()
    api("sendOobCode", {"requestType": "VERIFY_EMAIL", "idToken": account["idToken"]})

    def code_for(kind):
        response = requests.get(
            f"{EMULATOR}/emulator/v1/projects/demo-income-saas/oobCodes", timeout=10
        )
        response.raise_for_status()
        codes = response.json()["oobCodes"]
        return next(
            code["oobCode"]
            for code in reversed(codes)
            if code["email"] == email and code["requestType"] == kind
        )

    api("update", {"oobCode": code_for("VERIFY_EMAIL")})
    account = api(
        "signInWithPassword", {"email": email, "password": password, "returnSecureToken": True}
    )
    client, response = start_client(account["idToken"])
    assert response.status_code == 200
    api("sendOobCode", {"requestType": "PASSWORD_RESET", "email": email})
    reset_code = code_for("PASSWORD_RESET")
    api("resetPassword", {"oobCode": reset_code})
    time.sleep(1.1)  # Firebase revocation timestamp precision is one second.
    api("resetPassword", {"oobCode": reset_code, "newPassword": "Recovered-Emulator-123!"})
    assert client.get("/api/auth/me").status_code == 401
    recovered = api(
        "signInWithPassword",
        {"email": email, "password": "Recovered-Emulator-123!", "returnSecureToken": True},
    )
    assert start_client(recovered["idToken"])[1].status_code == 200
