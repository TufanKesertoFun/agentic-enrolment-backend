from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.domain.enums import (
    CreditMappingDecisionValue,
    CreditMappingRequestStatus,
    CreditSystem,
    EnrolmentApplicationStatus,
    ExternalProfileType,
    InstitutionType,
    RoleName,
    StudentDocumentStatus,
    StudentDocumentType,
    StudentStatus,
)
from app.infrastructure.database.base import Base
from app.models.base import TimestampMixin, UuidPrimaryKeyMixin


def enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_type]


def validate_non_negative_decimal(value: Decimal | None, field_name: str) -> Decimal | None:
    if value is not None and value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


class Country(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "countries"
    __table_args__ = (
        UniqueConstraint("code", name="uq_countries_code"),
        Index("ix_countries_code", "code"),
    )

    code: Mapped[str] = mapped_column(String(2), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    default_locale: Mapped[str | None] = mapped_column(String(20), nullable=True)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)

    institutions: Mapped[list[Institution]] = relationship(back_populates="country")
    resident_profiles: Mapped[list[StudentProfile]] = relationship(back_populates="country")
    students_from_country: Mapped[list[Student]] = relationship(back_populates="home_country")
    previous_educations: Mapped[list[PreviousEducation]] = relationship(back_populates="country")
    qualifications: Mapped[list[Qualification]] = relationship(back_populates="country")

    @validates("code")
    def validate_code(self, _key: str, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 2:
            raise ValueError("country code must use a two-character ISO-style code")
        return normalized


class Institution(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "institutions"
    __table_args__ = (
        UniqueConstraint(
            "country_id", "external_code", name="uq_institutions_country_external_code"
        ),
        Index("ix_institutions_external_code", "external_code"),
        Index("ix_institutions_country_id", "country_id"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_id: Mapped[UUID] = mapped_column(ForeignKey("countries.id"), nullable=False)
    external_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    institution_type: Mapped[InstitutionType] = mapped_column(
        Enum(InstitutionType, name="institution_type", values_callable=enum_values),
        nullable=False,
        default=InstitutionType.UNIVERSITY,
    )
    active: Mapped[bool] = mapped_column(default=True, nullable=False)

    country: Mapped[Country] = relationship(back_populates="institutions")
    programs: Mapped[list[Program]] = relationship(back_populates="institution")
    courses: Mapped[list[Course]] = relationship(back_populates="institution")
    current_students: Mapped[list[Student]] = relationship(back_populates="current_institution")
    previous_educations: Mapped[list[PreviousEducation]] = relationship(
        back_populates="institution"
    )
    historical_source_mappings: Mapped[list[HistoricalCreditMapping]] = relationship(
        back_populates="source_institution",
        foreign_keys="HistoricalCreditMapping.source_institution_id",
    )
    historical_target_mappings: Mapped[list[HistoricalCreditMapping]] = relationship(
        back_populates="target_institution",
        foreign_keys="HistoricalCreditMapping.target_institution_id",
    )


class User(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email_lower", text("lower(email)"), unique=True),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    preferred_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    role_assignments: Mapped[list[UserRole]] = relationship(back_populates="user")
    roles: Mapped[list[Role]] = relationship(secondary="user_roles", viewonly=True)
    student: Mapped[Student | None] = relationship(back_populates="user", uselist=False)
    reviewed_enrolment_applications: Mapped[list[EnrolmentApplication]] = relationship(
        back_populates="reviewed_by",
        foreign_keys="EnrolmentApplication.reviewed_by_user_id",
    )
    requested_credit_mapping_requests: Mapped[list[CreditMappingRequest]] = relationship(
        back_populates="requested_by",
        foreign_keys="CreditMappingRequest.requested_by_user_id",
    )
    assigned_credit_mapping_requests: Mapped[list[CreditMappingRequest]] = relationship(
        back_populates="assigned_reviewer",
        foreign_keys="CreditMappingRequest.assigned_reviewer_user_id",
    )
    credit_mapping_decisions: Mapped[list[CreditMappingDecision]] = relationship(
        back_populates="decided_by",
        foreign_keys="CreditMappingDecision.decided_by_user_id",
    )

    @validates("email")
    def validate_email(self, _key: str, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("email must contain @")
        return normalized


class Role(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("name", name="uq_roles_name"),)

    name: Mapped[RoleName] = mapped_column(
        Enum(RoleName, name="role_name", values_callable=enum_values),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user_assignments: Mapped[list[UserRole]] = relationship(back_populates="role")
    users: Mapped[list[User]] = relationship(secondary="user_roles", viewonly=True)


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (Index("ix_user_roles_role_id", "role_id"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
    )

    user: Mapped[User] = relationship(back_populates="role_assignments")
    role: Mapped[Role] = relationship(back_populates="user_assignments")


class Program(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "programs"
    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "program_code",
            "effective_from",
            name="uq_programs_institution_code_effective_from",
        ),
        CheckConstraint("total_credits >= 0", name="ck_programs_total_credits_non_negative"),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_programs_effective_date_range",
        ),
        Index("ix_programs_program_code", "program_code"),
        Index("ix_programs_institution_id", "institution_id"),
    )

    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id"), nullable=False)
    program_code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    qualification_level: Mapped[str] = mapped_column(String(120), nullable=False)
    credit_system: Mapped[CreditSystem] = mapped_column(
        Enum(CreditSystem, name="credit_system", values_callable=enum_values),
        nullable=False,
    )
    total_credits: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    institution: Mapped[Institution] = relationship(back_populates="programs")
    courses: Mapped[list[Course]] = relationship(back_populates="program")
    students: Mapped[list[Student]] = relationship(back_populates="current_program")
    enrolment_applications: Mapped[list[EnrolmentApplication]] = relationship(
        back_populates="program"
    )

    @validates("total_credits")
    def validate_total_credits(self, _key: str, value: Decimal) -> Decimal:
        result = validate_non_negative_decimal(value, "total_credits")
        if result is None:
            raise ValueError("total_credits is required")
        return result

    @validates("effective_to")
    def validate_effective_to(self, _key: str, value: date | None) -> date | None:
        if value is not None and self.effective_from is not None and value < self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        return value


class Course(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "course_code",
            "effective_from",
            name="uq_courses_institution_code_effective_from",
        ),
        CheckConstraint("credit_value >= 0", name="ck_courses_credit_value_non_negative"),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_courses_effective_date_range",
        ),
        Index("ix_courses_course_code", "course_code"),
        Index("ix_courses_institution_id", "institution_id"),
        Index("ix_courses_program_id", "program_id"),
    )

    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id"), nullable=False)
    program_id: Mapped[UUID | None] = mapped_column(ForeignKey("programs.id"), nullable=True)
    course_code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    credit_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    credit_system: Mapped[CreditSystem] = mapped_column(
        Enum(CreditSystem, name="credit_system", values_callable=enum_values),
        nullable=False,
    )
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)

    institution: Mapped[Institution] = relationship(back_populates="courses")
    program: Mapped[Program | None] = relationship(back_populates="courses")
    credit_mapping_requests: Mapped[list[CreditMappingRequest]] = relationship(
        back_populates="target_course"
    )
    historical_target_mappings: Mapped[list[HistoricalCreditMapping]] = relationship(
        back_populates="target_course",
    )

    @validates("credit_value")
    def validate_credit_value(self, _key: str, value: Decimal) -> Decimal:
        result = validate_non_negative_decimal(value, "credit_value")
        if result is None:
            raise ValueError("credit_value is required")
        return result

    @validates("effective_to")
    def validate_effective_to(self, _key: str, value: date | None) -> date | None:
        if value is not None and self.effective_from is not None and value < self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        return value


class Student(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint(
            "current_institution_id",
            "student_number",
            name="uq_students_institution_student_number",
        ),
        Index("ix_students_student_number", "student_number"),
        Index("ix_students_current_institution_id", "current_institution_id"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    student_number: Mapped[str] = mapped_column(String(80), nullable=False)
    home_country_id: Mapped[UUID] = mapped_column(ForeignKey("countries.id"), nullable=False)
    current_institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id"), nullable=False
    )
    current_program_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("programs.id"), nullable=True
    )
    status: Mapped[StudentStatus] = mapped_column(
        Enum(StudentStatus, name="student_status", values_callable=enum_values),
        nullable=False,
        default=StudentStatus.PROSPECTIVE,
    )

    user: Mapped[User] = relationship(back_populates="student")
    home_country: Mapped[Country] = relationship(back_populates="students_from_country")
    current_institution: Mapped[Institution] = relationship(back_populates="current_students")
    current_program: Mapped[Program | None] = relationship(back_populates="students")
    profile: Mapped[StudentProfile | None] = relationship(back_populates="student", uselist=False)
    previous_educations: Mapped[list[PreviousEducation]] = relationship(back_populates="student")
    qualifications: Mapped[list[Qualification]] = relationship(back_populates="student")
    documents: Mapped[list[StudentDocument]] = relationship(back_populates="student")
    external_profile_links: Mapped[list[ExternalProfileLink]] = relationship(
        back_populates="student"
    )
    enrolment_applications: Mapped[list[EnrolmentApplication]] = relationship(
        back_populates="student"
    )
    credit_mapping_requests: Mapped[list[CreditMappingRequest]] = relationship(
        back_populates="student"
    )

    @validates("student_number")
    def validate_student_number(self, _key: str, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("student_number is required")
        return normalized


class StudentProfile(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_profiles"
    __table_args__ = (UniqueConstraint("student_id", name="uq_student_profiles_student_id"),)

    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state_region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    country_id: Mapped[UUID | None] = mapped_column(ForeignKey("countries.id"), nullable=True)

    student: Mapped[Student] = relationship(back_populates="profile")
    country: Mapped[Country | None] = relationship(back_populates="resident_profiles")


class EnrolmentApplication(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "enrolment_applications"
    __table_args__ = (
        Index("ix_enrolment_applications_status", "status"),
        Index("ix_enrolment_applications_student_id", "student_id"),
    )

    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    program_id: Mapped[UUID] = mapped_column(ForeignKey("programs.id"), nullable=False)
    status: Mapped[EnrolmentApplicationStatus] = mapped_column(
        Enum(
            EnrolmentApplicationStatus,
            name="enrolment_application_status",
            values_callable=enum_values,
        ),
        nullable=False,
        default=EnrolmentApplicationStatus.DRAFT,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    student: Mapped[Student] = relationship(back_populates="enrolment_applications")
    program: Mapped[Program] = relationship(back_populates="enrolment_applications")
    reviewed_by: Mapped[User | None] = relationship(
        back_populates="reviewed_enrolment_applications",
        foreign_keys=[reviewed_by_user_id],
    )


class PreviousEducation(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "previous_educations"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_previous_educations_date_range",
        ),
        Index("ix_previous_educations_student_id", "student_id"),
    )

    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    institution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    institution_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    country_id: Mapped[UUID] = mapped_column(ForeignKey("countries.id"), nullable=False)
    qualification_name: Mapped[str] = mapped_column(String(255), nullable=False)
    qualification_level: Mapped[str] = mapped_column(String(120), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed: Mapped[bool] = mapped_column(default=False, nullable=False)

    student: Mapped[Student] = relationship(back_populates="previous_educations")
    institution: Mapped[Institution | None] = relationship(back_populates="previous_educations")
    country: Mapped[Country] = relationship(back_populates="previous_educations")
    courses: Mapped[list[PreviousCourse]] = relationship(back_populates="previous_education")

    @validates("end_date")
    def validate_end_date(self, _key: str, value: date | None) -> date | None:
        if value is not None and self.start_date is not None and value < self.start_date:
            raise ValueError("end_date must be after start_date")
        return value


class PreviousCourse(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "previous_courses"
    __table_args__ = (
        CheckConstraint(
            "credit_value IS NULL OR credit_value >= 0",
            name="ck_previous_courses_credit_value_non_negative",
        ),
        Index("ix_previous_courses_external_course_code", "external_course_code"),
        Index("ix_previous_courses_previous_education_id", "previous_education_id"),
    )

    previous_education_id: Mapped[UUID] = mapped_column(
        ForeignKey("previous_educations.id"),
        nullable=False,
    )
    external_course_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    course_title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    credit_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    credit_system: Mapped[CreditSystem | None] = mapped_column(
        Enum(CreditSystem, name="credit_system", values_callable=enum_values),
        nullable=True,
    )
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    result: Mapped[str | None] = mapped_column(String(80), nullable=True)
    year_completed: Mapped[int | None] = mapped_column(nullable=True)

    previous_education: Mapped[PreviousEducation] = relationship(back_populates="courses")
    credit_mapping_requests: Mapped[list[CreditMappingRequest]] = relationship(
        back_populates="source_previous_course",
    )

    @validates("credit_value")
    def validate_credit_value(self, _key: str, value: Decimal | None) -> Decimal | None:
        return validate_non_negative_decimal(value, "credit_value")


class Qualification(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "qualifications"
    __table_args__ = (
        CheckConstraint(
            "expiry_date IS NULL OR issued_date IS NULL OR expiry_date >= issued_date",
            name="ck_qualifications_date_range",
        ),
        Index("ix_qualifications_student_id", "student_id"),
    )

    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuing_organization: Mapped[str] = mapped_column(String(255), nullable=False)
    country_id: Mapped[UUID | None] = mapped_column(ForeignKey("countries.id"), nullable=True)
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    credential_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    student: Mapped[Student] = relationship(back_populates="qualifications")
    country: Mapped[Country | None] = relationship(back_populates="qualifications")

    @validates("expiry_date")
    def validate_expiry_date(self, _key: str, value: date | None) -> date | None:
        if value is not None and self.issued_date is not None and value < self.issued_date:
            raise ValueError("expiry_date must be after issued_date")
        return value


class ExternalProfileLink(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "external_profile_links"
    __table_args__ = (Index("ix_external_profile_links_student_id", "student_id"),)

    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    profile_type: Mapped[ExternalProfileType] = mapped_column(
        Enum(ExternalProfileType, name="external_profile_type", values_callable=enum_values),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    consent_given: Mapped[bool] = mapped_column(default=False, nullable=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    student: Mapped[Student] = relationship(back_populates="external_profile_links")


class StudentDocument(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_documents"
    __table_args__ = (
        CheckConstraint("file_size >= 0", name="ck_student_documents_file_size_non_negative"),
        Index("ix_student_documents_student_id", "student_id"),
        Index("ix_student_documents_status", "status"),
    )

    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    document_type: Mapped[StudentDocumentType] = mapped_column(
        Enum(StudentDocumentType, name="student_document_type", values_callable=enum_values),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[StudentDocumentStatus] = mapped_column(
        Enum(StudentDocumentStatus, name="student_document_status", values_callable=enum_values),
        nullable=False,
        default=StudentDocumentStatus.PENDING,
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student: Mapped[Student] = relationship(back_populates="documents")
    credit_mapping_evidence: Mapped[list[CreditMappingEvidence]] = relationship(
        back_populates="student_document",
    )

    @validates("file_size")
    def validate_file_size(self, _key: str, value: int) -> int:
        if value < 0:
            raise ValueError("file_size must be non-negative")
        return value


class CreditMappingRequest(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "credit_mapping_requests"
    __table_args__ = (
        Index("ix_credit_mapping_requests_status", "status"),
        Index("ix_credit_mapping_requests_student_id", "student_id"),
    )

    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    source_previous_course_id: Mapped[UUID] = mapped_column(
        ForeignKey("previous_courses.id"),
        nullable=False,
    )
    target_course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    status: Mapped[CreditMappingRequestStatus] = mapped_column(
        Enum(
            CreditMappingRequestStatus,
            name="credit_mapping_request_status",
            values_callable=enum_values,
        ),
        nullable=False,
        default=CreditMappingRequestStatus.DRAFT,
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_reviewer_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student: Mapped[Student] = relationship(back_populates="credit_mapping_requests")
    source_previous_course: Mapped[PreviousCourse] = relationship(
        back_populates="credit_mapping_requests",
    )
    target_course: Mapped[Course] = relationship(back_populates="credit_mapping_requests")
    requested_by: Mapped[User] = relationship(
        back_populates="requested_credit_mapping_requests",
        foreign_keys=[requested_by_user_id],
    )
    assigned_reviewer: Mapped[User | None] = relationship(
        back_populates="assigned_credit_mapping_requests",
        foreign_keys=[assigned_reviewer_user_id],
    )
    evidence: Mapped[list[CreditMappingEvidence]] = relationship(
        back_populates="credit_mapping_request",
    )
    decisions: Mapped[list[CreditMappingDecision]] = relationship(
        back_populates="credit_mapping_request",
    )


class CreditMappingEvidence(UuidPrimaryKeyMixin, Base):
    __tablename__ = "credit_mapping_evidence"
    __table_args__ = (
        UniqueConstraint(
            "credit_mapping_request_id",
            "student_document_id",
            name="uq_credit_mapping_evidence_request_document",
        ),
        Index("ix_credit_mapping_evidence_request_id", "credit_mapping_request_id"),
    )

    credit_mapping_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("credit_mapping_requests.id"),
        nullable=False,
    )
    student_document_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_documents.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
    )

    credit_mapping_request: Mapped[CreditMappingRequest] = relationship(back_populates="evidence")
    student_document: Mapped[StudentDocument] = relationship(
        back_populates="credit_mapping_evidence"
    )


class CreditMappingDecision(UuidPrimaryKeyMixin, Base):
    __tablename__ = "credit_mapping_decisions"
    __table_args__ = (
        CheckConstraint(
            "credit_awarded IS NULL OR credit_awarded >= 0",
            name="ck_credit_mapping_decisions_credit_awarded_non_negative",
        ),
        Index("ix_credit_mapping_decisions_request_id", "credit_mapping_request_id"),
    )

    credit_mapping_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("credit_mapping_requests.id"),
        nullable=False,
    )
    decision: Mapped[CreditMappingDecisionValue] = mapped_column(
        Enum(
            CreditMappingDecisionValue,
            name="credit_mapping_decision_value",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    decided_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    credit_awarded: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
    )

    credit_mapping_request: Mapped[CreditMappingRequest] = relationship(back_populates="decisions")
    decided_by: Mapped[User] = relationship(
        back_populates="credit_mapping_decisions",
        foreign_keys=[decided_by_user_id],
    )

    @validates("decided_by_user_id")
    def validate_decided_by_user_id(self, _key: str, value: UUID | None) -> UUID:
        if value is None:
            raise ValueError("credit mapping decisions require a human decided_by_user_id")
        return value

    @validates("credit_awarded")
    def validate_credit_awarded(self, _key: str, value: Decimal | None) -> Decimal | None:
        return validate_non_negative_decimal(value, "credit_awarded")


class HistoricalCreditMapping(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "historical_credit_mappings"
    __table_args__ = (
        CheckConstraint(
            "credit_awarded IS NULL OR credit_awarded >= 0",
            name="ck_historical_credit_mappings_credit_awarded_non_negative",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_historical_credit_mappings_effective_date_range",
        ),
        Index("ix_historical_credit_mappings_source_course_code", "source_course_code"),
        Index("ix_historical_credit_mappings_target_course_code", "target_course_code_snapshot"),
    )

    source_institution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("institutions.id"),
        nullable=True,
    )
    source_course_code: Mapped[str] = mapped_column(String(80), nullable=False)
    source_course_title: Mapped[str] = mapped_column(String(255), nullable=False)
    target_institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id"), nullable=False
    )
    target_course_id: Mapped[UUID | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    target_course_code_snapshot: Mapped[str] = mapped_column(String(80), nullable=False)
    decision: Mapped[CreditMappingDecisionValue] = mapped_column(
        Enum(
            CreditMappingDecisionValue,
            name="credit_mapping_decision_value",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    credit_awarded: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    source_institution: Mapped[Institution | None] = relationship(
        back_populates="historical_source_mappings",
        foreign_keys=[source_institution_id],
    )
    target_institution: Mapped[Institution] = relationship(
        back_populates="historical_target_mappings",
        foreign_keys=[target_institution_id],
    )
    target_course: Mapped[Course | None] = relationship(back_populates="historical_target_mappings")

    @validates("credit_awarded")
    def validate_credit_awarded(self, _key: str, value: Decimal | None) -> Decimal | None:
        return validate_non_negative_decimal(value, "credit_awarded")

    @validates("effective_to")
    def validate_effective_to(self, _key: str, value: date | None) -> date | None:
        if value is not None and self.effective_from is not None and value < self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        return value
