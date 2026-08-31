from typing import Protocol
from uuid import UUID

from app.auth.models import AccessToken, TokenIdentity


class AuthenticationProvider(Protocol):
    def create_access_token(self, user_id: UUID) -> AccessToken: ...

    def validate_access_token(self, token: str) -> TokenIdentity: ...


class AuthenticationProviderError(Exception):
    """Base class for authentication provider failures."""


class InvalidAccessTokenError(AuthenticationProviderError):
    """Raised when a token is malformed, incorrectly signed, or missing required claims."""


class AccessTokenExpiredError(AuthenticationProviderError):
    """Raised when a token has expired."""