from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import Table

from app.domain.enums import (
    CreditMappingDecisionValue,
    CreditMappingRequestStatus,
    EnrolmentApplicationStatus,
    StudentDocumentStatus,
)
from app.models import (
    Country,
    Course,
    CreditMappingDecision,
    Program,
    Student,
    StudentDocument,
    User,
)


def test_student_number_uniqueness_is_scoped_to_current_institution() -> None:
    table = cast(Table, Student.__table__)
    constraint_names = {constraint.name for constraint in table.constraints}
    index_names = {index.name for index in table.indexes}

    assert "uq_students_institution_student_number" in constraint_names
    assert "ix_students_student_number" in index_names


def test_user_email_is_normalized_and_indexed_case_insensitively() -> None:
    user = User(email=" Demo.Student@Example.Invalid ", first_name="Demo", last_name="Student")
    table = cast(Table, User.__table__)
    index_names = {index.name for index in table.indexes}

    assert user.email == "demo.student@example.invalid"
    assert "ix_users_email_lower" in index_names


def test_country_code_uses_two_character_iso_style_code() -> None:
    country = Country(code="au", name="Australia")

    assert country.code == "AU"

    with pytest.raises(ValueError, match="two-character"):
        Country(code="AUS", name="Australia")


def test_enrolment_and_credit_mapping_statuses_are_explicit() -> None:
    expected = {
        "DRAFT",
        "SUBMITTED",
        "UNDER_REVIEW",
        "MORE_INFORMATION_REQUIRED",
        "APPROVED",
        "REJECTED",
    }

    assert {status.value for status in EnrolmentApplicationStatus} == expected
    assert {status.value for status in CreditMappingRequestStatus} == expected


def test_student_document_file_size_cannot_be_negative() -> None:
    with pytest.raises(ValueError, match="file_size"):
        StudentDocument(file_size=-1)

    assert StudentDocument(file_size=0).file_size == 0
    assert StudentDocumentStatus.PENDING.value == "PENDING"


def test_credit_values_cannot_be_negative() -> None:
    with pytest.raises(ValueError, match="total_credits"):
        Program(total_credits=Decimal("-1.00"))

    with pytest.raises(ValueError, match="credit_value"):
        Course(credit_value=Decimal("-1.00"))


def test_course_effective_date_range_is_validated() -> None:
    with pytest.raises(ValueError, match="effective_to"):
        Course(
            credit_value=Decimal("3.00"),
            effective_from=datetime(2026, 1, 1, tzinfo=UTC).date(),
            effective_to=datetime(2025, 1, 1, tzinfo=UTC).date(),
        )


def test_credit_mapping_decision_requires_human_user_reference() -> None:
    with pytest.raises(ValueError, match="human decided_by_user_id"):
        CreditMappingDecision(decided_by_user_id=None)

    human_user_id = uuid4()
    decision = CreditMappingDecision(
        decision=CreditMappingDecisionValue.APPROVED,
        decided_by_user_id=human_user_id,
        decided_at=datetime.now(UTC),
        reason="Mock development decision.",
    )

    assert decision.decided_by_user_id == human_user_id
