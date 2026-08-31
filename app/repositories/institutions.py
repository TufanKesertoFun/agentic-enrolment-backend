from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.models import Country, Institution


class InstitutionRepository(Protocol):
    async def get_country_by_code(self, code: str) -> Country | None: ...

    async def list_active_countries(self) -> Sequence[Country]: ...

    async def get_institution_by_id(self, institution_id: UUID) -> Institution | None: ...

    async def get_institution_by_external_code(
        self,
        country_id: UUID,
        external_code: str,
    ) -> Institution | None: ...

    async def add_institution(self, institution: Institution) -> Institution: ...
