"""Safe RFC 9457-style HTTP problem responses."""

from typing import Literal, cast
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


class AuthProblemError(Exception):
    """Raised when an authentication transport decision must become a problem."""

    def __init__(self, *, status_code: int, code: str, detail: str) -> None:
        """Store the bounded public problem fields."""
        self.status_code = status_code
        self.code = code
        self.detail = detail
        super().__init__(detail)


class AuthProblemResponse(BaseModel):
    """Stable authentication problem envelope without credentials."""

    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int
    code: str
    request_id: UUID
    detail: str
    instance: str
    kind: Literal["auth"] = "auth"


async def auth_problem_handler(request: Request, error: Exception) -> JSONResponse:
    """Present one bounded authentication problem response."""
    problem_error = cast("AuthProblemError", error)
    problem = AuthProblemResponse(
        type="https://wef.invalid/problems/auth",
        title="Authentication problem",
        status=problem_error.status_code,
        code=problem_error.code,
        request_id=request.state.request_id,
        detail=problem_error.detail,
        instance=request.url.path,
    )
    return JSONResponse(
        status_code=problem_error.status_code,
        content=problem.model_dump(mode="json"),
        media_type="application/problem+json",
    )


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
