from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(slots=True, eq=False, kw_only=True)
class Entity:
    """
    Base class for domain entities.

    Equality is based on the entity identifier.
    """

    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        """Hook for subclasses."""
        pass

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return NotImplemented

        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)