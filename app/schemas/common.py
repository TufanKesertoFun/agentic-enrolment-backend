from typing import Any

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str
    service: str | None = None
    database: str | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None

    model_config = ConfigDict(extra="forbid")


class ErrorResponse(BaseModel):
    error: ErrorDetail
