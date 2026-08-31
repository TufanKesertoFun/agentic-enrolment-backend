from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.models import Course, HistoricalCreditMapping, Program


class AcademicRepository(Protocol):
    async def get_program_by_code(
        self, institution_id: UUID, program_code: str
    ) -> Program | None: ...

    async def get_course_by_code(self, institution_id: UUID, course_code: str) -> Course | None: ...

    async def list_courses_for_program(self, program_id: UUID) -> Sequence[Course]: ...

    async def add_program(self, program: Program) -> Program: ...

    async def add_course(self, course: Course) -> Course: ...

    async def list_historical_mappings_for_source_course(
        self,
        source_course_code: str,
    ) -> Sequence[HistoricalCreditMapping]: ...
