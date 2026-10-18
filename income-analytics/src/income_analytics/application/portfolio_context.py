"""Stable composition-boundary identity for the existing local portfolio."""

from contextvars import ContextVar, Token
from uuid import NAMESPACE_URL, UUID, uuid5

MAIN_PORTFOLIO_ID = uuid5(NAMESPACE_URL, "income-analytics:portfolio:MAIN_PORTFOLIO:v1")


_active_portfolio_id: ContextVar[UUID] = ContextVar(
    "active_portfolio_id", default=MAIN_PORTFOLIO_ID
)


def current_portfolio_id() -> UUID:
    """Return the portfolio selected for this request (MAIN outside requests)."""
    return _active_portfolio_id.get()


def set_active_portfolio_id(portfolio_id: UUID) -> Token[UUID]:
    return _active_portfolio_id.set(portfolio_id)


def reset_active_portfolio_id(token: Token[UUID]) -> None:
    _active_portfolio_id.reset(token)


_request_session: ContextVar[object | None] = ContextVar("portfolio_session", default=None)


def set_request_session(session: object) -> Token[object | None]:
    return _request_session.set(session)


def reset_request_session(token: Token[object | None]) -> None:
    _request_session.reset(token)


def get_request_session() -> object | None:
    return _request_session.get()
