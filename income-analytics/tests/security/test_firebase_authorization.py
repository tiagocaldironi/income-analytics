"""HTTP attack matrix with a deterministic IdP double; emulator tests are separate."""

import time
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from income_analytics.api.saas_security import (
    CURATOR_HANDLERS,
    PUBLIC,
    REFERENCE_HANDLERS,
    UNAVAILABLE_HANDLERS,
    api_routes,
)
from income_analytics.infrastructure.auth_config import cookie_name
from income_analytics.infrastructure.database import SessionFactory, initialize_database
from income_analytics.infrastructure.firebase_identity import identity_provider
from income_analytics.infrastructure.models import (
    AssetRecord,
    AuthSessionRecord,
    PortfolioRecord,
    SecurityRateLimitRecord,
    UserRecord,
)
from income_analytics.main import app

ORIGIN = "https://income.test"


@pytest.fixture
def saas(monkeypatch):
    initialize_database()
    monkeypatch.setenv("INCOME_AUTH_MODE", "firebase")
    monkeypatch.setenv("INCOME_APP_ORIGIN", ORIGIN)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "demo-unit-income")
    monkeypatch.setenv("INCOME_PUBLIC_SIGNUP_ENABLED", "1")
    with SessionFactory.begin() as db:
        db.query(SecurityRateLimitRecord).delete()
    tokens, cookies = {}, {}

    def verify(token, values):
        if token not in values:
            raise ValueError("Invalid/expired/revoked/disabled")
        return dict(values[token])

    def create_cookie(token, _seconds):
        cookie = uuid4().hex
        cookies[cookie] = tokens[token]
        return cookie

    monkeypatch.setattr(identity_provider, "verify_id_token", lambda t: verify(t, tokens))
    monkeypatch.setattr(identity_provider, "verify_cookie", lambda t: verify(t, cookies))
    monkeypatch.setattr(identity_provider, "verify_link_cookie", lambda t: verify(t, cookies))
    monkeypatch.setattr(identity_provider, "create_cookie", create_cookie)
    monkeypatch.setattr(identity_provider, "revoke", lambda _uid: cookies.clear())
    monkeypatch.setattr(identity_provider, "methods", lambda _uid: ["google.com", "password"])

    def login(*, uid=None, verified=True, provider="password", email="same@example.invalid"):
        token = uuid4().hex
        tokens[token] = {
            "sub": uid or uuid4().hex,
            "iss": "https://securetoken.google.com/demo-unit-income",
            "email": email,
            "email_verified": verified,
            "auth_time": time.time(),
            "firebase": {"sign_in_provider": provider},
        }
        client = TestClient(app, base_url=ORIGIN)
        csrf = client.get("/api/auth/csrf").json()["csrf_token"]
        client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": csrf})
        response = client.post("/api/auth/session", json={"id_token": token})
        if response.status_code == 200:
            csrf = client.get("/api/auth/csrf").json()["csrf_token"]
            client.headers["X-CSRF-Token"] = csrf
        return client, response, token

    return login, tokens, cookies


