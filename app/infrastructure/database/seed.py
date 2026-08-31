from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import (
    CreditMappingDecisionValue,
    CreditSystem,
    InstitutionType,
    RoleName,
    StudentStatus,
)
from app.infrastructure.database.session import get_session_factory
from app.models import (
    Country,
    Course,
    HistoricalCreditMapping,
    Institution,
    PreviousCourse,
    PreviousEducation,
    Program,
    Role,
    Student,
    User,
    UserRole,
)

DEMO_STUDENT_NUMBER = "11111"
DEMO_STUDENT_EMAIL = "demo.student@example.invalid"


@dataclass(frozen=True)
class CountrySeed:
    code: str
    name: str
    default_locale: str


@dataclass(frozen=True)
class MockHistoricalMappingSeed:
    source_course_code: str
    source_course_title: str
    target_course_code: str
    target_course_title: str
    decision: str
    credit_awarded: str


@dataclass(frozen=True)
class DevelopmentSeedSpec:
    countries: tuple[CountrySeed, ...]
    roles: tuple[str, ...]
    demo_student_number: str
    demo_student_email: str
    mock_historical_mappings: tuple[MockHistoricalMappingSeed, ...]


@dataclass(frozen=True)
class SeedSummary:
    countries: int
    roles: int
    demo_student_number: str
    historical_mappings: int


def build_development_seed_spec() -> DevelopmentSeedSpec:
    return DevelopmentSeedSpec(
        countries=(
            CountrySeed(code="AU", name="Australia", default_locale="en-AU"),
            CountrySeed(code="DE", name="Germany", default_locale="de-DE"),
            CountrySeed(code="TR", name="Turkey", default_locale="tr-TR"),
            CountrySeed(code="US", name="United States", default_locale="en-US"),
            CountrySeed(code="GB", name="United Kingdom", default_locale="en-GB"),
        ),
        roles=tuple(role.value for role in RoleName),
        demo_student_number=DEMO_STUDENT_NUMBER,
        demo_student_email=DEMO_STUDENT_EMAIL,
        mock_historical_mappings=(
            MockHistoricalMappingSeed(
                source_course_code="MOCK-ITP101",
                source_course_title="Introduction to Programming",
                target_course_code="COMP SCI 1101",
                target_course_title="Introduction to Computer Systems, Networks and Security",
                decision=CreditMappingDecisionValue.APPROVED.value,
                credit_awarded="3.00",
            ),
            MockHistoricalMappingSeed(
                source_course_code="MOCK-DBS201",
                source_course_title="Database Systems Foundations",
                target_course_code="COMP SCI 2207",
                target_course_title="Database and Information Systems",
                decision=CreditMappingDecisionValue.APPROVED.value,
                credit_awarded="3.00",
            ),
            MockHistoricalMappingSeed(
                source_course_code="MOCK-WEB150",
                source_course_title="Web Application Development",
                target_course_code="COMP SCI 2203",
                target_course_title="Software Engineering and Project",
                decision=CreditMappingDecisionValue.MORE_INFORMATION_REQUIRED.value,
                credit_awarded="0.00",
            ),
        ),
    )


async def _get_or_create_country(
    session: AsyncSession,
    seed: CountrySeed,
) -> Country:
    result = await session.execute(select(Country).where(Country.code == seed.code))
    country = result.scalar_one_or_none()
    if country is not None:
        return country

    country = Country(code=seed.code, name=seed.name, default_locale=seed.default_locale)
    session.add(country)
    await session.flush()
    return country


async def _get_or_create_role(session: AsyncSession, role_name: RoleName) -> Role:
    result = await session.execute(select(Role).where(Role.name == role_name))
    role = result.scalar_one_or_none()
    if role is not None:
        return role

    role = Role(name=role_name, description=f"Development role seed for {role_name.value}")
    session.add(role)
    await session.flush()
    return role


