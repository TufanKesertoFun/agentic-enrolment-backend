from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.enums import RoleName


@dataclass(frozen=True)
class AccessToken:
    access_token: str
    token_type: str
    expires_in: int


@dataclass(frozen=True)
class TokenIdentity:
    user_id: UUID
    issued_at: datetime
    expires_at: datetime
    jwt_id: str


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: UUID
    email: str
    first_name: str
    last_name: str
    preferred_name: str | None
    roles: frozenset[RoleName]

    def has_role(self, role: RoleName) -> bool:
        return role in self.roles

    def has_any_role(self, roles: Iterable[RoleName]) -> bool:
        return not self.roles.isdisjoint(frozenset(roles))