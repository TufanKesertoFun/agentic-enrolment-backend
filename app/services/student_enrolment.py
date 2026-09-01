from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ConflictException, NotFoundException
from app.domain.enums import EnrolmentApplicationStatus
from app.models import EnrolmentApplication, Student, StudentProfile
from app.repositories.enrolments import EnrolmentRepository
from app.repositories.students import StudentRepository
from app.schemas.students import StudentProfilePatchRequest


class StudentEnrolmentService:
    def __init__(
        self,
        student_repository: StudentRepository,
        enrolment_repository: EnrolmentRepository,
    ) -> None:
        self._student_repository = student_repository
        self._enrolment_repository = enrolment_repository

    async def get_current_student_profile(self, student: Student) -> StudentProfile:
        profile = await self._student_repository.get_profile(student.id)
        if profile is None:
            raise NotFoundException(message="Student profile was not found")
        return profile

    async def update_current_student_profile(
        self,
        student: Student,
        request: StudentProfilePatchRequest,
    ) -> StudentProfile:
        profile = await self._student_repository.get_profile(student.id)
        if profile is None:
            profile = StudentProfile(student_id=student.id)

        updates = request.model_dump(exclude_unset=True)
        country_id = updates.get("country_id")
        if country_id is not None and not await self._student_repository.country_exists(country_id):
            raise NotFoundException(message="Country was not found")

        for field_name, value in updates.items():
            setattr(profile, field_name, value)

        return await self._student_repository.save_profile(profile)

    async def list_current_student_enrolment_applications(
        self,
        student: Student,
    ) -> Sequence[EnrolmentApplication]:
        return await self._enrolment_repository.list_for_student(student.id)

    async def create_current_student_enrolment_application(
        self,
        student: Student,
        program_id: UUID,
    ) -> EnrolmentApplication:
        program = await self._enrolment_repository.get_active_program(program_id)
        if program is None:
            raise NotFoundException(message="Program was not found")

        application = EnrolmentApplication(
            student_id=student.id,
            program_id=program.id,
            status=EnrolmentApplicationStatus.DRAFT,
        )
        return await self._enrolment_repository.create(application)

    async def get_current_student_enrolment_application(
        self,
        student: Student,
        application_id: UUID,
    ) -> EnrolmentApplication:
        application = await self._enrolment_repository.get_for_student(student.id, application_id)
        if application is None:
            raise NotFoundException(message="Enrolment application was not found")
        return application

    async def submit_current_student_enrolment_application(
        self,
        student: Student,
        application_id: UUID,
    ) -> EnrolmentApplication:
        application = await self.get_current_student_enrolment_application(student, application_id)
        if application.status != EnrolmentApplicationStatus.DRAFT:
            raise ConflictException(message="Only draft enrolment applications can be submitted")

        application.status = EnrolmentApplicationStatus.SUBMITTED
        application.submitted_at = datetime.now(UTC)
        return await self._enrolment_repository.save(application)

    async def get_student_by_institution_and_number(
        self,
        institution_id: UUID,
        student_number: str,
    ) -> Student:
        student = await self._student_repository.get_by_institution_and_student_number(
            institution_id=institution_id,
            student_number=student_number,
        )
        if student is None:
            raise NotFoundException(message="Student was not found")
        return student
