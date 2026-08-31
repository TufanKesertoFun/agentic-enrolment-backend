from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.models import EnrolmentApplication, Program


class EnrolmentRepository(Protocol):
    async def get_application_by_id(self, application_id: UUID) -> EnrolmentApplication | None: ...

    async def list_applications_for_student(
        self, student_id: UUID
    ) -> Sequence[EnrolmentApplication]: ...

    async def list_for_student(self, student_id: UUID) -> Sequence[EnrolmentApplication]: ...

    async def get_for_student(
        self,
        student_id: UUID,
        application_id: UUID,
    ) -> EnrolmentApplication | None: ...

    async def get_active_program(self, program_id: UUID) -> Program | None: ...

    async def add_application(self, application: EnrolmentApplication) -> EnrolmentApplication: ...

    async def create(self, application: EnrolmentApplication) -> EnrolmentApplication: ...

    async def save(self, application: EnrolmentApplication) -> EnrolmentApplication: ...
