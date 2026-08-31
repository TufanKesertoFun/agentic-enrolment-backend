from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateTable

import app.models  # noqa: F401
from app.infrastructure.database.base import Base
from app.models import Student

EXPECTED_TABLES = {
    "countries",
    "institutions",
    "users",
    "roles",
    "user_roles",
    "students",
    "student_profiles",
    "programs",
    "courses",
    "enrolment_applications",
    "previous_educations",
    "previous_courses",
    "qualifications",
    "external_profile_links",
    "student_documents",
    "credit_mapping_requests",
    "credit_mapping_evidence",
    "credit_mapping_decisions",
    "historical_credit_mappings",
}


def test_sqlalchemy_metadata_loads_all_core_domain_tables() -> None:
    assert EXPECTED_TABLES <= set(Base.metadata.tables.keys())


def test_sqlalchemy_relationships_are_configured() -> None:
    configure_mappers()


def test_postgresql_ddl_compiles_for_all_tables() -> None:
    dialect = postgresql.dialect()

    for table in Base.metadata.sorted_tables:
        str(CreateTable(table).compile(dialect=dialect))


def test_student_number_lookup_query_compiles_for_postgresql() -> None:
    statement = select(Student).where(Student.student_number == "11111")
    compiled = statement.compile(dialect=postgresql.dialect())

    assert "students.student_number" in str(compiled)
