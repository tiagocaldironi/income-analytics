"""
Base class for auditable domain entities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from income_analytics.domain.entities.entity import Entity


def _now_utc() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(UTC)


@dataclass(slots=True, eq=False, kw_only=True)
class AuditableEntity(Entity):
    """
    Base class for entities that require audit information.

    Attributes
    ----------
    created_at:
        Timestamp when the entity was created.

    updated_at:
        Timestamp of the last modification.
    """

    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")

        if self.updated_at.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware.")

        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at.")

    def touch(self) -> None:
        """
        Update the modification timestamp.
        """
        self.updated_at = _now_utc()
