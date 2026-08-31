import logging
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_provider import DevelopmentJwtAuthenticationProvider
from app.auth.models import AuthenticatedUser
from app.auth.provider import (
    AccessTokenExpiredError,
    AuthenticationProvider,
    InvalidAccessTokenError,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AuthenticationRequiredException,
    ExpiredTokenException,
    InvalidTokenException,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.repositories.auth_users import SqlAlchemyAuthUserRepository
from app.repositories.users import AuthUserRepository

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    bearerFormat="JWT",
    description="JWT bearer token issued by /api/v1/auth/login.",
)


def get_authentication_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticationProvider:
    return DevelopmentJwtAuthenticationProvider(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
    )


def get_auth_user_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuthUserRepository:
    return SqlAlchemyAuthUserRepository(session)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_provider: Annotated[AuthenticationProvider, Depends(get_authentication_provider)],
    user_repository: Annotated[AuthUserRepository, Depends(get_auth_user_repository)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        logger.warning("event=AUTH_TOKEN_INVALID reason=missing_bearer_token")
        raise AuthenticationRequiredException()

    try:
        token_identity = auth_provider.validate_access_token(credentials.credentials)
    except AccessTokenExpiredError as exc:
        logger.warning("event=AUTH_TOKEN_EXPIRED")
        raise ExpiredTokenException() from exc
    except InvalidAccessTokenError as exc:
        logger.warning("event=AUTH_TOKEN_INVALID")
        raise InvalidTokenException() from exc

    user = await user_repository.get_user_by_id(token_identity.user_id)
    if user is None:
        logger.warning(
            "event=AUTH_TOKEN_INVALID reason=user_not_found user_id=%s",
            token_identity.user_id,
        )
        raise InvalidTokenException()
    if not user.is_active:
        logger.warning("event=AUTH_TOKEN_INVALID reason=inactive_user user_id=%s", user.id)
        raise InvalidTokenException()

    roles = frozenset(await user_repository.get_roles_for_user(user.id))
    return AuthenticatedUser(
        user_id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        preferred_name=user.preferred_name,
        roles=roles,
    )