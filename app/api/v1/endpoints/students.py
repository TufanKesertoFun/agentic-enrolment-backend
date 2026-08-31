from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_student, get_student_enrolment_service
from app.models import EnrolmentApplication, Student, StudentProfile
from app.schemas.common import ErrorResponse
from app.schemas.students import (
    CreateEnrolmentApplicationRequest,
    EnrolmentApplicationResponse,
    StudentProfilePatchRequest,
    StudentProfileResponse,
    StudentSummaryResponse,
)
from app.services.student_enrolment import StudentEnrolmentService

router = APIRouter(prefix="/students")


@router.get(
    "/me",
    response_model=StudentSummaryResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    },
)
async def get_current_student_summary(
    current_student: Annotated[Student, Depends(get_current_student)],
) -> Student:
    return current_student


@router.get(
    "/me/profile",
    response_model=StudentProfileResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def get_current_student_profile(
    current_student: Annotated[Student, Depends(get_current_student)],
    service: Annotated[StudentEnrolmentService, Depends(get_student_enrolment_service)],
) -> StudentProfile:
    return await service.get_current_student_profile(current_student)


@router.patch(
    "/me/profile",
    response_model=StudentProfileResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    },
)
async def update_current_student_profile(
    payload: StudentProfilePatchRequest,
    current_student: Annotated[Student, Depends(get_current_student)],
    service: Annotated[StudentEnrolmentService, Depends(get_student_enrolment_service)],
) -> StudentProfile:
    return await service.update_current_student_profile(current_student, payload)


@router.get(
    "/me/enrolment-applications",
    response_model=list[EnrolmentApplicationResponse],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    },
)
async def list_current_student_enrolment_applications(
    current_student: Annotated[Student, Depends(get_current_student)],
    service: Annotated[StudentEnrolmentService, Depends(get_student_enrolment_service)],
) -> Sequence[EnrolmentApplication]:
    return await service.list_current_student_enrolment_applications(current_student)


@router.post(
    "/me/enrolment-applications",
    response_model=EnrolmentApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def create_current_student_enrolment_application(
    payload: CreateEnrolmentApplicationRequest,
    current_student: Annotated[Student, Depends(get_current_student)],
    service: Annotated[StudentEnrolmentService, Depends(get_student_enrolment_service)],
) -> EnrolmentApplication:
    return await service.create_current_student_enrolment_application(
        student=current_student,
        program_id=payload.program_id,
    )


@router.get(
    "/me/enrolment-applications/{application_id}",
    response_model=EnrolmentApplicationResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def get_current_student_enrolment_application(
    application_id: UUID,
    current_student: Annotated[Student, Depends(get_current_student)],
    service: Annotated[StudentEnrolmentService, Depends(get_student_enrolment_service)],
) -> EnrolmentApplication:
    return await service.get_current_student_enrolment_application(current_student, application_id)


@router.post(
    "/me/enrolment-applications/{application_id}/submit",
    response_model=EnrolmentApplicationResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def submit_current_student_enrolment_application(
    application_id: UUID,
    current_student: Annotated[Student, Depends(get_current_student)],
    service: Annotated[StudentEnrolmentService, Depends(get_student_enrolment_service)],
) -> EnrolmentApplication:
    return await service.submit_current_student_enrolment_application(
        current_student,
        application_id,
    )
