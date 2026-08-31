import logging

from fastapi import APIRouter, status

from app.core.exceptions import ServiceUnavailableException
from app.infrastructure.database.session import check_database_connection
from app.schemas.common import ErrorResponse, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, response_model_exclude_none=True)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="backend")


@router.get("/health/live", response_model=HealthResponse, response_model_exclude_none=True)
async def liveness() -> HealthResponse:
    return HealthResponse(status="alive")


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    response_model_exclude_none=True,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse}},
)
async def readiness() -> HealthResponse:
    try:
        await check_database_connection()
    except Exception as exc:
        logger.warning("Database readiness check failed: %s", exc.__class__.__name__)
        raise ServiceUnavailableException(
            message="Database is unavailable",
            details={"database": "unavailable"},
        ) from exc

    return HealthResponse(status="ready", database="available")
