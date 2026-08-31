from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient, Response

from app.auth.dependencies import get_auth_user_repository
from app.auth.models import AuthenticatedUser
from app.auth.password import hash_password
from app.auth.permissions import require_any_role, require_role
from app.core.config import get_settings
from app.domain.enums import RoleName
from app.main import create_app
from app.models import User
from app.repositories.users import AuthUserRepository

TEST_JWT_SECRET = "unit-test-jwt-secret-value-with-at-least-32-bytes"
TEST_PASSWORD = "development-password"


class FakeAuthUserRepository:
    def __init__(
        self,
        users: list[User],
        roles_by_user_id: dict[UUID, tuple[RoleName, ...]],
    ) -> None:
        self._users_by_email = {user.email: user for user in users}
        self._users_by_id = {user.id: user for user in users}
        self._roles_by_user_id = roles_by_user_id

    async def get_user_by_email(self, email: str) -> User | None:
        return self._users_by_email.get(email.strip().lower())

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return self._users_by_id.get(user_id)

    async def get_roles_for_user(self, user_id: UUID) -> tuple[RoleName, ...]:
        return self._roles_by_user_id.get(user_id, ())


@pytest.fixture(scope="session")
def password_hash() -> str:
    return hash_password(TEST_PASSWORD)


@pytest.fixture
def auth_users(password_hash: str) -> dict[str, User]:
    return {
        "student": _user(
            email="demo.student@example.invalid",
            first_name="Demo",
            last_name="Student",
            password_hash=password_hash,
        ),
        "lecturer": _user(
            email="demo.lecturer@example.invalid",
            first_name="Demo",
            last_name="Lecturer",
            password_hash=password_hash,
        ),
        "enrolment": _user(
            email="demo.enrolment@example.invalid",
            first_name="Demo",
            last_name="Enrolment",
            password_hash=password_hash,
        ),
        "credit": _user(
            email="demo.credit@example.invalid",
            first_name="Demo",
            last_name="Credit",
            password_hash=password_hash,
        ),
        "admin": _user(
            email="demo.admin@example.invalid",
            first_name="Demo",
            last_name="Admin",
            password_hash=password_hash,
        ),
        "inactive": _user(
            email="demo.inactive@example.invalid",
            first_name="Demo",
            last_name="Inactive",
            password_hash=password_hash,
            is_active=False,
        ),
    }


@pytest.fixture
def auth_repository(auth_users: dict[str, User]) -> FakeAuthUserRepository:
    return FakeAuthUserRepository(
        users=list(auth_users.values()),
        roles_by_user_id={
            auth_users["student"].id: (RoleName.STUDENT,),
            auth_users["lecturer"].id: (RoleName.LECTURER,),
            auth_users["enrolment"].id: (RoleName.ENROLMENT_OFFICER,),
            auth_users["credit"].id: (RoleName.CREDIT_MAPPING_OFFICER,),
            auth_users["admin"].id: (RoleName.ADMINISTRATOR,),
            auth_users["inactive"].id: (RoleName.STUDENT,),
        },
    )


