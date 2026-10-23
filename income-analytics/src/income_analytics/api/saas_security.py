"""Default-deny boundary for every route, including aliases and future handlers."""

import copy
import os
import secrets
from uuid import UUID

from fastapi import HTTPException
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Match, compile_path

from income_analytics.application.auth_context import principal_context
from income_analytics.infrastructure.auth_config import cookie_name, origin
from income_analytics.infrastructure.auth_repository import (
    digest,
    rate_limit,
    resolve_identity,
    validate_local_session,
)
from income_analytics.infrastructure.firebase_identity import identity_provider
from income_analytics.infrastructure.sqlite_repositories import SqlitePortfolioRepository

PUBLIC = {
    "/",
    "/health",
    "/api/auth/config",
    "/api/auth/csrf",
    "/api/auth/session",
    "/api/auth/logout",
    "/entrar",
    "/criar-conta",
    "/confirmar-email",
    "/recuperar-senha",
}
REFERENCE_HANDLERS = {
    "list_investment_tools",
    "magic_formula_stocks",
    "magic_formula_stock_detail",
    "magic_formula_fiis",
    "list_income_starter_models",
    "get_income_starter_model",
    "get_benchmark_observations",
    "search_assets",
}
CURATOR_HANDLERS = {
    "create_benchmark_rate",
    "refresh_benchmark",
    "refresh_fx_rate",
    "backfill_fx_rate_history",
    "refresh_historical_price_cache",
    "backfill_b3_etf_price_history",
    "backfill_market_price_history",
    "backfill_us_market_price_history",
    "backfill_crypto_market_price_history",
    "refresh_pension_vehicle",
}
UNAVAILABLE_HANDLERS = {
    "get_paid_income_settings",
    "update_paid_income_settings",
    "test_paid_income_connection",
    "sync_paid_income",
}


def api_routes(routes, prefix=""):
    """Flatten eager and lazy FastAPI includes, retaining effective URL prefixes.

    Unknown route types remain denied. The original router is never mutated.
    """
    for candidate in routes:
        included = getattr(candidate, "original_router", None)
        if included is not None:
            context = getattr(candidate, "include_context", None)
            nested_prefix = prefix + getattr(context, "prefix", "")
            yield from api_routes(included.routes, nested_prefix)
        elif isinstance(candidate, APIRoute):
            if prefix:
                candidate = copy.copy(candidate)
                candidate.path = prefix + candidate.path
                candidate.path_regex, candidate.path_format, candidate.param_convertors = (
                    compile_path(candidate.path)
                )
            yield candidate


def check_csrf(request, expected_hash: str | None = None):
    if request.headers.get("origin") != origin():
        raise HTTPException(403, "Origem da solicitação não permitida.")
    cookie = request.cookies.get(cookie_name("csrf"), "")
    supplied = request.headers.get("x-csrf-token", "")
    if len(supplied) < 32 or not secrets.compare_digest(cookie, supplied):
        raise HTTPException(403, "Atualize a página e tente novamente.")
    if expected_hash and not secrets.compare_digest(digest(supplied), expected_hash):
        raise HTTPException(403, "Atualize a sessão e tente novamente.")


async def bounded_body(request):
    # Enforced on the stream too: Content-Length is not trusted.
    maximum = 8 * 1024 * 1024 if "imports/" in request.url.path else 128 * 1024
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > maximum:
            raise HTTPException(413, "O arquivo ou solicitação excede o limite permitido.")
    request._body = bytes(body)


