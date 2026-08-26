"""
Base class for all financial effects.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class FinancialEffect(ABC):
    """
    Base class for all Financial Effects.

    A Financial Effect represents an immutable financial consequence
    produced by a Financial Event.

    Financial Effects are consumed by Business Engines such as the
    Position Engine, Income Engine and Performance Engine.

    They do not contain business logic or calculations.
    """

    financial_event_id: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.financial_event_id, UUID):
            raise TypeError("financial_event_id must be a UUID.")
