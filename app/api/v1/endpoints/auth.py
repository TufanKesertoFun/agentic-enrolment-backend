import hashlib
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import (
    get_auth_user_repository,
    get_authentication_provider,
    get_current_user,
)
from app.auth.models import AuthenticatedUser
from app.auth.password import verify_password
from app.auth.provider import AuthenticationProvider
from app.core.exceptions import InvalidCredentialsException
from app.repositories.users import AuthUserRepository
from app.schemas.auth import AuthTokenResponse, CurrentUserResponse, LoginRequest
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}},
)
async def login(
    payload: LoginRequest,
    auth_provider: Annotated[AuthenticationProvider, Depends(get_authentication_provider)],
    user_repository: Annotated[AuthUserRepository, Depends(get_auth_user_repository)],
) -> AuthTokenResponse:
    user = await user_repository.get_user_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        logger.warning("event=LOGIN_FAILURE email_hash=%s", _email_hash(payload.email))
        raise InvalidCredentialsException()
    if not user.is_active:
        logger.warning("event=LOGIN_FAILURE reason=inactive_user user_id=%s", user.id)
        raise InvalidCredentialsException()

    token = auth_provider.create_access_token(user.id)
    logger.info("event=LOGIN_SUCCESS user_id=%s", user.id)
    return AuthTokenResponse(
        access_token=token.access_token,
        token_type="bearer",
        expires_in=token.expires_in,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    },
)
async def get_me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=current_user.user_id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        preferred_name=current_user.preferred_name,
        roles=sorted(current_user.roles, key=lambda role: role.value),
    )


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]