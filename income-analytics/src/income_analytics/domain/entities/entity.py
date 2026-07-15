"""
Base class for all domain entities.
"""

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

    from typing import Self


    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented

        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)