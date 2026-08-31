import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ApplicationException(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "APPLICATION_ERROR"
    default_message = "Application error"

    def __init__(self, message: str | None = None, details: Any | None = None) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.details = details


class ValidationException(ApplicationException):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "VALIDATION_ERROR"
    default_message = "Validation failed"


class NotFoundException(ApplicationException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    default_message = "Resource was not found"


class ForbiddenException(ApplicationException):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"
    default_message = "Action is not permitted"


class AccessDeniedException(ForbiddenException):
    code = "ACCESS_DENIED"
    default_message = "Insufficient permissions"


class UnauthorizedException(ApplicationException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"
    default_message = "Authentication required"


class AuthenticationRequiredException(UnauthorizedException):
    code = "AUTHENTICATION_REQUIRED"
    default_message = "Authentication credentials were not provided"


class InvalidCredentialsException(UnauthorizedException):
    code = "INVALID_CREDENTIALS"
    default_message = "Invalid email or password"


class InvalidTokenException(UnauthorizedException):
    code = "INVALID_TOKEN"
    default_message = "Invalid access token"


class ExpiredTokenException(UnauthorizedException):
    code = "TOKEN_EXPIRED"
    default_message = "Access token has expired"


class ConflictException(ApplicationException):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    default_message = "Resource conflict"


class ServiceUnavailableException(ApplicationException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "SERVICE_UNAVAILABLE"
    default_message = "Service is unavailable"


def error_response(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


async def application_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, ApplicationException):
        exc = ApplicationException()

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(code=exc.code, message=exc.message, details=exc.details),
    )


async def http_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                code="INTERNAL_SERVER_ERROR",
                message="Internal server error",
                details=None,
            ),
        )

    message = str(exc.detail) if exc.detail else "HTTP error"
    code = "NOT_FOUND" if exc.status_code == status.HTTP_404_NOT_FOUND else "HTTP_ERROR"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(code=code, message=message, details=None),
    )


async def validation_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    details = exc.errors() if isinstance(exc, RequestValidationError) else None
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details=details,
        ),
    )


async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code="INTERNAL_SERVER_ERROR",
            message="Internal server error",
            details=None,
        ),
    )


def add_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationException, application_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)