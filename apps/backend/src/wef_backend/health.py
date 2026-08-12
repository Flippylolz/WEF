"""Liveness and database-readiness HTTP routes."""

from collections.abc import Awaitable, Callable
from typing import Literal, cast

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/api/v1/health", tags=["health"])
ReadyCheck = Callable[[], Awaitable[bool]]


class HealthResponse(BaseModel):
    """Machine-readable health response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["live", "ready"]


@router.get(
    "/live",
    operation_id="getLiveness",
    summary="Check process liveness",
)
async def liveness() -> HealthResponse:
    """Report that the event loop can serve requests."""
    return HealthResponse(status="live")


@router.get(
    "/ready",
    operation_id="getReadiness",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Database unavailable"}},
    summary="Check database readiness",
)
async def readiness(request: Request) -> HealthResponse:
    """Report readiness only when the composed database check succeeds."""
    ready_check = cast("ReadyCheck", request.app.state.is_ready)
    if not await ready_check():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="service is not ready",
        )
    return HealthResponse(status="ready")
