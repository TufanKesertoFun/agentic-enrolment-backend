from app.repositories.academic import AcademicRepository
from app.repositories.base import Repository
from app.repositories.credit_mappings import CreditMappingRepository
from app.repositories.enrolments import EnrolmentRepository
from app.repositories.institutions import InstitutionRepository
from app.repositories.students import StudentRepository
from app.repositories.users import AuthUserRepository

__all__ = [
    "AcademicRepository",
    "AuthUserRepository",
    "CreditMappingRepository",
    "EnrolmentRepository",
    "InstitutionRepository",
    "Repository",
    "StudentRepository",
]