"""Firebase-to-HttpOnly session exchange; no browser credentials are persisted."""

import json
import os
import secrets
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError

from income_analytics.infrastructure.auth_config import (
    cookie_name,
    origin,
    saas_enabled,
    secure_cookies,
    signup_enabled,
)
from income_analytics.infrastructure.auth_repository import (
    delete_session,
    resolve_identity,
    store_session,
)
from income_analytics.infrastructure.firebase_identity import identity_provider

router = APIRouter(prefix="/api/auth", tags=["Account"])
SESSION_SECONDS = 6 * 3600


def fresh_current_identity(request, token):
    try:
        claims = identity_provider.verify_id_token(token)
        if (
            claims["sub"] != request.state.principal.firebase_uid
            or claims.get("email_verified") is not True
            or not 0 <= time.time() - claims.get("auth_time", 0) <= 300
        ):
            raise ValueError("Fresh same-account access required")
        return claims
    except Exception as error:
        raise HTTPException(403, "Confirme um acesso recente à conta atual.") from error


def set_cookie(response: Response, kind: str, value: str, seconds: int):
    response.set_cookie(
        cookie_name(kind),
        value,
        max_age=seconds,
        httponly=True,
        secure=secure_cookies(),
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def require_firebase():
    if not saas_enabled():
        raise HTTPException(404, "Recurso indisponível no modo local.")


@router.get("/config")
def configuration():
    if not saas_enabled():
        return {"mode": "local"}
    return {
        "mode": "firebase",
        "signup_enabled": signup_enabled(),
        # These are public Firebase web identifiers, never Admin credentials.
        "firebase": {
            "apiKey": os.getenv("FIREBASE_WEB_API_KEY", ""),
            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
            "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
            "appId": os.getenv("FIREBASE_WEB_APP_ID", ""),
        },
        "emulator": os.getenv("FIREBASE_AUTH_EMULATOR_HOST")
        if os.getenv("INCOME_ENV") == "development"
        else None,
    }


@router.get("/csrf")
def csrf_token(request: Request, response: Response):
    require_firebase()
    # Reuse an existing session's token; other tabs must not invalidate its binding.
    token = request.cookies.get(cookie_name("csrf")) or secrets.token_urlsafe(32)
    set_cookie(response, "csrf", token, SESSION_SECONDS)
    return {"csrf_token": token}


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_token: str = Field(min_length=1, max_length=16000)


@router.post("/session")
def create_session(body: LoginInput, response: Response):
    require_firebase()
    try:
        claims = identity_provider.verify_id_token(body.id_token)
        if claims.get("email_verified") is not True:
            raise HTTPException(403, "Confirme seu e-mail antes de entrar.")
        if claims.get("firebase", {}).get("sign_in_provider") not in {"google.com", "password"}:
            raise HTTPException(403, "Utilize Google ou e-mail e senha.")
        if not 0 <= time.time() - claims.get("auth_time", 0) <= 300:
            raise HTTPException(401, "Entre novamente para iniciar uma sessão segura.")
        # Different token types have different Firebase issuers. The mapping is
        # always the verified project's identity issuer, not the session issuer.
        claims["iss"] = "https://securetoken.google.com/" + os.environ["FIREBASE_PROJECT_ID"]
        try:
            principal = resolve_identity(claims, create=True)
        except IntegrityError:
            principal = resolve_identity(claims)
        cookie = identity_provider.create_cookie(body.id_token, SESSION_SECONDS)
        if isinstance(cookie, bytes):
            cookie = cookie.decode()
        # Firebase can issue identical JWT cookies to the same user within one
        # second. A fresh local nonce ensures logout stays revoked even if an
        # identical Firebase JWT is issued again on a subsequent login.
        cookie = cookie + "~" + secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        store_session(cookie, principal, csrf, SESSION_SECONDS)
        set_cookie(response, "session", cookie, SESSION_SECONDS)
        set_cookie(response, "csrf", csrf, SESSION_SECONDS)
        return {"user_id": str(principal.user_id), "plan": "FREE"}
    except HTTPException:
        raise
    except Exception as error:
        # Never reflect Firebase's token or internal configuration errors.
        raise HTTPException(401, "Não foi possível validar o acesso. Entre novamente.") from error


@router.post("/logout")
def logout(request: Request, response: Response):
    require_firebase()
    cookie = request.cookies.get(cookie_name("session"), "")
    delete_session(cookie)
    for kind in ("session", "csrf"):
        response.delete_cookie(
            cookie_name(kind), path="/", secure=secure_cookies(), httponly=True, samesite="strict"
        )
    return {"signed_out": True}


@router.get("/me")
def account(request: Request):
    require_firebase()
    principal = request.state.principal
    return {
        "user_id": str(principal.user_id),
        "plan": "FREE",
        "capabilities": ["manual_portfolios", "analytics", "strategies", "simulations", "reports"],
        "origin": origin(),
    }


@router.post("/revoke")
def revoke_all(request: Request):
    require_firebase()
    from income_analytics.infrastructure.database import SessionFactory
    from income_analytics.infrastructure.models import AuthSessionRecord

    principal = request.state.principal
    # Remove local access first, even when Firebase cannot be reached.
    with SessionFactory.begin() as db:
        db.query(AuthSessionRecord).filter_by(user_id=str(principal.user_id)).delete()
    try:
        identity_provider.revoke(principal.firebase_uid)
    except Exception as error:
        raise HTTPException(
            503, "Acesso local encerrado. Tente encerrar outros acessos novamente."
        ) from error
    return {"revoked": True}


@router.post("/confirm-method")
def confirm_login_method(request: Request, body: LoginInput):
    from income_analytics.infrastructure.database import SessionFactory
    from income_analytics.infrastructure.models import AuthIdentityRecord

    claims = fresh_current_identity(request, body.id_token)
    method = claims.get("firebase", {}).get("sign_in_provider")
    with SessionFactory.begin() as db:
        row = (
            db.query(AuthIdentityRecord)
            .filter_by(
                user_id=str(request.state.principal.user_id),
                subject=claims["sub"],
                issuer="https://securetoken.google.com/" + os.environ["FIREBASE_PROJECT_ID"],
            )
            .one()
        )
        if method not in json.loads(row.approved_methods):
            raise HTTPException(403, "Confirme pelo método de acesso que você já utiliza.")
        row.link_confirmed_until = int(time.time()) + 120
    return {"confirmed": True}


@router.post("/authorize-method")
def authorize_login_method(request: Request, body: LoginInput):
    from income_analytics.infrastructure.auth_repository import audit
    from income_analytics.infrastructure.database import SessionFactory
    from income_analytics.infrastructure.models import AuthIdentityRecord

    claims = fresh_current_identity(request, body.id_token)
    try:
        methods = identity_provider.methods(claims["sub"])
    except Exception as error:
        raise HTTPException(403, "Não foi possível validar o método adicionado.") from error
    with SessionFactory.begin() as db:
        row = (
            db.query(AuthIdentityRecord)
            .filter_by(
                user_id=str(request.state.principal.user_id),
                subject=claims["sub"],
                issuer="https://securetoken.google.com/" + os.environ["FIREBASE_PROJECT_ID"],
            )
            .one()
        )
        changed = (
            db.query(AuthIdentityRecord)
            .filter(
                AuthIdentityRecord.id == row.id,
                AuthIdentityRecord.link_confirmed_until > int(time.time()),
            )
            .update(
                {"link_confirmed_until": 0, "approved_methods": json.dumps(sorted(set(methods)))},
                synchronize_session=False,
            )
        )
        if changed != 1:
            raise HTTPException(403, "Confirme novamente seu acesso antes de adicionar um método.")
        audit(db, row.user_id, "LOGIN_METHOD_LINKED")
    return {"linked": True}
