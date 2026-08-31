"""create core domain schema

Revision ID: 20260831_0002
Revises: 20260831_0001
Create Date: 2026-08-31 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20260831_0002"
down_revision: str | None = "20260831_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_NAMES = (
    "STUDENT",
    "LECTURER",
    "ENROLMENT_OFFICER",
    "CREDIT_MAPPING_OFFICER",
    "ADMINISTRATOR",
)
INSTITUTION_TYPES = ("UNIVERSITY", "COLLEGE", "VOCATIONAL", "OTHER")
STUDENT_STATUSES = ("PROSPECTIVE", "ACTIVE", "INACTIVE", "COMPLETED", "WITHDRAWN")
CREDIT_SYSTEMS = ("AU_CREDIT_POINTS", "ECTS", "US_CREDIT_HOURS", "UK_CREDITS")
WORKFLOW_STATUSES = (
    "DRAFT",
    "SUBMITTED",
    "UNDER_REVIEW",
    "MORE_INFORMATION_REQUIRED",
    "APPROVED",
    "REJECTED",
)
PROFILE_TYPES = ("LINKEDIN", "PORTFOLIO", "PROFESSIONAL_PROFILE", "OTHER")
DOCUMENT_TYPES = (
    "TRANSCRIPT",
    "CERTIFICATE",
    "COURSE_OUTLINE",
    "ACADEMIC_RECORD",
    "IDENTIFICATION",
    "EMPLOYMENT_EVIDENCE",
    "PROFESSIONAL_CERTIFICATE",
    "OTHER",
)
DOCUMENT_STATUSES = ("PENDING", "QUARANTINED", "CLEAN", "REJECTED", "ARCHIVED")
DECISION_VALUES = ("APPROVED", "REJECTED", "MORE_INFORMATION_REQUIRED")


def _enum(name: str, values: tuple[str, ...]) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def _create_enum(bind: Connection, name: str, values: tuple[str, ...]) -> None:
    postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)


def _drop_enum(bind: Connection, name: str, values: tuple[str, ...]) -> None:
    postgresql.ENUM(*values, name=name).drop(bind, checkfirst=True)


def _uuid_pk() -> sa.Column[Any]:
    return sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False)


def _created_at() -> sa.Column[Any]:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("timezone('utc', now())"),
        nullable=False,
    )


def _updated_at() -> sa.Column[Any]:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("timezone('utc', now())"),
        nullable=False,
    )


def _timestamps() -> list[sa.Column[Any]]:
    return [_created_at(), _updated_at()]


def upgrade() -> None:
    bind = op.get_bind()
    _create_enum(bind, "role_name", ROLE_NAMES)
    _create_enum(bind, "institution_type", INSTITUTION_TYPES)
    _create_enum(bind, "student_status", STUDENT_STATUSES)
    _create_enum(bind, "credit_system", CREDIT_SYSTEMS)
    _create_enum(bind, "enrolment_application_status", WORKFLOW_STATUSES)
    _create_enum(bind, "external_profile_type", PROFILE_TYPES)
    _create_enum(bind, "student_document_type", DOCUMENT_TYPES)
    _create_enum(bind, "student_document_status", DOCUMENT_STATUSES)
    _create_enum(bind, "credit_mapping_request_status", WORKFLOW_STATUSES)
    _create_enum(bind, "credit_mapping_decision_value", DECISION_VALUES)

    op.create_table(
        "countries",
        _uuid_pk(),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("default_locale", sa.String(length=20), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_countries_code"),
    )
    op.create_index("ix_countries_code", "countries", ["code"])

    op.create_table(
        "users",
        _uuid_pk(),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("preferred_name", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "roles",
        _uuid_pk(),
        sa.Column("name", _enum("role_name", ROLE_NAMES), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )

    op.create_table(
        "institutions",
        _uuid_pk(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("country_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_code", sa.String(length=80), nullable=True),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("institution_type", _enum("institution_type", INSTITUTION_TYPES), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "country_id",
            "external_code",
            name="uq_institutions_country_external_code",
        ),
    )
    op.create_index("ix_institutions_country_id", "institutions", ["country_id"])
    op.create_index("ix_institutions_external_code", "institutions", ["external_code"])

    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    op.create_table(
        "programs",
        _uuid_pk(),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("qualification_level", sa.String(length=120), nullable=False),
        sa.Column("credit_system", _enum("credit_system", CREDIT_SYSTEMS), nullable=False),
        sa.Column("total_credits", sa.Numeric(10, 2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("total_credits >= 0", name="ck_programs_total_credits_non_negative"),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_programs_effective_date_range",
        ),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "institution_id",
            "program_code",
            "effective_from",
            name="uq_programs_institution_code_effective_from",
        ),
    )
    op.create_index("ix_programs_institution_id", "programs", ["institution_id"])
    op.create_index("ix_programs_program_code", "programs", ["program_code"])

    op.create_table(
        "courses",
        _uuid_pk(),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("course_code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("credit_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("credit_system", _enum("credit_system", CREDIT_SYSTEMS), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("credit_value >= 0", name="ck_courses_credit_value_non_negative"),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_courses_effective_date_range",
        ),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "institution_id",
            "course_code",
            "effective_from",
            name="uq_courses_institution_code_effective_from",
        ),
    )
    op.create_index("ix_courses_course_code", "courses", ["course_code"])
    op.create_index("ix_courses_institution_id", "courses", ["institution_id"])
    op.create_index("ix_courses_program_id", "courses", ["program_id"])

    op.create_table(
        "students",
        _uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_number", sa.String(length=80), nullable=False),
        sa.Column("home_country_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_program_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", _enum("student_status", STUDENT_STATUSES), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["current_institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["current_program_id"], ["programs.id"]),
        sa.ForeignKeyConstraint(["home_country_id"], ["countries.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "current_institution_id",
            "student_number",
            name="uq_students_institution_student_number",
        ),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_students_current_institution_id", "students", ["current_institution_id"])
    op.create_index("ix_students_student_number", "students", ["student_number"])

    op.create_table(
        "student_profiles",
        _uuid_pk(),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("address_line_1", sa.String(length=255), nullable=True),
        sa.Column("address_line_2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state_region", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=30), nullable=True),
        sa.Column("country_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", name="uq_student_profiles_student_id"),
    )

    op.create_table(
        "enrolment_applications",
        _uuid_pk(),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status", _enum("enrolment_application_status", WORKFLOW_STATUSES), nullable=False
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_enrolment_applications_status", "enrolment_applications", ["status"])
    op.create_index(
        "ix_enrolment_applications_student_id", "enrolment_applications", ["student_id"]
    )

    op.create_table(
        "previous_educations",
        _uuid_pk(),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("institution_name_snapshot", sa.String(length=255), nullable=False),
        sa.Column("country_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qualification_name", sa.String(length=255), nullable=False),
        sa.Column("qualification_level", sa.String(length=120), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_previous_educations_date_range",
        ),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"]),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_previous_educations_student_id", "previous_educations", ["student_id"])

    op.create_table(
        "previous_courses",
        _uuid_pk(),
        sa.Column("previous_education_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_course_code", sa.String(length=80), nullable=True),
        sa.Column("course_title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("credit_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("credit_system", _enum("credit_system", CREDIT_SYSTEMS), nullable=True),
        sa.Column("grade", sa.String(length=50), nullable=True),
        sa.Column("result", sa.String(length=80), nullable=True),
        sa.Column("year_completed", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "credit_value IS NULL OR credit_value >= 0",
            name="ck_previous_courses_credit_value_non_negative",
        ),
        sa.ForeignKeyConstraint(["previous_education_id"], ["previous_educations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_previous_courses_external_course_code", "previous_courses", ["external_course_code"]
    )
    op.create_index(
        "ix_previous_courses_previous_education_id", "previous_courses", ["previous_education_id"]
    )

    op.create_table(
        "qualifications",
        _uuid_pk(),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("issuing_organization", sa.String(length=255), nullable=False),
        sa.Column("country_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("credential_reference", sa.String(length=255), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "expiry_date IS NULL OR issued_date IS NULL OR expiry_date >= issued_date",
            name="ck_qualifications_date_range",
        ),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qualifications_student_id", "qualifications", ["student_id"])

    op.create_table(
        "external_profile_links",
        _uuid_pk(),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_type", _enum("external_profile_type", PROFILE_TYPES), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("consent_given", sa.Boolean(), nullable=False),
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_profile_links_student_id", "external_profile_links", ["student_id"]
    )

    op.create_table(
        "student_documents",
        _uuid_pk(),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", _enum("student_document_type", DOCUMENT_TYPES), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("status", _enum("student_document_status", DOCUMENT_STATUSES), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("file_size >= 0", name="ck_student_documents_file_size_non_negative"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_documents_status", "student_documents", ["status"])
    op.create_index("ix_student_documents_student_id", "student_documents", ["student_id"])

    op.create_table(
        "credit_mapping_requests",
        _uuid_pk(),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_previous_course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status", _enum("credit_mapping_request_status", WORKFLOW_STATUSES), nullable=False
        ),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["assigned_reviewer_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["source_previous_course_id"], ["previous_courses.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["target_course_id"], ["courses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_mapping_requests_status", "credit_mapping_requests", ["status"])
    op.create_index(
        "ix_credit_mapping_requests_student_id", "credit_mapping_requests", ["student_id"]
    )

    op.create_table(
        "credit_mapping_evidence",
        _uuid_pk(),
        sa.Column("credit_mapping_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(["credit_mapping_request_id"], ["credit_mapping_requests.id"]),
        sa.ForeignKeyConstraint(["student_document_id"], ["student_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "credit_mapping_request_id",
            "student_document_id",
            name="uq_credit_mapping_evidence_request_document",
        ),
    )
    op.create_index(
        "ix_credit_mapping_evidence_request_id",
        "credit_mapping_evidence",
        ["credit_mapping_request_id"],
    )

    op.create_table(
        "credit_mapping_decisions",
        _uuid_pk(),
        sa.Column("credit_mapping_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "decision", _enum("credit_mapping_decision_value", DECISION_VALUES), nullable=False
        ),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("credit_awarded", sa.Numeric(10, 2), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "credit_awarded IS NULL OR credit_awarded >= 0",
            name="ck_credit_mapping_decisions_credit_awarded_non_negative",
        ),
        sa.ForeignKeyConstraint(["credit_mapping_request_id"], ["credit_mapping_requests.id"]),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_credit_mapping_decisions_request_id",
        "credit_mapping_decisions",
        ["credit_mapping_request_id"],
    )

    op.create_table(
        "historical_credit_mappings",
        _uuid_pk(),
        sa.Column("source_institution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_course_code", sa.String(length=80), nullable=False),
        sa.Column("source_course_title", sa.String(length=255), nullable=False),
        sa.Column("target_institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_course_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_course_code_snapshot", sa.String(length=80), nullable=False),
        sa.Column(
            "decision", _enum("credit_mapping_decision_value", DECISION_VALUES), nullable=False
        ),
        sa.Column("credit_awarded", sa.Numeric(10, 2), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "credit_awarded IS NULL OR credit_awarded >= 0",
            name="ck_historical_credit_mappings_credit_awarded_non_negative",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_historical_credit_mappings_effective_date_range",
        ),
        sa.ForeignKeyConstraint(["source_institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["target_course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["target_institution_id"], ["institutions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_historical_credit_mappings_source_course_code",
        "historical_credit_mappings",
        ["source_course_code"],
    )
    op.create_index(
        "ix_historical_credit_mappings_target_course_code",
        "historical_credit_mappings",
        ["target_course_code_snapshot"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table("historical_credit_mappings")
    op.drop_table("credit_mapping_decisions")
    op.drop_table("credit_mapping_evidence")
    op.drop_table("credit_mapping_requests")
    op.drop_table("student_documents")
    op.drop_table("external_profile_links")
    op.drop_table("qualifications")
    op.drop_table("previous_courses")
    op.drop_table("previous_educations")
    op.drop_table("enrolment_applications")
    op.drop_table("student_profiles")
    op.drop_table("students")
    op.drop_table("courses")
    op.drop_table("programs")
    op.drop_table("user_roles")
    op.drop_table("institutions")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("countries")

    _drop_enum(bind, "credit_mapping_decision_value", DECISION_VALUES)
    _drop_enum(bind, "credit_mapping_request_status", WORKFLOW_STATUSES)
    _drop_enum(bind, "student_document_status", DOCUMENT_STATUSES)
    _drop_enum(bind, "student_document_type", DOCUMENT_TYPES)
    _drop_enum(bind, "external_profile_type", PROFILE_TYPES)
    _drop_enum(bind, "enrolment_application_status", WORKFLOW_STATUSES)
    _drop_enum(bind, "credit_system", CREDIT_SYSTEMS)
    _drop_enum(bind, "student_status", STUDENT_STATUSES)
    _drop_enum(bind, "institution_type", INSTITUTION_TYPES)
    _drop_enum(bind, "role_name", ROLE_NAMES)
