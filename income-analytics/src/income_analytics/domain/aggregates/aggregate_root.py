from __future__ import annotations

from abc import ABC

from income_analytics.domain.entities.entity import Entity
from income_analytics.domain.events.domain_event import DomainEvent


class AggregateRoot(Entity, ABC):
    """
    Base class for aggregate roots.

    Aggregate roots are responsible for maintaining business consistency
    and recording Domain Events generated during state changes.
    """

    def __post_init__(self) -> None:
        super().__post_init__()
        self._domain_events: list[DomainEvent] = []

    @property
    def domain_events(self) -> tuple[DomainEvent, ...]:
        """
        Returns an immutable view of recorded domain events.
        """
        return tuple(self._domain_events)

    def add_domain_event(self, event: DomainEvent) -> None:
        """
        Records a domain event.
        """
        self._domain_events.append(event)

    def clear_domain_events(self) -> None:
        """
        Removes every recorded domain event.
        """
        self._domain_events.clear()

    @property
    def has_domain_events(self) -> bool:
        """
        Indicates whether the aggregate contains pending domain events.
        """
        return bool(self._domain_events)
