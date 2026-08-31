from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import EnrolmentApplicationStatus, StudentStatus


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CountrySummaryResponse(ReadModel):
    id: UUID
    code: str
    name: str


class InstitutionSummaryResponse(ReadModel):
    id: UUID
    name: str
    external_code: str | None = None


class ProgramSummaryResponse(ReadModel):
    id: UUID
    program_code: str
    name: str
    qualification_level: str
    active: bool


class StudentSummaryResponse(ReadModel):
    id: UUID
    student_number: str
    status: StudentStatus
    home_country: CountrySummaryResponse
    current_institution: InstitutionSummaryResponse
    current_program: ProgramSummaryResponse | None = None


class StudentProfileResponse(ReadModel):
    id: UUID
    student_id: UUID
    date_of_birth: date | None = None
    phone: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state_region: str | None = None
    postal_code: str | None = None
    country_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class StudentProfilePatchRequest(BaseModel):
    date_of_birth: date | None = None
    phone: str | None = Field(default=None, max_length=50)
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state_region: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=30)
    country_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")


class CreateEnrolmentApplicationRequest(BaseModel):
    program_id: UUID

    model_config = ConfigDict(extra="forbid")


class EnrolmentApplicationResponse(ReadModel):
    id: UUID
    student_id: UUID
    program_id: UUID
    status: EnrolmentApplicationStatus
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by_user_id: UUID | None = None
    decision_reason: str | None = None
    created_at: datetime
    updated_at: datetime