@pytest.fixture
def auth_app(
    monkeypatch: pytest.MonkeyPatch,
    auth_repository: FakeAuthUserRepository,
) -> Generator[FastAPI, None, None]:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    get_settings.cache_clear()

    app = create_app()

    def override_auth_user_repository() -> AuthUserRepository:
        return auth_repository

    app.dependency_overrides[get_auth_user_repository] = override_auth_user_repository

    @app.get("/test/admin")
    async def admin_only(
        current_user: Annotated[
            AuthenticatedUser,
            Depends(require_role(RoleName.ADMINISTRATOR)),
        ],
    ) -> dict[str, str]:
        return {"user_id": str(current_user.user_id)}

    @app.get("/test/staff")
    async def staff_only(
        current_user: Annotated[
            AuthenticatedUser,
            Depends(require_any_role(RoleName.LECTURER, RoleName.ENROLMENT_OFFICER)),
        ],
    ) -> dict[str, str]:
        return {"user_id": str(current_user.user_id)}

    yield app

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
async def auth_client(auth_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_valid_login_succeeds(auth_client: AsyncClient, auth_users: dict[str, User]) -> None:
    response = await _login(auth_client, "demo.student@example.invalid")

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert isinstance(body["access_token"], str)
    assert "password" not in body
    assert "password_hash" not in body

    payload = jwt.decode(body["access_token"], TEST_JWT_SECRET, algorithms=["HS256"])
    assert set(payload) == {"sub", "iat", "exp", "jti"}
    assert payload["sub"] == str(auth_users["student"].id)


async def test_invalid_password_returns_generic_401(auth_client: AsyncClient) -> None:
    response = await _login(auth_client, "demo.student@example.invalid", password="wrong")

    assert response.status_code == 401
    assert response.json() == _invalid_credentials_response()


async def test_unknown_email_returns_same_generic_credential_failure(
    auth_client: AsyncClient,
) -> None:
    invalid_password = await _login(auth_client, "demo.student@example.invalid", password="wrong")
    unknown_email = await _login(auth_client, "nobody@example.invalid", password=TEST_PASSWORD)

    assert unknown_email.status_code == 401
    assert unknown_email.json() == invalid_password.json() == _invalid_credentials_response()


async def test_missing_token_returns_401(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


async def test_malformed_token_returns_401(auth_client: AsyncClient) -> None:
    response = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


async def test_incorrectly_signed_token_returns_401(
    auth_client: AsyncClient,
    auth_users: dict[str, User],
) -> None:
    token = _token_for(
        auth_users["student"].id,
        secret="wrong-unit-test-secret-value-with-at-least-32-bytes",
    )

    response = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


async def test_expired_token_returns_401(
    auth_client: AsyncClient,
    auth_users: dict[str, User],
) -> None:
    token = _token_for(auth_users["student"].id, expires_delta=timedelta(minutes=-1))

    response = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


async def test_valid_token_calls_auth_me(
    auth_client: AsyncClient,
    auth_users: dict[str, User],
) -> None:
    response = await _get_me(auth_client, auth_users["student"].id)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(auth_users["student"].id)
    assert body["email"] == "demo.student@example.invalid"
    assert body["first_name"] == "Demo"
    assert body["last_name"] == "Student"
    assert body["preferred_name"] == "Demo"
    assert body["roles"] == ["STUDENT"]


async def test_auth_me_returns_trusted_persistence_roles(
    auth_client: AsyncClient,
    auth_users: dict[str, User],
) -> None:
    response = await _get_me(auth_client, auth_users["admin"].id)

    assert response.status_code == 200
    assert response.json()["roles"] == ["ADMINISTRATOR"]


async def test_inactive_user_is_rejected_even_with_valid_token(
    auth_client: AsyncClient,
    auth_users: dict[str, User],
) -> None:
    response = await _get_me(auth_client, auth_users["inactive"].id)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


@pytest.mark.parametrize(
    ("user_key", "expected_role"),
    [
        ("student", "STUDENT"),
        ("lecturer", "LECTURER"),
        ("enrolment", "ENROLMENT_OFFICER"),
        ("credit", "CREDIT_MAPPING_OFFICER"),
        ("admin", "ADMINISTRATOR"),
    ],
)
async def test_each_role_resolves_correctly(
    auth_client: AsyncClient,
    auth_users: dict[str, User],
    user_key: str,
    expected_role: str,
) -> None:
    response = await _get_me(auth_client, auth_users[user_key].id)

    assert response.status_code == 200
    assert response.json()["roles"] == [expected_role]


async def test_require_role_succeeds_when_role_is_present(
    auth_client: AsyncClient,
    auth_users: dict[str, User],
) -> None:
    token = _token_for(auth_users["admin"].id)

    response = await auth_client.get(
        "/test/admin",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"user_id": str(auth_users["admin"].id)}


async def test_require_role_returns_403_when_role_is_missing(
    auth_client: AsyncClient,
    auth_users: dict[str, User],
) -> None:
    token = _token_for(auth_users["student"].id)

    response = await auth_client.get(
        "/test/admin",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCESS_DENIED"


async def test_require_any_role_works_correctly(
    auth_client: AsyncClient,
    auth_users: dict[str, User],
) -> None:
    lecturer_token = _token_for(auth_users["lecturer"].id)
    enrolment_token = _token_for(auth_users["enrolment"].id)
    student_token = _token_for(auth_users["student"].id)

    lecturer_response = await auth_client.get(
        "/test/staff",
        headers={"Authorization": f"Bearer {lecturer_token}"},
    )
    enrolment_response = await auth_client.get(
        "/test/staff",
        headers={"Authorization": f"Bearer {enrolment_token}"},
    )
    student_response = await auth_client.get(
        "/test/staff",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert lecturer_response.status_code == 200
    assert enrolment_response.status_code == 200
    assert student_response.status_code == 403


async def test_password_hash_is_never_returned_from_auth_apis(
    auth_client: AsyncClient,
    auth_users: dict[str, User],
) -> None:
    login_response = await _login(auth_client, "demo.student@example.invalid")
    me_response = await _get_me(auth_client, auth_users["student"].id)

    assert "password_hash" not in login_response.text
    assert "password_hash" not in me_response.text
    assert TEST_PASSWORD not in login_response.text
    assert TEST_PASSWORD not in me_response.text


async def test_client_role_claims_cannot_grant_admin_privileges(
    auth_client: AsyncClient,
    auth_users: dict[str, User],
) -> None:
    forged_token = _token_for(
        auth_users["student"].id,
        extra_claims={"role": "ADMINISTRATOR", "roles": ["ADMINISTRATOR"]},
    )

    admin_response = await auth_client.get(
        "/test/admin",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    me_response = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {forged_token}"},
    )

    assert admin_response.status_code == 403
    assert me_response.status_code == 200
    assert me_response.json()["roles"] == ["STUDENT"]


async def test_openapi_exposes_auth_endpoints_and_bearer_security(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/auth/me" in schema["paths"]
    assert "BearerAuth" in schema["components"]["securitySchemes"]
    assert schema["components"]["securitySchemes"]["BearerAuth"]["type"] == "http"
    assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    assert schema["paths"]["/api/v1/auth/me"]["get"]["security"] == [{"BearerAuth": []}]


def _user(
    *,
    email: str,
    first_name: str,
    last_name: str,
    password_hash: str,
    is_active: bool = True,
) -> User:
    return User(
        id=uuid4(),
        email=email,
        first_name=first_name,
        last_name=last_name,
        preferred_name="Demo",
        password_hash=password_hash,
        is_active=is_active,
    )


def _token_for(
    user_id: UUID,
    *,
    secret: str = TEST_JWT_SECRET,
    expires_delta: timedelta = timedelta(minutes=60),
    extra_claims: dict[str, object] | None = None,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid4()),
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, secret, algorithm="HS256")


async def _login(
    client: AsyncClient,
    email: str,
    *,
    password: str = TEST_PASSWORD,
) -> Response:
    return await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


async def _get_me(client: AsyncClient, user_id: UUID) -> Response:
    token = _token_for(user_id)
    return await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})


def _invalid_credentials_response() -> dict[str, object]:
    return {
        "error": {
            "code": "INVALID_CREDENTIALS",
            "message": "Invalid email or password",
            "details": None,
        }
    }