async def authorize_request(request, call_next, *, portfolio_handler):
    context_token = None
    try:
        # Trust neither arbitrary Host nor forwarded headers from untrusted peers.
        if str(request.base_url).rstrip("/") != origin():
            raise HTTPException(400, "Endereço de acesso inválido.")
        path = request.url.path
        if path.startswith("/static/"):
            return await call_next(request)
        if path in {"/docs", "/redoc", "/openapi.json"}:
            raise HTTPException(404, "Recurso não encontrado.")
        peer = request.client.host if request.client else "unknown"
        rate_limit("ip:" + peer, limit=300)
        if path.startswith("/api/auth/"):
            rate_limit("auth:" + peer, limit=40)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            await bounded_body(request)
            check_csrf(request)
        if path in PUBLIC:
            return await call_next(request)
        cookie = request.cookies.get(cookie_name("session"), "")
        if not cookie:
            raise HTTPException(401, "Entre na sua conta para continuar.")
        try:
            firebase_cookie, nonce = cookie.rsplit("~", 1)
            if len(nonce) < 32:
                raise ValueError("Invalid local session binding")
            if path == "/api/auth/authorize-method" and request.method == "POST":
                claims = await run_in_threadpool(
                    identity_provider.verify_link_cookie, firebase_cookie
                )
            else:
                claims = await run_in_threadpool(identity_provider.verify_cookie, firebase_cookie)
            if claims.get("email_verified") is not True:
                raise HTTPException(401, "Confirme seu e-mail para continuar.")
            claims["iss"] = "https://securetoken.google.com/" + os.environ["FIREBASE_PROJECT_ID"]
            principal = await run_in_threadpool(resolve_identity, claims)
            csrf_hash = await run_in_threadpool(validate_local_session, cookie, principal)
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(401, "Sessão inválida ou encerrada. Entre novamente.") from error
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            check_csrf(request, csrf_hash)
        rate_limit("user:" + str(principal.user_id), limit=240)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            rate_limit("write:" + str(principal.user_id), limit=60)
        if "imports/" in path and request.method == "POST":
            rate_limit("imports:" + str(principal.user_id), limit=20, seconds=86400)
        if (
            path.startswith("/api/assets/search")
            or "automatic" in path
            or path == "/api/market-prices/refresh"
        ):
            rate_limit("market:" + str(principal.user_id), limit=200, seconds=86400)
            rate_limit("market:platform", limit=5000, seconds=86400)
        request.state.principal = principal
        context_token = principal_context.set(principal)
        route, params = None, {}
        for candidate in api_routes(request.app.routes):
            match, scope = candidate.matches(request.scope)
            if match == Match.FULL and isinstance(candidate, APIRoute):
                route, params = candidate, scope.get("path_params", {})
                break
        if route is None:
            raise HTTPException(404, "Recurso não encontrado.")
        if route.name in UNAVAILABLE_HANDLERS:
            raise HTTPException(403, "Integração automática indisponível nesta fase.")
        if route.name in CURATOR_HANDLERS and "MARKET_CURATOR" not in principal.roles:
            raise HTTPException(403, "Esta ação exige curadoria de dados de mercado.")
        if route.name == "get_data_sources":
            return JSONResponse({"providers": []})
        if route.name == "list_market_price_refresh_runs":
            # Legacy run records are global and may contain private diagnostics.
            return JSONResponse({"runs": []})
        if (
            path.startswith("/api/auth/")
            or route.name in REFERENCE_HANDLERS
            or route.name == "account_page"
        ):
            return await call_next(request)
        repository = SqlitePortfolioRepository()
        if path == "/api/portfolios":
            return await call_next(request)
        selected = params.get("portfolio_id") or request.headers.get("x-portfolio-id")
        if not selected:
            raise HTTPException(400, "Selecione uma carteira.")
        try:
            portfolio_id = UUID(str(selected))
        except ValueError as error:
            raise HTTPException(400, "Identificador de carteira inválido.") from error
        portfolio = repository.get_owned(portfolio_id, principal.user_id)
        if portfolio is None:
            raise HTTPException(404, "Carteira não encontrada.")
        if path.startswith("/api/portfolios/"):
            return await call_next(request)
        return await portfolio_handler(portfolio_id)
    except HTTPException as error:
        if (
            error.status_code == 401
            and request.method == "GET"
            and request.url.path in {"/conta", "/primeiro-acesso"}
        ):
            return RedirectResponse("/entrar", status_code=303)
        return JSONResponse(
            {"detail": error.detail}, status_code=error.status_code, headers=error.headers
        )
    finally:
        if context_token is not None:
            principal_context.reset(context_token)