def wallet(client, label):
    response = client.post("/api/portfolios", json={"name": f"{label}-{uuid4().hex[:6]}"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def trade(client, wallet_id, ticker="SHARED3", **fields):
    payload = {
        "event_type": "BUY",
        "ticker": ticker,
        "quantity": "2",
        "unit_price": "10",
        "asset_class": "BRAZILIAN_STOCK",
        "effective_date": "2026-10-01",
        **fields,
    }
    return client.post("/api/trades", headers={"X-Portfolio-Id": wallet_id}, json=payload)


def test_two_users_four_wallets_scoped_lifecycle_and_no_main(saas):
    login, _, _ = saas
    a, ar, _ = login()
    b, br, _ = login()  # same email, different subjects must stay independent
    assert ar.status_code == br.status_code == 200
    assert ar.json()["user_id"] != br.json()["user_id"]
    a1, a2, b1, b2 = [wallet(c, n) for c, n in ((a, "A1"), (a, "A2"), (b, "B1"), (b, "B2"))]
    assert {p["id"] for p in a.get("/api/portfolios").json()["portfolios"]} == {a1, a2}
    assert {p["id"] for p in b.get("/api/portfolios").json()["portfolios"]} == {b1, b2}
    assert a.get("/api/portfolio").status_code == 400
    assert a.get("/api/portfolio", headers={"X-Portfolio-Id": b1}).status_code == 404
    assert a.patch(f"/api/portfolios/{b1}", json={"name": "stolen"}).status_code == 404
    assert a.post(f"/api/portfolios/{b1}/archive").status_code == 404
    assert trade(a, a1).status_code == 201
    assert trade(b, b1).status_code == 201
    assert a.get("/api/portfolio", headers={"X-Portfolio-Id": a2}).json()["positions"] == []
    assert b.get("/api/portfolio", headers={"X-Portfolio-Id": b2}).json()["positions"] == []


def test_every_registered_private_wallet_route_rejects_foreign_selection(saas):
    login, _, _ = saas
    a, _, _ = login()
    b, _, _ = login()
    foreign = wallet(b, "Foreign")
    tested = set()
    for route in api_routes(app.routes):
        if not isinstance(route, APIRoute) or route.path in PUBLIC:
            continue
        if route.path.startswith("/api/auth/") or route.name in REFERENCE_HANDLERS:
            continue
        if route.name in {"account_page", "list_portfolios", "create_portfolio"}:
            continue
        path = route.path
        for parameter in route.param_convertors:
            path = path.replace(
                "{" + parameter + "}", foreign if parameter == "portfolio_id" else str(uuid4())
            )
        for method in route.methods:
            response = a.request(method, path, headers={"X-Portfolio-Id": foreign}, json={})
            expected = {403} if route.name in (CURATOR_HANDLERS | UNAVAILABLE_HANDLERS) else {404}
            if route.name in {"get_data_sources", "list_market_price_refresh_runs"}:
                expected = {200}  # sanitized empty response, never the legacy log
            assert response.status_code in expected, (
                method,
                path,
                response.status_code,
                response.text,
            )
            tested.add((method, route.path))
    assert len(tested) >= 70


def test_anonymous_aliases_and_unknown_paths_never_expose_private_data(saas):
    client = TestClient(app, base_url=ORIGIN)
    for path in (
        "/api/portfolios",
        "/api/portfolio",
        "/api/operations",
        "/api/private-new",
        "/imports/b3/fake/apply",
        "/backup.db",
    ):
        assert client.get(path).status_code == 401, path
    assert client.get("/conta", follow_redirects=False).status_code == 303
    assert client.get("/docs").status_code == 404
    assert (
        client.get("/api/portfolio", headers={"Authorization": "Bearer forged"}).status_code == 401
    )
    assert client.get("/static/../income_analytics.db").status_code != 200


def test_csrf_host_body_size_and_cookies(saas):
    login, _, _ = saas
    a, response, _ = login()
    cookies = response.headers.get_list("set-cookie")
    assert all(
        "HttpOnly" in value and "Secure" in value and "SameSite=strict" in value
        for value in cookies
    )
    assert any("__Host-income_session=" in value for value in cookies)
    assert (
        a.post(
            "/api/portfolios", headers={"Origin": "https://evil.test"}, json={"name": "bad"}
        ).status_code
        == 403
    )
    assert (
        a.post(
            "/api/portfolios", headers={"X-CSRF-Token": "forged"}, json={"name": "bad"}
        ).status_code
        == 403
    )
    assert a.get("/api/portfolios", headers={"Host": "evil.test"}).status_code == 400
    assert a.post("/api/portfolios", content="x" * (128 * 1024 + 1)).status_code == 413
    assert "no-store" in a.get("/api/portfolios").headers["cache-control"]


def test_unverified_disabled_expired_and_logout_replay(saas):
    login, _, cookies = saas
    _, response, _ = login(verified=False)
    assert response.status_code == 403
    a, response, _ = login()
    user_id = response.json()["user_id"]
    cookie = a.cookies.get(cookie_name("session"))
    with SessionFactory.begin() as db:
        db.get(UserRecord, user_id).status = "SUSPENDED"
    assert a.get("/api/auth/me").status_code == 401
    with SessionFactory.begin() as db:
        db.get(UserRecord, user_id).status = "ACTIVE"
        db.query(AuthSessionRecord).filter_by(user_id=user_id).update({"expires_at": 0})
    assert a.get("/api/auth/me").status_code == 401
    a, _, _ = login()
    cookie = a.cookies.get(cookie_name("session"))
    assert a.post("/api/auth/logout").status_code == 200
    a.cookies.set(cookie_name("session"), cookie)
    assert a.get("/api/auth/me").status_code == 401
    a, _, _ = login()
    cookies.clear()  # IdP revocation/disabled account, not merely local deletion
    assert a.get("/api/auth/me").status_code == 401


def test_p0_global_classification_and_manual_prices_are_private(saas):
    login, _, _ = saas
    a, _, _ = login()
    b, _, _ = login()
    a1, b1 = wallet(a, "A"), wallet(b, "B")
    assert trade(a, a1, name="Private A name").status_code == 201
    assert trade(b, b1, name="Private B name").status_code == 201
    assert (
        a.put(
            "/api/assets/SHARED3/class", headers={"X-Portfolio-Id": a1}, json={"asset_class": "FII"}
        ).status_code
        == 200
    )
    b_view = b.get("/api/portfolio", headers={"X-Portfolio-Id": b1}).json()
    assert b_view["positions"][0]["asset_class"] == "BRAZILIAN_STOCK"
    assert "Private A name" not in str(b_view)
    before = b_view["positions"]
    response = a.put(
        "/api/market-prices/SHARED3",
        headers={"X-Portfolio-Id": a1},
        json={"current_price": "99", "effective_date": "2026-10-01"},
    )
    assert response.status_code == 200, response.text
    assert b.get("/api/portfolio", headers={"X-Portfolio-Id": b1}).json()["positions"] == before
    with SessionFactory() as db:
        records = db.query(AssetRecord).filter(AssetRecord.ticker.like("@%:SHARED3")).all()
        assert len(records) >= 2
    for method, path in (
        ("PUT", "/api/settings/paid-income"),
        ("GET", "/api/settings/paid-income"),
        ("POST", "/api/benchmarks/CDI"),
    ):
        assert a.request(method, path, headers={"X-Portfolio-Id": a1}, json={}).status_code == 403


def test_legacy_remains_unclaimed_and_unlisted(saas):
    login, _, _ = saas
    a, _, _ = login()
    assert (
        a.get(
            "/api/portfolio", headers={"X-Portfolio-Id": "7a54eeb7-542a-5832-8544-8be7dcb0237e"}
        ).status_code
        == 404
    )
    with SessionFactory() as db:
        assert db.get(PortfolioRecord, "7a54eeb7-542a-5832-8544-8be7dcb0237e").owner_user_id is None


def test_linking_requires_existing_method_and_same_uid(saas):
    login, tokens, _ = saas
    uid = uuid4().hex
    a, _, old = login(uid=uid)
    _, unapproved, new = login(uid=uid, provider="google.com")
    assert unapproved.status_code == 403
    assert a.post("/api/auth/confirm-method", json={"id_token": new}).status_code == 403
    _, _, foreign = login()
    assert a.post("/api/auth/confirm-method", json={"id_token": foreign}).status_code == 403
    assert a.post("/api/auth/authorize-method", json={"id_token": old}).status_code == 403
    assert a.post("/api/auth/confirm-method", json={"id_token": old}).status_code == 200
    assert a.post("/api/auth/authorize-method", json={"id_token": old}).status_code == 200
    assert a.post("/api/auth/authorize-method", json={"id_token": old}).status_code == 403
    assert login(uid=uid, provider="google.com")[1].status_code == 200


def test_reset_is_owned_and_allows_recreating_private_tickers(saas):
    login, _, _ = saas
    a, _, _ = login()
    b, _, _ = login()
    a1, b1 = wallet(a, "A-reset"), wallet(b, "B-preserved")
    assert trade(a, a1, ticker="RESET3").status_code == 201
    assert trade(b, b1, ticker="RESET3").status_code == 201
    before = b.get("/api/portfolio", headers={"X-Portfolio-Id": b1}).json()["positions"]
    assert (
        a.post(
            "/api/data/reset", headers={"X-Portfolio-Id": b1}, json={"confirmation": "EXCLUIR"}
        ).status_code
        == 404
    )
    assert (
        a.post(
            "/api/data/reset", headers={"X-Portfolio-Id": a1}, json={"confirmation": "EXCLUIR"}
        ).status_code
        == 200
    )
    assert trade(a, a1, ticker="RESET3").status_code == 201
    assert b.get("/api/portfolio", headers={"X-Portfolio-Id": b1}).json()["positions"] == before


def test_foreign_event_id_cannot_be_deleted_using_an_owned_wallet(saas):
    login, _, _ = saas
    a, _, _ = login()
    b, _, _ = login()
    a1, b1 = wallet(a, "A-event"), wallet(b, "B-event")
    assert trade(b, b1).status_code == 201
    headers = {"X-Portfolio-Id": b1}
    before = b.get("/api/operations", headers=headers).json()
    event_id = before["operations"][0]["id"]
    assert (
        a.delete(f"/api/operations/{event_id}", headers={"X-Portfolio-Id": a1}).status_code == 404
    )
    assert b.get("/api/operations", headers=headers).json() == before


def test_signup_kill_switch_and_recent_signin(saas, monkeypatch):
    login, tokens, _ = saas
    uid = uuid4().hex
    assert login(uid=uid)[1].status_code == 200
    monkeypatch.setenv("INCOME_PUBLIC_SIGNUP_ENABLED", "0")
    assert login(uid=uid)[1].status_code == 200
    assert login()[1].status_code == 403
    a, _, token = login(uid=uid)
    tokens[token]["auth_time"] = time.time() - 301
    assert a.post("/api/auth/session", json={"id_token": token}).status_code == 401
    assert (
        a.post(
            "/api/auth/session", json={"id_token": token, "income_roles": ["MARKET_CURATOR"]}
        ).status_code
        == 422
    )


def test_upload_archive_bombs_and_xml_entities_are_rejected():
    from io import BytesIO
    from zipfile import ZIP_DEFLATED, ZipFile

    from income_analytics.infrastructure.upload_safety import validate_workbook

    for xml in (b"<!DOCTYPE sheet [<!ENTITY secret 'x'>]><sheet/>", b"x" * (2 * 1024 * 1024)):
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            archive.writestr("xl/worksheets/sheet1.xml", xml)
        with pytest.raises(ValueError):
            validate_workbook(output.getvalue())


def test_rate_limit_shared_counter_and_production_emulator_guard(saas, monkeypatch):
    from fastapi import HTTPException

    from income_analytics.infrastructure.auth_config import validate_configuration
    from income_analytics.infrastructure.auth_repository import rate_limit

    key = uuid4().hex
    for _ in range(3):
        rate_limit(key, limit=3)
    with pytest.raises(HTTPException) as error:
        rate_limit(key, limit=3)
    assert error.value.status_code == 429
    monkeypatch.setenv("INCOME_ENV", "production")
    monkeypatch.setenv("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")
    with pytest.raises(RuntimeError):
        validate_configuration()


def test_logout_replay_stays_revoked_when_firebase_reissues_same_cookie(saas, monkeypatch):
    login, tokens, cookies = saas
    uid = uuid4().hex

    def identical_cookie(token, _seconds):
        cookies["identical-firebase-jwt"] = tokens[token]
        return "identical-firebase-jwt"

    monkeypatch.setattr(identity_provider, "create_cookie", identical_cookie)
    a, _, _ = login(uid=uid)
    old_cookie = a.cookies.get(cookie_name("session"))
    assert a.post("/api/auth/logout").status_code == 200
    b, _, _ = login(uid=uid)
    assert b.cookies.get(cookie_name("session")) != old_cookie
    a.cookies.set(cookie_name("session"), old_cookie)
    assert a.get("/api/auth/me").status_code == 401
    assert b.get("/api/auth/me").status_code == 200


def test_onboarding_metadata_is_persisted_and_isolated_without_financial_writes(saas):
    login, _, _ = saas
    a, ra, _ = login()
    b, rb, _ = login()
    assert ra.status_code == rb.status_code == 200
    a1, a2, b1 = wallet(a, "guide-a"), wallet(a, "guide-a2"), wallet(b, "guide-b")
    def path(key):
        return f"/api/portfolios/{key}/onboarding"

    before = a.get("/api/portfolio", headers={"X-Portfolio-Id": a1}).json()
    assert a.get(path(a1)).json() == {"current_step": 1, "status": "ACTIVE"}
    state = {"current_step": 3, "status": "SKIPPED"}
    assert a.put(path(a1), json=state).status_code == 200
    assert a.get(path(a1)).json() == state
    assert a.get(path(a2)).json() == {"current_step": 1, "status": "ACTIVE"}
    assert b.get(path(b1)).json() == {"current_step": 1, "status": "ACTIVE"}
    assert b.get(path(a1), headers={"X-Portfolio-Id": b1}).status_code == 404
    assert b.put(path(a1), json=state).status_code == 404
    assert a.put(path(a1), json={**state, "user_id": rb.json()["user_id"]}).status_code == 422
    assert a.put(path(a1), json={"current_step": 5, "status": "ACTIVE"}).status_code == 422
    assert a.put(path(a1), json={"current_step": 3, "status": "ACTIVE"}).status_code == 200
    assert a.get("/api/portfolio", headers={"X-Portfolio-Id": a1}).json() == before


def test_contextual_onboarding_intent_is_personal_progress_is_per_wallet(saas):
    login, tokens, _ = saas
    a,_,token=login();b,_,_=login()
    first=wallet(a,"onboard-a");second=wallet(a,"onboard-second");foreign=wallet(b,"onboard-b")
    path=f"/api/portfolios/{first}/onboarding-v2"
    initial=a.get(path).json()
    assert initial["ask_intent"] and initial["achievements"][0]["state"]=="COMPLETED"
    assert not initial["facts"]["confirmed_investment"]
    for client,w in ((a,foreign),(b,first)):
        assert client.get(f"/api/portfolios/{w}/onboarding-v2").status_code==404
        assert client.put(f"/api/portfolios/{w}/onboarding-v2",json={"action":"START"}).status_code==404
    assert a.put(path,json={"action":"INTENT","intent":"EXISTING","user_id":"forged"}).status_code==422
    assert a.put(path,json={"action":"INTENT","intent":"EXISTING"}).status_code==200
    assert a.get(path).json()["intent"]=="EXISTING"
    returning,session,_=login(uid=tokens[token]["sub"])
    assert session.status_code==200 and returning.get(path).json()["intent"]=="EXISTING"
    other=a.get(f"/api/portfolios/{second}/onboarding-v2").json()
    assert other["intent"]=="EXISTING" and not other["ask_intent"]
    assert other["status"]=="ACTIVE"
    assert a.put(path,json={"action":"CONFIRM_ASSET"}).status_code==409
    assert a.put(path,json={"action":"EXPLORE","analysis":"composition"}).status_code==409
    assert a.put(path,json={"action":"CLASS","asset_class":"FAKE_CLASS"}).status_code==422
    assert a.put(path,json={"action":"CLASS","asset_class":"FII"}).json()["last_step"]==4
    assert a.put(path,json={"action":"SKIP"}).json()["status"]=="SKIPPED"
    assert a.get(path).json()["status"]=="SKIPPED"
    assert a.put(path,json={"action":"RESUME"}).json()["status"]=="ACTIVE"
    assert a.put(path,json={"action":"DISMISS"}).json()["dismissed_at"] is not None
    assert a.get(f"/api/portfolios/{second}/onboarding-v2").json()["status"]=="ACTIVE"


def test_contextual_onboarding_confirmed_facts_events_and_deletion(saas):
    from sqlalchemy import select,func
    from income_analytics.infrastructure.models import OnboardingEventV2Record,FinancialEventRecord
    login,_,_=saas
    client,_,_=login();wid=wallet(client,"onboard-confirmed");path=f"/api/portfolios/{wid}/onboarding-v2"
    assert client.put(path,json={"action":"START"}).status_code==200
    assert client.put(path,json={"action":"START"}).status_code==200
    failed=trade(client,wid,ticker="ONBV2",quantity="-1")
    assert failed.status_code==422
    assert not client.get(path).json()["facts"]["confirmed_investment"]
    assert trade(client,wid,ticker="ONBV2").status_code==201
    loaded=client.get(path).json()
    assert loaded["facts"]["confirmed_investment"]
    assert loaded["achievements"][1]["state"]=="COMPLETED"
    assert loaded["facts"]["available_analyses"]==[]
    assert client.put('/api/market-prices/ONBV2',headers={"X-Portfolio-Id":wid},json={"current_price":"12","effective_date":"2026-10-01"}).status_code==200
    loaded=client.get(path).json()
    assert loaded["facts"]["available_analyses"]
    before=client.get('/api/portfolio',headers={"X-Portfolio-Id":wid}).json()
    assert client.put(path,json={"action":"CONFIRM_ASSET"}).json()["last_step"]==5
    for _ in range(2):
        result=client.put(path,json={"action":"EXPLORE","analysis":loaded["facts"]["available_analyses"][0]})
        assert result.status_code==200 and result.json()["status"]=="COMPLETED"
    assert client.get('/api/portfolio',headers={"X-Portfolio-Id":wid}).json()==before
    with SessionFactory() as db:
        assert db.scalar(select(func.count()).select_from(OnboardingEventV2Record).where(OnboardingEventV2Record.portfolio_id==wid,OnboardingEventV2Record.event_name=="onboarding_started"))==1
        assert db.scalar(select(func.count()).select_from(OnboardingEventV2Record).where(OnboardingEventV2Record.portfolio_id==wid,OnboardingEventV2Record.event_name=="onboarding_completed"))==1
        event_id=db.scalar(select(FinancialEventRecord.id).where(FinancialEventRecord.portfolio_id==wid))
    assert client.delete(f"/api/operations/{event_id}",headers={"X-Portfolio-Id":wid}).status_code==200
    deleted=client.get(path).json()
    assert not deleted["facts"]["has_current_investments"]
    assert deleted["achievements"][1]["state"]=="NOT_STARTED"
    assert deleted["first_asset_earned_at"] is not None


def test_contextual_onboarding_unauthenticated_and_csrf(saas):
    login,_,_=saas
    client,_,_=login();wid=wallet(client,"onboard-csrf");path=f"/api/portfolios/{wid}/onboarding-v2"
    assert TestClient(app,base_url=ORIGIN).get(path).status_code==401
    assert client.put(path,headers={"X-CSRF-Token":"forged"},json={"action":"START"}).status_code==403
    assert client.post('/api/auth/logout').status_code==200
    client.headers['X-CSRF-Token']=client.get('/api/auth/csrf').json()['csrf_token']
    assert client.put(path,json={"action":"START"}).status_code==401


def test_data_sources_exposes_only_public_catalog(saas):
    login, _, _ = saas
    client, response, _ = login()
    assert response.status_code == 200
    response = client.get("/api/data-sources")
    assert response.status_code == 200
    providers = response.json()["providers"]
    assert {item["provider"] for item in providers} == {"Brapi", "B3 COTAHIST", "BCB PTAX", "CoinGecko"}
    allowed = {"provider", "description", "status", "last_success", "next_execution", "execution_note", "group"}
    for item in providers:
        assert set(item) == allowed
        assert item["status"] == "UNKNOWN"
        assert item["last_success"] is None
        assert item["next_execution"] is None
    anonymous = TestClient(app, base_url=ORIGIN)
    assert anonymous.get("/api/data-sources").status_code == 401


def test_executable_simulation_owned_read_only_and_validated(saas):
    from datetime import date
    from decimal import Decimal
    from sqlalchemy import select, func
    from income_analytics.infrastructure.models import FinancialEventRecord
    login, _, _ = saas
    a, _, _ = login()
    b, _, _ = login()
    aid, bid = wallet(a, "plan-A"), wallet(b, "plan-B")
    assert trade(a, aid, ticker="PLAN3").status_code == 201
    headers = {"X-Portfolio-Id": aid}
    assert a.put("/api/market-prices/PLAN3", headers=headers, json={"current_price": "34.50", "effective_date": date.today().isoformat()}).status_code == 200
    assert a.put("/api/allocation-policy", headers=headers, json={"targets": {"BRAZILIAN_STOCK": "1"}}).status_code == 200
    assert a.put("/api/asset-allocation-policy", headers=headers, json={"targets": {"BRAZILIAN_STOCK": {"PLAN3": "1"}}}).status_code == 200
    path = "/api/portfolio/simulation/executable-contribution"
    before = a.get("/api/portfolio", headers=headers).json()
    with SessionFactory() as db:
        count = db.scalar(select(func.count()).select_from(FinancialEventRecord))
    response = a.post(path, headers=headers, json={"amount": "50"})
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["orders"][0]["quantity"] == "1"
    assert Decimal(plan["total_estimated"]) == Decimal("34.50")
    assert Decimal(plan["residual_amount"]) == Decimal("15.50")
    assert b.post(path, headers=headers, json={"amount": "50"}).status_code == 404
    assert a.post(path, headers={"X-Portfolio-Id": bid}, json={"amount": "50"}).status_code == 404
    assert a.post(path, json={"amount": "50"}).status_code == 400
    for payload in [
        {"amount": "0"}, {"amount": "NaN"}, {"amount": "0.001"},
        {"amount": "50", "unit_price": "1"},
        {"amount": "50", "rules": {"PLAN3": {"quantity_step": ".5"}}},
        {"amount": "50", "rules": {"PLAN3": {"fixed_fee_base": "-1"}}},
        {"amount": "50", "rules": {"OTHER3": {}}},
    ]:
        assert a.post(path, headers=headers, json=payload).status_code == 422, payload
    token = a.headers.pop("X-CSRF-Token")
    assert a.post(path, headers=headers, json={"amount": "50"}).status_code == 403
    a.headers["X-CSRF-Token"] = token
    assert a.get("/api/portfolio", headers=headers).json() == before
    with SessionFactory() as db:
        assert db.scalar(select(func.count()).select_from(FinancialEventRecord)) == count
