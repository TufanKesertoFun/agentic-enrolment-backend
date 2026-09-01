import os
from collections.abc import AsyncGenerator, Generator, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.api.dependencies import get_enrolment_repository, get_student_repository
from app.auth.dependencies import get_auth_user_repository
from app.auth.password import hash_password
from app.core.config import get_settings
from app.domain.enums import (
    CreditSystem,
    EnrolmentApplicationStatus,
    InstitutionType,
    RoleName,
    StudentStatus,
)
from app.infrastructure.database.seed import (
    DEMO_STUDENT_EMAIL,
    DEMO_STUDENT_NUMBER,
    seed_development_data,
)
from app.infrastructure.database.session import get_engine, get_session_factory
from app.main import create_app
from app.models import (
    Country,
    EnrolmentApplication,
    Institution,
    Program,
    Student,
    StudentProfile,
    User,
)
from app.repositories.enrolments import EnrolmentRepository
from app.repositories.students import StudentRepository
from app.repositories.users import AuthUserRepository

TEST_JWT_SECRET = "unit-test-jwt-secret-value-with-at-least-32-bytes"
TEST_PASSWORD = "development-password"


class TimestampedEntity(Protocol):
    created_at: datetime
    updated_at: datetime


class FakeAuthUserRepository:
    def __init__(
        self,
        users: Sequence[User],
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


class FakeStudentRepository:
    def __init__(
        self,
        students: Sequence[Student],
        profiles: Sequence[StudentProfile],
    ) -> None:
        self.students_by_id = {student.id: student for student in students}
        self.students_by_user_id = {student.user_id: student for student in students}
        self.students_by_institution_number = {
            (student.current_institution_id, student.student_number): student
            for student in students
        }
        self.profiles_by_student_id = {profile.student_id: profile for profile in profiles}
        self.country_ids = {student.home_country_id for student in students}
        self.country_ids.update(
            profile.country_id for profile in profiles if profile.country_id is not None
        )
        self.country_exists_calls: list[UUID] = []

    async def get_by_id(self, student_id: UUID) -> Student | None:
        return self.students_by_id.get(student_id)

    async def get_by_user_id(self, user_id: UUID) -> Student | None:
        return self.students_by_user_id.get(user_id)

    async def get_by_student_number(
        self,
        institution_id: UUID,
        student_number: str,
    ) -> Student | None:
        return await self.get_by_institution_and_student_number(institution_id, student_number)

    async def get_by_institution_and_student_number(
        self,
        institution_id: UUID,
        student_number: str,
    ) -> Student | None:
        return self.students_by_institution_number.get((institution_id, student_number.strip()))

    async def get_profile(self, student_id: UUID) -> StudentProfile | None:
        return self.profiles_by_student_id.get(student_id)

    async def country_exists(self, country_id: UUID) -> bool:
        self.country_exists_calls.append(country_id)
        return country_id in self.country_ids

    async def add(self, student: Student) -> Student:
        self.students_by_id[student.id] = student
        self.students_by_user_id[student.user_id] = student
        self.students_by_institution_number[
            (student.current_institution_id, student.student_number)
        ] = student
        return student

    async def save_profile(self, profile: StudentProfile) -> StudentProfile:
        _ensure_identity(profile)
        _ensure_timestamps(profile)
        self.profiles_by_student_id[profile.student_id] = profile
        return profile


class FakeEnrolmentRepository:
    def __init__(
        self,
        programs: Sequence[Program],
        applications: Sequence[EnrolmentApplication],
    ) -> None:
        self.programs_by_id = {program.id: program for program in programs}
        self.applications_by_id = {application.id: application for application in applications}

    async def get_application_by_id(self, application_id: UUID) -> EnrolmentApplication | None:
        return self.applications_by_id.get(application_id)

    async def list_applications_for_student(
        self,
        student_id: UUID,
    ) -> Sequence[EnrolmentApplication]:
        return await self.list_for_student(student_id)

    async def list_for_student(self, student_id: UUID) -> Sequence[EnrolmentApplication]:
        applications = [
            application
            for application in self.applications_by_id.values()
            if application.student_id == student_id
        ]
        return tuple(sorted(applications, key=lambda item: item.created_at, reverse=True))

    async def get_for_student(
        self,
        student_id: UUID,
        application_id: UUID,
    ) -> EnrolmentApplication | None:
        application = self.applications_by_id.get(application_id)
        if application is None or application.student_id != student_id:
            return None
        return application

    async def get_active_program(self, program_id: UUID) -> Program | None:
        program = self.programs_by_id.get(program_id)
        if program is None or not program.active:
            return None
        return program

    async def add_application(self, application: EnrolmentApplication) -> EnrolmentApplication:
        return await self.create(application)

    async def create(self, application: EnrolmentApplication) -> EnrolmentApplication:
        _ensure_identity(application)
        _ensure_timestamps(application)
        if application.status is None:
            application.status = EnrolmentApplicationStatus.DRAFT
        self.applications_by_id[application.id] = application
        return application

    async def save(self, application: EnrolmentApplication) -> EnrolmentApplication:
        _ensure_timestamps(application)
        self.applications_by_id[application.id] = application
        return application


@dataclass
class StudentApiState:
    users: dict[str, User]
    auth_repository: FakeAuthUserRepository
    student_repository: FakeStudentRepository
    enrolment_repository: FakeEnrolmentRepository
    country: Country
    institution: Institution
    program: Program
    student: Student
    other_student: Student
    draft_application: EnrolmentApplication
    submitted_application: EnrolmentApplication
    other_student_application: EnrolmentApplication

@pytest.fixture
def t005_state() -> StudentApiState:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    users = {
        "student": _user("demo.student@example.invalid"),
        "other_student": _user("other.student@example.invalid"),
        "lecturer": _user("demo.lecturer@example.invalid"),
        "admin": _user("demo.admin@example.invalid"),
    }
    country = _stamp(
        Country(id=uuid4(), code="AU", name="Australia", default_locale="en-AU", active=True),
        now,
    )
    institution = _stamp(
        Institution(
            id=uuid4(),
            country=country,
            country_id=country.id,
            name="Demo University",
            external_code="DEMO-AU",
            institution_type=InstitutionType.UNIVERSITY,
            active=True,
        ),
        now,
    )
    program = _stamp(
        Program(
            id=uuid4(),
            institution=institution,
            institution_id=institution.id,
            program_code="DEMO-BCOMP",
            name="Bachelor of Computer Science Demo Program",
            qualification_level="Bachelor",
            credit_system=CreditSystem.AU_CREDIT_POINTS,
            total_credits=Decimal("72.00"),
            active=True,
        ),
        now,
    )
    inactive_program = _stamp(
        Program(
            id=uuid4(),
            institution=institution,
            institution_id=institution.id,
            program_code="DEMO-INACTIVE",
            name="Inactive Demo Program",
            qualification_level="Bachelor",
            credit_system=CreditSystem.AU_CREDIT_POINTS,
            total_credits=Decimal("72.00"),
            active=False,
        ),
        now,
    )
    student = _stamp(
        Student(
            id=uuid4(),
            user_id=users["student"].id,
            student_number="11111",
            home_country=country,
            home_country_id=country.id,
            current_institution=institution,
            current_institution_id=institution.id,
            current_program=program,
            current_program_id=program.id,
            status=StudentStatus.ACTIVE,
        ),
        now,
    )
    other_student = _stamp(
        Student(
            id=uuid4(),
            user_id=users["other_student"].id,
            student_number="22222",
            home_country=country,
            home_country_id=country.id,
            current_institution=institution,
            current_institution_id=institution.id,
            current_program=program,
            current_program_id=program.id,
            status=StudentStatus.ACTIVE,
        ),
        now,
    )
    profile = _stamp(
        StudentProfile(
            id=uuid4(),
            student=student,
            student_id=student.id,
            date_of_birth=date(2000, 1, 2),
            phone="0400000000",
            address_line_1="1 Demo Street",
            city="Adelaide",
            state_region="SA",
            postal_code="5000",
            country=country,
            country_id=country.id,
        ),
        now,
    )
    draft_application = _stamp(
        EnrolmentApplication(
            id=uuid4(),
            student=student,
            student_id=student.id,
            program=program,
            program_id=program.id,
            status=EnrolmentApplicationStatus.DRAFT,
        ),
        now,
    )
    submitted_application = _stamp(
        EnrolmentApplication(
            id=uuid4(),
            student=student,
            student_id=student.id,
            program=program,
            program_id=program.id,
            status=EnrolmentApplicationStatus.SUBMITTED,
            submitted_at=now,
        ),
        now,
    )
    other_student_application = _stamp(
        EnrolmentApplication(
            id=uuid4(),
            student=other_student,
            student_id=other_student.id,
            program=program,
            program_id=program.id,
            status=EnrolmentApplicationStatus.DRAFT,
        ),
        now,
    )
    auth_repository = FakeAuthUserRepository(
        users=tuple(users.values()),
        roles_by_user_id={
            users["student"].id: (RoleName.STUDENT,),
            users["other_student"].id: (RoleName.STUDENT,),
            users["lecturer"].id: (RoleName.LECTURER,),
            users["admin"].id: (RoleName.ADMINISTRATOR,),
        },
    )
    student_repository = FakeStudentRepository(
        students=(student, other_student),
        profiles=(profile,),
    )
    enrolment_repository = FakeEnrolmentRepository(
        programs=(program, inactive_program),
        applications=(draft_application, submitted_application, other_student_application),
    )
    return StudentApiState(
        users=users,
        auth_repository=auth_repository,
        student_repository=student_repository,
        enrolment_repository=enrolment_repository,
        country=country,
        institution=institution,
        program=program,
        student=student,
        other_student=other_student,
        draft_application=draft_application,
        submitted_application=submitted_application,
        other_student_application=other_student_application,
    )


@pytest.fixture
def student_api_app(
    monkeypatch: pytest.MonkeyPatch,
    t005_state: StudentApiState,
) -> Generator[FastAPI, None, None]:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    get_settings.cache_clear()

    app = create_app()

    def override_auth_user_repository() -> AuthUserRepository:
        return t005_state.auth_repository

    def override_student_repository() -> StudentRepository:
        return t005_state.student_repository

    def override_enrolment_repository() -> EnrolmentRepository:
        return t005_state.enrolment_repository

    app.dependency_overrides[get_auth_user_repository] = override_auth_user_repository
    app.dependency_overrides[get_student_repository] = override_student_repository
    app.dependency_overrides[get_enrolment_repository] = override_enrolment_repository

    yield app

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
async def student_api_client(
    student_api_app: FastAPI,
) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=student_api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

async def test_student_can_get_students_me(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.get(
        "/api/v1/students/me",
        headers=_headers_for(t005_state.users["student"].id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(t005_state.student.id)
    assert body["student_number"] == "11111"
    assert body["status"] == "ACTIVE"
    assert body["home_country"] == {
        "id": str(t005_state.country.id),
        "code": "AU",
        "name": "Australia",
    }
    assert body["current_institution"]["id"] == str(t005_state.institution.id)
    assert body["current_program"]["id"] == str(t005_state.program.id)
    assert "password" not in response.text
    assert "password_hash" not in response.text


async def test_missing_jwt_returns_401(student_api_client: AsyncClient) -> None:
    response = await student_api_client.get("/api/v1/students/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


async def test_lecturer_cannot_use_student_self_endpoint(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.get(
        "/api/v1/students/me",
        headers=_headers_for(t005_state.users["lecturer"].id),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCESS_DENIED"


async def test_student_can_get_own_profile(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.get(
        "/api/v1/students/me/profile",
        headers=_headers_for(t005_state.users["student"].id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == str(t005_state.student.id)
    assert body["phone"] == "0400000000"
    assert body["city"] == "Adelaide"


async def test_student_can_patch_own_profile(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.patch(
        "/api/v1/students/me/profile",
        headers=_headers_for(t005_state.users["student"].id),
        json={"phone": "0411111111", "city": "Melbourne"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == str(t005_state.student.id)
    assert body["phone"] == "0411111111"
    assert body["city"] == "Melbourne"
    profile = t005_state.student_repository.profiles_by_student_id[t005_state.student.id]
    assert profile.phone == "0411111111"


async def test_student_can_save_valid_existing_country_id(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    profile = t005_state.student_repository.profiles_by_student_id[t005_state.student.id]
    profile.country_id = None

    response = await student_api_client.patch(
        "/api/v1/students/me/profile",
        headers=_headers_for(t005_state.users["student"].id),
        json={"country_id": str(t005_state.country.id)},
    )

    assert response.status_code == 200
    assert response.json()["country_id"] == str(t005_state.country.id)
    assert profile.country_id == t005_state.country.id


async def test_unknown_country_id_returns_404(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    unknown_country_id = uuid4()

    response = await student_api_client.patch(
        "/api/v1/students/me/profile",
        headers=_headers_for(t005_state.users["student"].id),
        json={"country_id": str(unknown_country_id)},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Country was not found",
            "details": None,
        }
    }


async def test_unknown_country_id_does_not_return_500(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.patch(
        "/api/v1/students/me/profile",
        headers=_headers_for(t005_state.users["student"].id),
        json={"country_id": str(uuid4())},
    )

    assert response.status_code != 500
    assert response.status_code == 404


async def test_null_country_id_remains_valid_and_clears_profile_country(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.patch(
        "/api/v1/students/me/profile",
        headers=_headers_for(t005_state.users["student"].id),
        json={"country_id": None},
    )

    profile = t005_state.student_repository.profiles_by_student_id[t005_state.student.id]
    assert response.status_code == 200
    assert response.json()["country_id"] is None
    assert profile.country_id is None
    assert t005_state.student_repository.country_exists_calls == []

async def test_student_cannot_change_restricted_student_fields(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.patch(
        "/api/v1/students/me/profile",
        headers=_headers_for(t005_state.users["student"].id),
        json={"student_number": "99999", "roles": ["ADMINISTRATOR"]},
    )

    assert response.status_code == 422
    assert t005_state.student.student_number == "11111"


async def test_student_can_create_draft_enrolment_application(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.post(
        "/api/v1/students/me/enrolment-applications",
        headers=_headers_for(t005_state.users["student"].id),
        json={"program_id": str(t005_state.program.id)},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "DRAFT"
    assert body["program_id"] == str(t005_state.program.id)


async def test_created_application_belongs_to_authenticated_student(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.post(
        "/api/v1/students/me/enrolment-applications",
        headers=_headers_for(t005_state.users["student"].id),
        json={"program_id": str(t005_state.program.id)},
    )

    assert response.status_code == 201
    application_id = UUID(response.json()["id"])
    application = t005_state.enrolment_repository.applications_by_id[application_id]
    assert application.student_id == t005_state.student.id


async def test_student_cannot_spoof_student_id(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    existing_count = len(t005_state.enrolment_repository.applications_by_id)

    response = await student_api_client.post(
        "/api/v1/students/me/enrolment-applications",
        headers=_headers_for(t005_state.users["student"].id),
        json={
            "program_id": str(t005_state.program.id),
            "student_id": str(t005_state.other_student.id),
        },
    )

    assert response.status_code == 422
    assert len(t005_state.enrolment_repository.applications_by_id) == existing_count


async def test_student_can_list_own_applications(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.get(
        "/api/v1/students/me/enrolment-applications",
        headers=_headers_for(t005_state.users["student"].id),
    )

    assert response.status_code == 200
    applications = response.json()
    assert {application["id"] for application in applications} == {
        str(t005_state.draft_application.id),
        str(t005_state.submitted_application.id),
    }
    assert all(
        application["student_id"] == str(t005_state.student.id) for application in applications
    )


async def test_student_can_read_own_application(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.get(
        f"/api/v1/students/me/enrolment-applications/{t005_state.draft_application.id}",
        headers=_headers_for(t005_state.users["student"].id),
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(t005_state.draft_application.id)


async def test_student_cannot_read_another_students_application(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.get(
        f"/api/v1/students/me/enrolment-applications/"
        f"{t005_state.other_student_application.id}",
        headers=_headers_for(t005_state.users["student"].id),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_student_can_submit_draft_application(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.post(
        f"/api/v1/students/me/enrolment-applications/{t005_state.draft_application.id}/submit",
        headers=_headers_for(t005_state.users["student"].id),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SUBMITTED"


async def test_submission_populates_submitted_at(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.post(
        f"/api/v1/students/me/enrolment-applications/{t005_state.draft_application.id}/submit",
        headers=_headers_for(t005_state.users["student"].id),
    )

    assert response.status_code == 200
    assert response.json()["submitted_at"] is not None
    assert t005_state.draft_application.submitted_at is not None


async def test_submitting_again_returns_409(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    url = f"/api/v1/students/me/enrolment-applications/{t005_state.draft_application.id}/submit"
    first_response = await student_api_client.post(
        url,
        headers=_headers_for(t005_state.users["student"].id),
    )
    second_response = await student_api_client.post(
        url,
        headers=_headers_for(t005_state.users["student"].id),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json()["error"]["code"] == "CONFLICT"


async def test_student_cannot_set_approved_status(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.post(
        "/api/v1/students/me/enrolment-applications",
        headers=_headers_for(t005_state.users["student"].id),
        json={"program_id": str(t005_state.program.id), "status": "APPROVED"},
    )

    assert response.status_code == 422


async def test_authorized_staff_can_search_student_by_institution_and_number(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.get(
        f"/api/v1/institutions/{t005_state.institution.id}/students/11111",
        headers=_headers_for(t005_state.users["lecturer"].id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["student_number"] == "11111"
    assert "profile" not in body
    assert "documents" not in body


async def test_student_cannot_use_staff_search_endpoint(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    response = await student_api_client.get(
        f"/api/v1/institutions/{t005_state.institution.id}/students/11111",
        headers=_headers_for(t005_state.users["student"].id),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCESS_DENIED"

async def test_profile_patch_creates_missing_profile(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    del t005_state.student_repository.profiles_by_student_id[t005_state.student.id]

    response = await student_api_client.patch(
        "/api/v1/students/me/profile",
        headers=_headers_for(t005_state.users["student"].id),
        json={"phone": "0499999999", "city": "Perth"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == str(t005_state.student.id)
    assert body["phone"] == "0499999999"
    assert body["city"] == "Perth"
    assert t005_state.student.id in t005_state.student_repository.profiles_by_student_id


async def test_inactive_program_cannot_be_used_for_new_application(
    student_api_client: AsyncClient,
    t005_state: StudentApiState,
) -> None:
    inactive_program = next(
        program for program in t005_state.enrolment_repository.programs_by_id.values()
        if not program.active
    )
    existing_count = len(t005_state.enrolment_repository.applications_by_id)

    response = await student_api_client.post(
        "/api/v1/students/me/enrolment-applications",
        headers=_headers_for(t005_state.users["student"].id),
        json={"program_id": str(inactive_program.id)},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert len(t005_state.enrolment_repository.applications_by_id) == existing_count

async def test_openapi_exposes_t005_paths_and_bearer_security(
    student_api_client: AsyncClient,
) -> None:
    response = await student_api_client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    expected_operations = (
        ("/api/v1/students/me", "get"),
        ("/api/v1/students/me/profile", "get"),
        ("/api/v1/students/me/profile", "patch"),
        ("/api/v1/students/me/enrolment-applications", "get"),
        ("/api/v1/students/me/enrolment-applications", "post"),
        ("/api/v1/students/me/enrolment-applications/{application_id}", "get"),
        ("/api/v1/students/me/enrolment-applications/{application_id}/submit", "post"),
        ("/api/v1/institutions/{institution_id}/students/{student_number}", "get"),
    )
    assert "BearerAuth" in schema["components"]["securitySchemes"]
    for path, method in expected_operations:
        assert path in schema["paths"]
        assert schema["paths"][path][method]["security"] == [{"BearerAuth": []}]


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL student API integration tests.",
)
async def test_postgresql_demo_student_resolves_through_authenticated_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("DEMO_USER_PASSWORD", TEST_PASSWORD)
    get_settings.cache_clear()

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await seed_development_data(session, demo_user_password=TEST_PASSWORD)

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"email": DEMO_STUDENT_EMAIL, "password": TEST_PASSWORD},
            )
            token = login_response.json()["access_token"]
            student_response = await client.get(
                "/api/v1/students/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        async with session_factory() as session:
            duplicate_check = await session.execute(
                select(func.count())
                .select_from(Student)
                .join(User, Student.user_id == User.id)
                .where(
                    Student.student_number == DEMO_STUDENT_NUMBER,
                    User.email == DEMO_STUDENT_EMAIL,
                ),
            )
            matching_demo_students = duplicate_check.scalar_one()

        assert login_response.status_code == 200
        assert student_response.status_code == 200
        assert student_response.json()["student_number"] == DEMO_STUDENT_NUMBER
        assert matching_demo_students == 1
    finally:
        await _dispose_cached_database_engine()
        get_settings.cache_clear()


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL student API integration tests.",
)
async def test_postgresql_unknown_profile_country_id_returns_404_not_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("DEMO_USER_PASSWORD", TEST_PASSWORD)
    get_settings.cache_clear()

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await seed_development_data(session, demo_user_password=TEST_PASSWORD)

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"email": DEMO_STUDENT_EMAIL, "password": TEST_PASSWORD},
            )
            token = login_response.json()["access_token"]
            response = await client.patch(
                "/api/v1/students/me/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={"country_id": str(uuid4())},
            )

        assert login_response.status_code == 200
        assert response.status_code != 500
        assert response.status_code == 404
        assert response.json()["error"] == {
            "code": "NOT_FOUND",
            "message": "Country was not found",
            "details": None,
        }
    finally:
        await _dispose_cached_database_engine()
        get_settings.cache_clear()

def _user(email: str) -> User:
    return User(
        id=uuid4(),
        email=email,
        first_name="Demo",
        last_name="User",
        preferred_name="Demo",
        password_hash=hash_password(TEST_PASSWORD),
        is_active=True,
    )


def _headers_for(user_id: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token_for(user_id)}"}


def _token_for(user_id: UUID) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=60),
        "jti": str(uuid4()),
    }
    return jwt.encode(claims, TEST_JWT_SECRET, algorithm="HS256")


def _stamp[EntityT: TimestampedEntity](entity: EntityT, value: datetime) -> EntityT:
    entity.created_at = value
    entity.updated_at = value
    return entity


def _ensure_identity(entity: StudentProfile | EnrolmentApplication) -> None:
    if getattr(entity, "id", None) is None:
        entity.id = uuid4()


def _ensure_timestamps(entity: StudentProfile | EnrolmentApplication) -> None:
    now = datetime.now(UTC)
    if getattr(entity, "created_at", None) is None:
        entity.created_at = now
    entity.updated_at = now


async def _dispose_cached_database_engine() -> None:
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
