from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_student_enrolment_service
from app.auth.models import AuthenticatedUser
from app.auth.permissions import require_any_role
from app.domain.enums import RoleName
from app.models import Student
from app.schemas.common import ErrorResponse
from app.schemas.students import StudentSummaryResponse
from app.services.student_enrolment import StudentEnrolmentService

router = APIRouter(prefix="/institutions")


@router.get(
    "/{institution_id}/students/{student_number}",
    response_model=StudentSummaryResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def get_student_by_institution_and_number(
    institution_id: UUID,
    student_number: str,
    _current_user: Annotated[
        AuthenticatedUser,
        Depends(
            require_any_role(
                RoleName.LECTURER,
                RoleName.ENROLMENT_OFFICER,
                RoleName.CREDIT_MAPPING_OFFICER,
                RoleName.ADMINISTRATOR,
            )
        ),
    ],
    service: Annotated[StudentEnrolmentService, Depends(get_student_enrolment_service)],
) -> Student:
    return await service.get_student_by_institution_and_number(
        institution_id=institution_id,
        student_number=student_number,
    )