async def _get_or_create_institution(
    session: AsyncSession,
    country: Country,
    name: str,
    external_code: str,
    institution_type: InstitutionType,
) -> Institution:
    result = await session.execute(
        select(Institution).where(
            Institution.country_id == country.id,
            Institution.external_code == external_code,
        ),
    )
    institution = result.scalar_one_or_none()
    if institution is not None:
        return institution

    institution = Institution(
        name=name,
        country=country,
        external_code=external_code,
        institution_type=institution_type,
        active=True,
    )
    session.add(institution)
    await session.flush()
    return institution


async def _get_or_create_program(
    session: AsyncSession,
    institution: Institution,
) -> Program:
    result = await session.execute(
        select(Program).where(
            Program.institution_id == institution.id,
            Program.program_code == "DEMO-BCOMP",
        ),
    )
    program = result.scalar_one_or_none()
    if program is not None:
        return program

    program = Program(
        institution=institution,
        program_code="DEMO-BCOMP",
        name="Bachelor of Computer Science Demo Program",
        qualification_level="Bachelor",
        credit_system=CreditSystem.AU_CREDIT_POINTS,
        total_credits=Decimal("72.00"),
        active=True,
    )
    session.add(program)
    await session.flush()
    return program


async def _get_or_create_course(
    session: AsyncSession,
    institution: Institution,
    program: Program,
    course_code: str,
    title: str,
) -> Course:
    result = await session.execute(
        select(Course).where(
            Course.institution_id == institution.id,
            Course.course_code == course_code,
        ),
    )
    course = result.scalar_one_or_none()
    if course is not None:
        return course

    course = Course(
        institution=institution,
        program=program,
        course_code=course_code,
        title=title,
        credit_value=Decimal("3.00"),
        credit_system=CreditSystem.AU_CREDIT_POINTS,
        active=True,
    )
    session.add(course)
    await session.flush()
    return course


async def _get_or_create_demo_user(session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == DEMO_STUDENT_EMAIL))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        email=DEMO_STUDENT_EMAIL,
        first_name="Demo",
        last_name="Student",
        preferred_name="Demo",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _assign_role(session: AsyncSession, user: User, role: Role) -> None:
    result = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
        ),
    )
    if result.scalar_one_or_none() is not None:
        return

    session.add(UserRole(user=user, role=role))
    await session.flush()


async def _get_or_create_demo_student(
    session: AsyncSession,
    user: User,
    country: Country,
    institution: Institution,
    program: Program,
) -> Student:
    result = await session.execute(
        select(Student).where(
            Student.current_institution_id == institution.id,
            Student.student_number == DEMO_STUDENT_NUMBER,
        ),
    )
    student = result.scalar_one_or_none()
    if student is not None:
        return student

    student = Student(
        user=user,
        student_number=DEMO_STUDENT_NUMBER,
        home_country=country,
        current_institution=institution,
        current_program=program,
        status=StudentStatus.ACTIVE,
    )
    session.add(student)
    await session.flush()
    return student


async def _get_or_create_previous_education(
    session: AsyncSession,
    student: Student,
    institution: Institution,
    country: Country,
) -> PreviousEducation:
    result = await session.execute(
        select(PreviousEducation).where(
            PreviousEducation.student_id == student.id,
            PreviousEducation.institution_name_snapshot == institution.name,
        ),
    )
    previous_education = result.scalar_one_or_none()
    if previous_education is not None:
        return previous_education

    previous_education = PreviousEducation(
        student=student,
        institution=institution,
        institution_name_snapshot=institution.name,
        country=country,
        qualification_name="Mock Diploma of Information Technology",
        qualification_level="Diploma",
        completed=True,
    )
    session.add(previous_education)
    await session.flush()
    return previous_education


async def _get_or_create_previous_course(
    session: AsyncSession,
    previous_education: PreviousEducation,
    source_course_code: str,
    source_course_title: str,
) -> PreviousCourse:
    result = await session.execute(
        select(PreviousCourse).where(
            PreviousCourse.previous_education_id == previous_education.id,
            PreviousCourse.external_course_code == source_course_code,
        ),
    )
    previous_course = result.scalar_one_or_none()
    if previous_course is not None:
        return previous_course

    previous_course = PreviousCourse(
        previous_education=previous_education,
        external_course_code=source_course_code,
        course_title=source_course_title,
        credit_value=Decimal("3.00"),
        credit_system=CreditSystem.AU_CREDIT_POINTS,
        result="PASS",
        year_completed=2025,
    )
    session.add(previous_course)
    await session.flush()
    return previous_course


