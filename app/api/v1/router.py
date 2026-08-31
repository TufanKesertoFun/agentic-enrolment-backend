from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.institutions import router as institutions_router
from app.api.v1.endpoints.students import router as students_router

router = APIRouter()
router.include_router(auth_router, tags=["auth"])
router.include_router(health_router, tags=["health"])
router.include_router(students_router, tags=["students"])
router.include_router(institutions_router, tags=["institutions"])
