from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Country, Institution, Program, Student, StudentProfile


class SqlAlchemyStudentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, student_id: UUID) -> Student | None:
        result = await self._session.execute(
            _student_summary_query().where(Student.id == student_id),
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> Student | None:
        result = await self._session.execute(
            _student_summary_query().where(Student.user_id == user_id),
        )
        return result.scalar_one_or_none()

    async def get_by_student_number(
        self,
        institution_id: UUID,
        student_number: str,
    ) -> Student | None:
        return await self.get_by_institution_and_student_number(institution_id, student_number)

    async def get_by_institution_and_student_number(
        self,
        institution_id: UUID,
        student_number: str,
    ) -> Student | None:
        result = await self._session.execute(
            _student_summary_query().where(
                Student.current_institution_id == institution_id,
                Student.student_number == student_number.strip(),
            ),
        )
        return result.scalar_one_or_none()

    async def get_profile(self, student_id: UUID) -> StudentProfile | None:
        result = await self._session.execute(
            select(StudentProfile)
            .options(selectinload(StudentProfile.country))
            .where(StudentProfile.student_id == student_id),
        )
        return result.scalar_one_or_none()

    async def country_exists(self, country_id: UUID) -> bool:
        result = await self._session.execute(
            select(Country.id).where(Country.id == country_id),
        )
        return result.scalar_one_or_none() is not None

    async def add(self, student: Student) -> Student:
        self._session.add(student)
        await self._session.flush()
        await self._session.refresh(student)
        return student

    async def save_profile(self, profile: StudentProfile) -> StudentProfile:
        self._session.add(profile)
        await self._session.flush()
        await self._session.refresh(profile)
        await self._session.commit()
        return profile


def _student_summary_query() -> Any:
    return select(Student).options(
        selectinload(Student.home_country).load_only(Country.id, Country.code, Country.name),
        selectinload(Student.current_institution).load_only(
            Institution.id,
            Institution.name,
            Institution.external_code,
        ),
        selectinload(Student.current_program).load_only(
            Program.id,
            Program.program_code,
            Program.name,
            Program.qualification_level,
            Program.active,
        ),
    )
