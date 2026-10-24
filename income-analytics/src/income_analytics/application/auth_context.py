"""Request identity is server verified; a portfolio header is only a selector."""

from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: UUID
    firebase_uid: str
    roles: frozenset[str] = frozenset()


principal_context: ContextVar[Principal | None] = ContextVar("income_principal", default=None)


def current_principal() -> Principal | None:
    return principal_context.get()
