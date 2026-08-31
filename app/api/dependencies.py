from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import AuthenticatedUser
from app.core.exceptions import AccessDeniedException
from app.domain.enums import RoleName
from app.infrastructure.database.session import get_db
from app.infrastructure.repositories.enrolments import SqlAlchemyEnrolmentRepository
from app.infrastructure.repositories.students import SqlAlchemyStudentRepository
from app.models import Student
from app.repositories.enrolments import EnrolmentRepository
from app.repositories.students import StudentRepository
from app.services.student_enrolment import StudentEnrolmentService


def get_student_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> StudentRepository:
    return SqlAlchemyStudentRepository(session)


def get_enrolment_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EnrolmentRepository:
    return SqlAlchemyEnrolmentRepository(session)


def get_student_enrolment_service(
    student_repository: Annotated[StudentRepository, Depends(get_student_repository)],
    enrolment_repository: Annotated[EnrolmentRepository, Depends(get_enrolment_repository)],
) -> StudentEnrolmentService:
    return StudentEnrolmentService(
        student_repository=student_repository,
        enrolment_repository=enrolment_repository,
    )


async def get_current_student(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    student_repository: Annotated[StudentRepository, Depends(get_student_repository)],
) -> Student:
    if not current_user.has_role(RoleName.STUDENT):
        raise AccessDeniedException()

    student = await student_repository.get_by_user_id(current_user.user_id)
    if student is None:
        raise AccessDeniedException(message="Authenticated student record was not found")

    return student
