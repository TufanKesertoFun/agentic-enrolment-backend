from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import EnrolmentApplicationStatus
from app.models import EnrolmentApplication, Program


class SqlAlchemyEnrolmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_application_by_id(self, application_id: UUID) -> EnrolmentApplication | None:
        result = await self._session.execute(
            select(EnrolmentApplication).where(EnrolmentApplication.id == application_id),
        )
        return result.scalar_one_or_none()

    async def list_applications_for_student(
        self,
        student_id: UUID,
    ) -> Sequence[EnrolmentApplication]:
        return await self.list_for_student(student_id)

    async def list_for_student(self, student_id: UUID) -> Sequence[EnrolmentApplication]:
        result = await self._session.execute(
            select(EnrolmentApplication)
            .where(EnrolmentApplication.student_id == student_id)
            .order_by(EnrolmentApplication.created_at.desc()),
        )
        return result.scalars().all()

    async def get_for_student(
        self,
        student_id: UUID,
        application_id: UUID,
    ) -> EnrolmentApplication | None:
        result = await self._session.execute(
            select(EnrolmentApplication).where(
                EnrolmentApplication.id == application_id,
                EnrolmentApplication.student_id == student_id,
            ),
        )
        return result.scalar_one_or_none()

    async def get_active_program(self, program_id: UUID) -> Program | None:
        result = await self._session.execute(
            select(Program).where(Program.id == program_id, Program.active.is_(True)),
        )
        return result.scalar_one_or_none()

    async def add_application(self, application: EnrolmentApplication) -> EnrolmentApplication:
        return await self.create(application)

    async def create(self, application: EnrolmentApplication) -> EnrolmentApplication:
        if application.status is None:
            application.status = EnrolmentApplicationStatus.DRAFT
        self._session.add(application)
        await self._session.flush()
        await self._session.refresh(application)
        await self._session.commit()
        return application

    async def save(self, application: EnrolmentApplication) -> EnrolmentApplication:
        self._session.add(application)
        await self._session.flush()
        await self._session.refresh(application)
        await self._session.commit()
        return application
