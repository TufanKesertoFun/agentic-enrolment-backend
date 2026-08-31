import logging
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import get_current_user
from app.auth.models import AuthenticatedUser
from app.core.exceptions import AccessDeniedException
from app.domain.enums import RoleName

logger = logging.getLogger(__name__)


def require_role(required_role: RoleName) -> Callable[..., Awaitable[AuthenticatedUser]]:
    return require_any_role(required_role)


def require_any_role(*required_roles: RoleName) -> Callable[..., Awaitable[AuthenticatedUser]]:
    if not required_roles:
        raise ValueError("At least one role is required")

    async def dependency(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if current_user.has_any_role(required_roles):
            return current_user

        logger.warning(
            "event=ACCESS_DENIED user_id=%s required_roles=%s actual_roles=%s",
            current_user.user_id,
            _role_values(required_roles),
            _role_values(current_user.roles),
        )
        raise AccessDeniedException()

    return dependency


def _role_values(roles: tuple[RoleName, ...] | frozenset[RoleName]) -> list[str]:
    return sorted(role.value for role in roles)