async def _get_or_create_historical_mapping(
    session: AsyncSession,
    mapping: MockHistoricalMappingSeed,
    source_institution: Institution,
    target_institution: Institution,
    target_course: Course,
) -> HistoricalCreditMapping:
    result = await session.execute(
        select(HistoricalCreditMapping).where(
            HistoricalCreditMapping.source_reference == "MOCK-DEVELOPMENT",
            HistoricalCreditMapping.source_course_code == mapping.source_course_code,
            HistoricalCreditMapping.target_course_code_snapshot == mapping.target_course_code,
        ),
    )
    historical_mapping = result.scalar_one_or_none()
    if historical_mapping is not None:
        return historical_mapping

    historical_mapping = HistoricalCreditMapping(
        source_institution=source_institution,
        source_course_code=mapping.source_course_code,
        source_course_title=mapping.source_course_title,
        target_institution=target_institution,
        target_course=target_course,
        target_course_code_snapshot=mapping.target_course_code,
        decision=CreditMappingDecisionValue(mapping.decision),
        credit_awarded=Decimal(mapping.credit_awarded),
        source_reference="MOCK-DEVELOPMENT",
    )
    session.add(historical_mapping)
    await session.flush()
    return historical_mapping


async def seed_development_data(session: AsyncSession) -> SeedSummary:
    spec = build_development_seed_spec()

    countries = {
        country_seed.code: await _get_or_create_country(session, country_seed)
        for country_seed in spec.countries
    }
    roles = {
        role_name: await _get_or_create_role(session, RoleName(role_name))
        for role_name in spec.roles
    }

    australia = countries["AU"]
    demo_institution = await _get_or_create_institution(
        session=session,
        country=australia,
        name="Demo University",
        external_code="DEMO-AU",
        institution_type=InstitutionType.UNIVERSITY,
    )
    source_institution = await _get_or_create_institution(
        session=session,
        country=australia,
        name="Mock Prior Learning College",
        external_code="MOCK-PRIOR-AU",
        institution_type=InstitutionType.COLLEGE,
    )
    demo_program = await _get_or_create_program(session, demo_institution)
    demo_user = await _get_or_create_demo_user(session)
    await _assign_role(session, demo_user, roles[RoleName.STUDENT.value])
    demo_student = await _get_or_create_demo_student(
        session=session,
        user=demo_user,
        country=australia,
        institution=demo_institution,
        program=demo_program,
    )
    previous_education = await _get_or_create_previous_education(
        session=session,
        student=demo_student,
        institution=source_institution,
        country=australia,
    )

    historical_mappings = 0
    for mapping in spec.mock_historical_mappings:
        target_course = await _get_or_create_course(
            session=session,
            institution=demo_institution,
            program=demo_program,
            course_code=mapping.target_course_code,
            title=mapping.target_course_title,
        )
        await _get_or_create_previous_course(
            session=session,
            previous_education=previous_education,
            source_course_code=mapping.source_course_code,
            source_course_title=mapping.source_course_title,
        )
        await _get_or_create_historical_mapping(
            session=session,
            mapping=mapping,
            source_institution=source_institution,
            target_institution=demo_institution,
            target_course=target_course,
        )
        historical_mappings += 1

    await session.commit()
    return SeedSummary(
        countries=len(countries),
        roles=len(roles),
        demo_student_number=demo_student.student_number,
        historical_mappings=historical_mappings,
    )


async def run_development_seed() -> SeedSummary:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await seed_development_data(session)


def _json_default(value: Any) -> str:
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed development reference data.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the seed plan without connecting to PostgreSQL.",
    )
    args = parser.parse_args()

    if args.dry_run:
        print(json.dumps(asdict(build_development_seed_spec()), indent=2, default=_json_default))
        return 0

    summary = asyncio.run(run_development_seed())
    print(json.dumps(asdict(summary), indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
