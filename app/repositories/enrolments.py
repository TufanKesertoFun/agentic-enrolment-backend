from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.models import EnrolmentApplication


class EnrolmentRepository(Protocol):
    async def get_application_by_id(self, application_id: UUID) -> EnrolmentApplication | None: ...

    async def list_applications_for_student(
        self, student_id: UUID
    ) -> Sequence[EnrolmentApplication]: ...

    async def add_application(self, application: EnrolmentApplication) -> EnrolmentApplication: ...
