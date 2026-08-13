"""Safe RFC 9457-style HTTP problem responses."""

from typing import Literal
from uuid import UUID

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class ProblemResponse(BaseModel):
    """Stable public error envelope without rejected values."""

    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int
    code: str
    request_id: UUID
    detail: str
    instance: str
    kind: Literal["validation_error"] = "validation_error"


class NotFoundProblemResponse(BaseModel):
    """Stable not-found envelope shared by absent and hidden resources."""

    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int
    code: str
    request_id: UUID
    detail: str
    instance: str
    kind: Literal["not_found"] = "not_found"


class QueryValidationError(ValueError):
    """Application-level invalid query combination."""


class ResourceNotFoundError(LookupError):
    """Raised when a public resource is absent or not visible."""


def problem_response(
    *,
    request: Request,
    detail: str,
    code: str = "invalid_query",
) -> JSONResponse:
    """Build one bounded validation problem response."""
    request_id = request.state.request_id
    problem = ProblemResponse(
        type="https://wef.invalid/problems/invalid-query",
        title="Invalid query parameters",
        status=422,
        code=code,
        request_id=request_id,
        detail=detail,
        instance=request.url.path,
    )
    return JSONResponse(
        status_code=422,
        content=problem.model_dump(mode="json"),
        media_type="application/problem+json",
    )


async def request_validation_handler(
    request: Request,
    _: Exception,
) -> JSONResponse:
    """Hide rejected input while retaining a stable client error."""
    return problem_response(
        request=request,
        detail="One or more query parameters are invalid.",
    )


async def query_validation_handler(
    request: Request,
    error: Exception,
) -> JSONResponse:
    """Present bounded application filter validation."""
    return problem_response(request=request, detail=str(error))


async def resource_not_found_handler(
    request: Request,
    _: Exception,
) -> JSONResponse:
    """Return the same response for absent and non-public resources."""
    problem = NotFoundProblemResponse(
        type="https://wef.invalid/problems/not-found",
        title="Resource not found",
        status=404,
        code="not_found",
        request_id=request.state.request_id,
        detail="The requested resource was not found.",
        instance=request.url.path,
    )
    return JSONResponse(
        status_code=404,
        content=problem.model_dump(mode="json"),
        media_type="application/problem+json",
    )
