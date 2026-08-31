from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.auth.models import AccessToken, TokenIdentity
from app.auth.provider import AccessTokenExpiredError, InvalidAccessTokenError

REQUIRED_CLAIMS = ["sub", "iat", "exp", "jti"]


class DevelopmentJwtAuthenticationProvider:
    def __init__(
        self,
        *,
        secret: str,
        algorithm: str,
        access_token_expire_minutes: int,
    ) -> None:
        self._secret = secret.strip()
        if not self._secret:
            raise RuntimeError(
                "JWT_SECRET must be configured before issuing or validating access tokens."
            )
        if access_token_expire_minutes < 1:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be at least 1")

        self._algorithm = algorithm
        self._expires_in = access_token_expire_minutes * 60

    def create_access_token(self, user_id: UUID) -> AccessToken:
        issued_at = datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=self._expires_in)
        claims: dict[str, Any] = {
            "sub": str(user_id),
            "iat": issued_at,
            "exp": expires_at,
            "jti": str(uuid4()),
        }
        token = jwt.encode(claims, self._secret, algorithm=self._algorithm)
        return AccessToken(access_token=token, token_type="bearer", expires_in=self._expires_in)

    def validate_access_token(self, token: str) -> TokenIdentity:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": REQUIRED_CLAIMS},
            )
        except ExpiredSignatureError as exc:
            raise AccessTokenExpiredError("Access token has expired") from exc
        except InvalidTokenError as exc:
            raise InvalidAccessTokenError("Access token is invalid") from exc

        return self._token_identity_from_payload(payload)

    @staticmethod
    def _token_identity_from_payload(payload: dict[str, Any]) -> TokenIdentity:
        try:
            user_id = UUID(str(payload["sub"]))
            issued_at = _timestamp_to_datetime(payload["iat"])
            expires_at = _timestamp_to_datetime(payload["exp"])
            jwt_id = str(payload["jti"])
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidAccessTokenError("Access token claims are invalid") from exc

        if not jwt_id:
            raise InvalidAccessTokenError("Access token claims are invalid")

        return TokenIdentity(
            user_id=user_id,
            issued_at=issued_at,
            expires_at=expires_at,
            jwt_id=jwt_id,
        )


def _timestamp_to_datetime(value: Any) -> datetime:
    if not isinstance(value, int | float):
        raise ValueError("JWT timestamp claim must be numeric")
    return datetime.fromtimestamp(value, tz=UTC)