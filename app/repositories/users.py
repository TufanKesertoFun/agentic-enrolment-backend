from typing import Protocol
from uuid import UUID

from app.domain.enums import RoleName
from app.models import User


class AuthUserRepository(Protocol):
    async def get_user_by_email(self, email: str) -> User | None: ...

    async def get_user_by_id(self, user_id: UUID) -> User | None: ...

    async def get_roles_for_user(self, user_id: UUID) -> tuple[RoleName, ...]: ...