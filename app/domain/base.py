from dataclasses import dataclass
from typing import Any
from uuid import UUID


class DomainException(Exception):
    """Base exception for domain rule violations."""


@dataclass(frozen=True, slots=True)
class Entity:
    id: UUID

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id


@dataclass(frozen=True, slots=True)
class AggregateRoot(Entity):
    """Marker base for aggregate roots."""
