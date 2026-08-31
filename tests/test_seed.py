import os

import pytest
from sqlalchemy import select

from app.infrastructure.database.seed import (
    DEMO_STUDENT_EMAIL,
    DEMO_STUDENT_NUMBER,
    build_development_seed_spec,
    seed_development_data,
)
from app.infrastructure.database.session import get_session_factory
from app.models import Student


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


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="Set RUN_POSTGRES_TESTS=1 to run PostgreSQL seed integration tests.",
)
async def test_development_seed_creates_retrievable_fake_student_in_postgresql() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await seed_development_data(session)

    async with session_factory() as session:
        result = await session.execute(select(Student).where(Student.student_number == "11111"))
        student = result.scalar_one()

    assert student.student_number == "11111"
