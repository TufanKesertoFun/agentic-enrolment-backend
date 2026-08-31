from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    CreditMappingDecisionValue,
    CreditMappingRequestStatus,
    CreditSystem,
    EnrolmentApplicationStatus,
    ExternalProfileType,
    InstitutionType,
    StudentDocumentStatus,
    StudentDocumentType,
    StudentStatus,
)


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedRead(ReadModel):
    id: UUID
    created_at: datetime
    updated_at: datetime


class CreatedRead(ReadModel):
    id: UUID
    created_at: datetime


class CountryBase(BaseModel):
    code: str = Field(min_length=2, max_length=2)
    name: str
    default_locale: str | None = None
    active: bool = True


class CountryCreate(CountryBase):
    pass


class CountryUpdate(BaseModel):
    name: str | None = None
    default_locale: str | None = None
    active: bool | None = None


class CountryRead(CountryBase, TimestampedRead):
    pass


class InstitutionBase(BaseModel):
    name: str
    country_id: UUID
    external_code: str | None = None
    website_url: str | None = None
    institution_type: InstitutionType = InstitutionType.UNIVERSITY
    active: bool = True


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionUpdate(BaseModel):
    name: str | None = None
    external_code: str | None = None
    website_url: str | None = None
    institution_type: InstitutionType | None = None
    active: bool | None = None


class InstitutionRead(InstitutionBase, TimestampedRead):
    pass


class ProgramBase(BaseModel):
    institution_id: UUID
    program_code: str
    name: str
    qualification_level: str
    credit_system: CreditSystem
    total_credits: Decimal = Field(ge=0)
    active: bool = True
    effective_from: date | None = None
    effective_to: date | None = None


class ProgramCreate(ProgramBase):
    pass


class ProgramUpdate(BaseModel):
    name: str | None = None
    qualification_level: str | None = None
    credit_system: CreditSystem | None = None
    total_credits: Decimal | None = Field(default=None, ge=0)
    active: bool | None = None
    effective_from: date | None = None
    effective_to: date | None = None


class ProgramRead(ProgramBase, TimestampedRead):
    pass


class CourseBase(BaseModel):
    institution_id: UUID
    program_id: UUID | None = None
    course_code: str
    title: str
    description: str | None = None
    credit_value: Decimal = Field(ge=0)
    credit_system: CreditSystem
    effective_from: date | None = None
    effective_to: date | None = None
    active: bool = True


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    program_id: UUID | None = None
    title: str | None = None
    description: str | None = None
    credit_value: Decimal | None = Field(default=None, ge=0)
    credit_system: CreditSystem | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    active: bool | None = None


class CourseRead(CourseBase, TimestampedRead):
    pass


class StudentBase(BaseModel):
    user_id: UUID
    student_number: str
    home_country_id: UUID
    current_institution_id: UUID
    current_program_id: UUID | None = None
    status: StudentStatus = StudentStatus.PROSPECTIVE


class StudentCreate(StudentBase):
    pass


class StudentRead(StudentBase, TimestampedRead):
    pass


class StudentProfileBase(BaseModel):
    student_id: UUID
    date_of_birth: date | None = None
    phone: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state_region: str | None = None
    postal_code: str | None = None
    country_id: UUID | None = None


class StudentProfileCreate(StudentProfileBase):
    pass


class StudentProfileUpdate(BaseModel):
    date_of_birth: date | None = None
    phone: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state_region: str | None = None
    postal_code: str | None = None
    country_id: UUID | None = None


class StudentProfileRead(StudentProfileBase, TimestampedRead):
    pass


class PreviousEducationBase(BaseModel):
    student_id: UUID
    institution_id: UUID | None = None
    institution_name_snapshot: str
    country_id: UUID
    qualification_name: str
    qualification_level: str
    start_date: date | None = None
    end_date: date | None = None
    completed: bool = False


class PreviousEducationCreate(PreviousEducationBase):
    pass


class PreviousEducationRead(PreviousEducationBase, TimestampedRead):
    pass


class PreviousCourseBase(BaseModel):
    previous_education_id: UUID
    external_course_code: str | None = None
    course_title: str
    description: str | None = None
    credit_value: Decimal | None = Field(default=None, ge=0)
    credit_system: CreditSystem | None = None
    grade: str | None = None
    result: str | None = None
    year_completed: int | None = None


class PreviousCourseCreate(PreviousCourseBase):
    pass


class PreviousCourseRead(PreviousCourseBase, TimestampedRead):
    pass


class QualificationBase(BaseModel):
    student_id: UUID
    name: str
    issuing_organization: str
    country_id: UUID | None = None
    issued_date: date | None = None
    expiry_date: date | None = None
    credential_reference: str | None = None


class QualificationCreate(QualificationBase):
    pass


class QualificationRead(QualificationBase, TimestampedRead):
    pass


class ExternalProfileLinkBase(BaseModel):
    student_id: UUID
    profile_type: ExternalProfileType
    url: str
    consent_given: bool = False
    consent_given_at: datetime | None = None


class ExternalProfileLinkCreate(ExternalProfileLinkBase):
    pass


class ExternalProfileLinkRead(ExternalProfileLinkBase, TimestampedRead):
    pass


class StudentDocumentBase(BaseModel):
    student_id: UUID
    document_type: StudentDocumentType
    original_filename: str
    content_type: str
    file_size: int = Field(ge=0)
    storage_key: str
    checksum: str | None = None
    status: StudentDocumentStatus = StudentDocumentStatus.PENDING
    uploaded_at: datetime | None = None


class StudentDocumentCreate(StudentDocumentBase):
    pass


class StudentDocumentRead(StudentDocumentBase, TimestampedRead):
    pass


class EnrolmentApplicationBase(BaseModel):
    student_id: UUID
    program_id: UUID
    status: EnrolmentApplicationStatus = EnrolmentApplicationStatus.DRAFT
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by_user_id: UUID | None = None
    decision_reason: str | None = None


class EnrolmentApplicationCreate(EnrolmentApplicationBase):
    pass


class EnrolmentApplicationUpdate(BaseModel):
    status: EnrolmentApplicationStatus | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by_user_id: UUID | None = None
    decision_reason: str | None = None


class EnrolmentApplicationRead(EnrolmentApplicationBase, TimestampedRead):
    pass


class CreditMappingRequestBase(BaseModel):
    student_id: UUID
    source_previous_course_id: UUID
    target_course_id: UUID
    status: CreditMappingRequestStatus = CreditMappingRequestStatus.DRAFT
    requested_by_user_id: UUID
    assigned_reviewer_user_id: UUID | None = None
    submitted_at: datetime | None = None


class CreditMappingRequestCreate(CreditMappingRequestBase):
    pass


class CreditMappingRequestUpdate(BaseModel):
    status: CreditMappingRequestStatus | None = None
    assigned_reviewer_user_id: UUID | None = None
    submitted_at: datetime | None = None


class CreditMappingRequestRead(CreditMappingRequestBase, TimestampedRead):
    pass


class CreditMappingDecisionBase(BaseModel):
    credit_mapping_request_id: UUID
    decision: CreditMappingDecisionValue
    decided_by_user_id: UUID
    reason: str
    credit_awarded: Decimal | None = Field(default=None, ge=0)
    decided_at: datetime


class CreditMappingDecisionCreate(CreditMappingDecisionBase):
    pass


class CreditMappingDecisionRead(CreditMappingDecisionBase, CreatedRead):
    pass
