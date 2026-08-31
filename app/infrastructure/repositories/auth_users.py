from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import RoleName
from app.models import Role, User, UserRole


class SqlAlchemyAuthUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_by_email(self, email: str) -> User | None:
        normalized_email = email.strip().lower()
        result = await self._session.execute(
            select(User).where(func.lower(User.email) == normalized_email),
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_roles_for_user(self, user_id: UUID) -> tuple[RoleName, ...]:
        result = await self._session.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.name),
        )
        role_names = result.scalars().all()
        return tuple(
            role_name if isinstance(role_name, RoleName) else RoleName(role_name)
            for role_name in role_names
        )