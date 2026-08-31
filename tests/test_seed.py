import os

import pytest
from sqlalchemy import select

from app.auth.password import verify_password
from app.core.config import get_settings
from app.domain.enums import RoleName
from app.infrastructure.database.seed import (
    DEMO_STUDENT_EMAIL,
    DEMO_STUDENT_NUMBER,
    DEMO_USER_PASSWORD_REQUIRED_MESSAGE,
    build_development_seed_spec,
    resolve_demo_user_password,
    seed_development_data,
)
from app.infrastructure.database.session import get_engine, get_session_factory
from app.models import Role, Student, User, UserRole

DEVELOPMENT_PASSWORD = "development-password"


def test_development_seed_spec_contains_reference_data_and_fake_student() -> None:
    spec = build_development_seed_spec()

    assert {country.code for country in spec.countries} == {"AU", "DE", "TR", "US", "GB"}
    assert "STUDENT" in spec.roles
    assert "ADMINISTRATOR" in spec.roles
    assert spec.demo_student_number == DEMO_STUDENT_NUMBER == "11111"
    assert spec.demo_student_email == DEMO_STUDENT_EMAIL
    assert spec.demo_student_email.endswith(".invalid")
    assert len(spec.mock_historical_mappings) == 3
    assert all(
        mapping.source_course_code.startswith("MOCK-") for mapping in spec.mock_historical_mappings
    )


def test_development_seed_spec_contains_fake_auth_identities() -> None:
    spec = build_development_seed_spec()
    users_by_email = {user.email: user for user in spec.development_users}

    assert users_by_email["demo.student@example.invalid"].role == RoleName.STUDENT
    assert users_by_email["demo.lecturer@example.invalid"].role == RoleName.LECTURER
    assert users_by_email["demo.enrolment@example.invalid"].role == RoleName.ENROLMENT_OFFICER
    assert users_by_email["demo.credit@example.invalid"].role == RoleName.CREDIT_MAPPING_OFFICER
    assert users_by_email["demo.admin@example.invalid"].role == RoleName.ADMINISTRATOR
    assert all(email.endswith(".invalid") for email in users_by_email)


def test_development_seed_requires_explicit_demo_user_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEMO_USER_PASSWORD", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match=DEMO_USER_PASSWORD_REQUIRED_MESSAGE):
        resolve_demo_user_password()

    get_settings.cache_clear()


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL seed integration tests.",
)
async def test_development_seed_creates_retrievable_fake_student_in_postgresql() -> None:
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await seed_development_data(session, demo_user_password=DEVELOPMENT_PASSWORD)

        async with session_factory() as session:
            result = await session.execute(select(Student).where(Student.student_number == "11111"))
            student = result.scalar_one()

        assert student.student_number == "11111"
    finally:
        await _dispose_cached_database_engine()


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL seed integration tests.",
)
async def test_development_seed_creates_fake_users_with_hashed_passwords_and_roles() -> None:
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await seed_development_data(session, demo_user_password=DEVELOPMENT_PASSWORD)

        async with session_factory() as session:
            users_result = await session.execute(select(User))
            users = {user.email: user for user in users_result.scalars().all()}
            roles_result = await session.execute(
                select(User.email, Role.name)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id),
            )
            roles_by_email = {email: role for email, role in roles_result.all()}

        assert users["demo.admin@example.invalid"].password_hash is not None
        assert users["demo.admin@example.invalid"].password_hash != DEVELOPMENT_PASSWORD
        assert verify_password(
            DEVELOPMENT_PASSWORD,
            users["demo.admin@example.invalid"].password_hash,
        )
        assert roles_by_email["demo.student@example.invalid"] == RoleName.STUDENT
        assert roles_by_email["demo.lecturer@example.invalid"] == RoleName.LECTURER
        assert roles_by_email["demo.enrolment@example.invalid"] == RoleName.ENROLMENT_OFFICER
        assert roles_by_email["demo.credit@example.invalid"] == RoleName.CREDIT_MAPPING_OFFICER
        assert roles_by_email["demo.admin@example.invalid"] == RoleName.ADMINISTRATOR
    finally:
        await _dispose_cached_database_engine()


async def _dispose_cached_database_engine() -> None:
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
    get_engine.cache_clear()
    get_session_factory.cache_clear()