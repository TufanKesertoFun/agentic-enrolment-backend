from typing import Protocol
from uuid import UUID

from app.models import Student, StudentProfile


class StudentRepository(Protocol):
    async def get_by_id(self, student_id: UUID) -> Student | None: ...

    async def get_by_user_id(self, user_id: UUID) -> Student | None: ...

    async def get_by_student_number(
        self,
        institution_id: UUID,
        student_number: str,
    ) -> Student | None: ...

    async def get_by_institution_and_student_number(
        self,
        institution_id: UUID,
        student_number: str,
    ) -> Student | None: ...

    async def get_profile(self, student_id: UUID) -> StudentProfile | None: ...

    async def add(self, student: Student) -> Student: ...

    async def save_profile(self, profile: StudentProfile) -> StudentProfile: ...
