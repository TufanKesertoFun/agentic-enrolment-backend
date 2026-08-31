from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.models import CreditMappingDecision, CreditMappingEvidence, CreditMappingRequest


class CreditMappingRepository(Protocol):
    async def get_request_by_id(self, request_id: UUID) -> CreditMappingRequest | None: ...

    async def list_requests_for_student(
        self, student_id: UUID
    ) -> Sequence[CreditMappingRequest]: ...

    async def add_request(self, request: CreditMappingRequest) -> CreditMappingRequest: ...

    async def add_evidence(self, evidence: CreditMappingEvidence) -> CreditMappingEvidence: ...

    async def add_decision(self, decision: CreditMappingDecision) -> CreditMappingDecision: ...
