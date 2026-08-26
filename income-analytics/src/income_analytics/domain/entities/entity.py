from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(slots=True, eq=False, kw_only=True)
class Entity:
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise TypeError("Entity id must be a UUID.")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented

        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
