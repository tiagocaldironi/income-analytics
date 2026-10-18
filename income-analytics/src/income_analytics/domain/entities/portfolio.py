"""A portfolio is the ownership boundary for private investment data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Portfolio:
    id: UUID
    name: str
    base_currency: str = "BRL"
    status: str = "ACTIVE"
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)
