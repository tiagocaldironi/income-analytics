"""Stable composition-boundary identity for the existing local portfolio."""

from contextvars import ContextVar, Token
from uuid import NAMESPACE_URL, UUID, uuid5

MAIN_PORTFOLIO_ID = uuid5(NAMESPACE_URL, "income-analytics:portfolio:MAIN_PORTFOLIO:v1")


def current_portfolio_id() -> UUID:
    """Resolve the only portfolio exposed by the current product surface."""
    return MAIN_PORTFOLIO_ID


_request_session: ContextVar[object | None] = ContextVar("portfolio_session", default=None)


def set_request_session(session: object) -> Token[object | None]:
    return _request_session.set(session)


def reset_request_session(token: Token[object | None]) -> None:
    _request_session.reset(token)


def get_request_session() -> object | None:
    return _request_session.get()
