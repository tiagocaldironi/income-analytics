from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def now_utc() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """
    Base class for all domain events.

    Domain events describe something that happened inside the domain.
    They are immutable and are not persisted as Financial Events.
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None:
            raise ValueError("Domain event timestamp must be timezone-aware.")
