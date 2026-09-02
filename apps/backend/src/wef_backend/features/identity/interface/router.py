"""HTTP adapter for pseudonymous registration and opaque sessions."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, StringConstraints

from wef_backend.errors import AuthProblemError
from wef_backend.features.identity.application.identity import (
    AccountView,
    IdentityService,
    InvalidCredentialsError,
    RegistrationDeclinedError,
)
from wef_backend.features.identity.domain.model import PasswordPolicyError

SESSION_COOKIE = "wef_session"

PasswordValue = Annotated[
    str,
    StringConstraints(strip_whitespace=False, min_length=10, max_length=256),
]
UsernameValue = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=64),
]

REGISTER_RATE_LIMIT = 5
REGISTER_RATE_WINDOW_SECONDS = 600
LOGIN_RATE_LIMIT = 10
LOGIN_RATE_WINDOW_SECONDS = 600
PASSWORD_RATE_LIMIT = 5
PASSWORD_RATE_WINDOW_SECONDS = 600


class RegisterRequest(BaseModel):
    """Strict registration syntax."""

    model_config = ConfigDict(extra="forbid")

    username: UsernameValue
    password: PasswordValue


class LoginRequest(BaseModel):
    """Strict login syntax."""

    model_config = ConfigDict(extra="forbid")

    username: UsernameValue
    password: PasswordValue


class ChangePasswordRequest(BaseModel):
    """Strict password-change syntax."""

    model_config = ConfigDict(extra="forbid")

    current_password: PasswordValue
    new_password: PasswordValue


class AccountResponse(BaseModel):
    """Minimal public account projection."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    username: str
    role: Literal["user", "owner"]
    must_change_password: bool
    created_at: str
    last_login_at: str | None


def _present_account(account: AccountView) -> AccountResponse:
    """Render one account view without hash, token, or status internals."""
    return AccountResponse(
        id=account.id,
        username=account.username,
        role=account.role.value,
        must_change_password=account.must_change_password,
        created_at=account.created_at.isoformat(),
        last_login_at=(account.last_login_at.isoformat() if account.last_login_at else None),
    )


def _identity(request: Request) -> IdentityService:
    """Return the composed identity service or refuse safely."""
    service: IdentityService | None = getattr(request.app.state, "identity", None)
    if service is None:
        raise AuthProblemError(
            status_code=503,
            code="identity_unavailable",
            detail="Authentication is currently unavailable.",
        )
    return service


def _enforce_trusted_origin(request: Request) -> None:
    """Require JSON mutations and same-origin browser requests."""
    if request.method == "GET":
        return
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        raise AuthProblemError(
            status_code=415,
            code="unsupported_media_type",
            detail="Mutations require a JSON content type.",
        )
    origin = request.headers.get("origin")
    if origin is None:
        return
    expected = str(request.base_url).rstrip("/")
    if origin != expected:
        raise AuthProblemError(
            status_code=403,
            code="origin_rejected",
            detail="Cross-origin mutations are not accepted.",
        )


def _client_key(request: Request, scope: str, subject: str) -> str:
    """Build one bounded in-memory rate-limit key without persisting it."""
    host = request.client.host if request.client is not None else "unknown"
    return f"{scope}:{host}:{subject[:64]}"


def _session_cookie_secure(request: Request) -> bool:
    """Report whether the environment requires Secure cookie transport."""
    return bool(getattr(request.app.state, "auth_cookie_secure", False))


async def _require_account(request: Request) -> AccountView:
    """Resolve the session cookie to an active account view."""
    service = _identity(request)
    raw_token = request.cookies.get(SESSION_COOKIE, "")
    account = await service.resolve_session(raw_token)
    if account is None:
        raise AuthProblemError(
            status_code=401,
            code="not_authenticated",
            detail="Authentication is required.",
        )
    return account


async def enforce_trusted_origin(request: Request) -> None:
    """Apply the origin and content-type guard before body validation."""
    _enforce_trusted_origin(request)


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
    dependencies=[Depends(enforce_trusted_origin)],
)


@router.post(
    "/register",
    status_code=201,
    operation_id="registerAccount",
    summary="Register one pseudonymous account",
    responses={
        409: {"description": "The username or registration was declined."},
        415: {"description": "Mutations require a JSON content type."},
        429: {"description": "Too many attempts from this client."},
    },
)
async def register_account(request: Request, payload: RegisterRequest) -> AccountResponse:
    """Create one user-role account; no session is established."""
    service = _identity(request)
    key = _client_key(request, "register", payload.username)
    if not service.rate_limiter.allow(
        key,
        limit=REGISTER_RATE_LIMIT,
        window_seconds=REGISTER_RATE_WINDOW_SECONDS,
    ):
        raise AuthProblemError(
            status_code=429,
            code="rate_limited",
            detail="Too many attempts. Try again later.",
        )
    try:
        account = await service.register(
            username=payload.username,
            password=payload.password,
        )
    except RegistrationDeclinedError as error:
        status_code = 409 if str(error) == "username unavailable" else 422
        raise AuthProblemError(
            status_code=status_code,
            code=str(error).replace(" ", "_"),
            detail=str(error).capitalize() + ".",
        ) from error
    return _present_account(account)


@router.post(
    "/login",
    operation_id="loginAccount",
    summary="Establish one opaque session",
    responses={
        401: {"description": "The credentials were not accepted."},
        415: {"description": "Mutations require a JSON content type."},
        429: {"description": "Too many attempts from this client."},
    },
)
async def login_account(
    request: Request, response: Response, payload: LoginRequest
) -> AccountResponse:
    """Verify credentials and set the HttpOnly session cookie."""
    service = _identity(request)
    key = _client_key(request, "login", payload.username)
    if not service.rate_limiter.allow(
        key,
        limit=LOGIN_RATE_LIMIT,
        window_seconds=LOGIN_RATE_WINDOW_SECONDS,
    ):
        raise AuthProblemError(
            status_code=429,
            code="rate_limited",
            detail="Too many attempts. Try again later.",
        )
    try:
        result = await service.authenticate(
            username=payload.username,
            password=payload.password,
        )
    except InvalidCredentialsError as error:
        raise AuthProblemError(
            status_code=401,
            code="invalid_credentials",
            detail="Invalid username or password.",
        ) from error
    response.set_cookie(
        SESSION_COOKIE,
        result.raw_token,
        max_age=result.ttl_seconds,
        httponly=True,
        secure=_session_cookie_secure(request),
        samesite="lax",
        path="/",
    )
    return _present_account(result.account)


@router.post(
    "/logout",
    status_code=204,
    operation_id="logoutAccount",
    summary="Revoke the current session",
    responses={
        415: {"description": "Mutations require a JSON content type."},
    },
)
async def logout_account(
    request: Request,
    response: Response,
    wef_session: Annotated[str | None, Cookie()] = None,
) -> None:
    """Revoke the session behind the cookie and clear it."""
    service = _identity(request)
    await service.logout(wef_session or "")
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get(
    "/me",
    operation_id="getOwnAccount",
    summary="View the authenticated account",
    responses={
        401: {"description": "Authentication is required."},
    },
)
async def get_own_account(request: Request, response: Response) -> AccountResponse:
    """Return the minimal account view for the current session."""
    response.headers["Cache-Control"] = "no-store, private"
    account = await _require_account(request)
    return _present_account(account)


@router.post(
    "/password",
    status_code=204,
    operation_id="changeOwnPassword",
    summary="Change the account password",
    responses={
        401: {"description": "Authentication is required."},
        415: {"description": "Mutations require a JSON content type."},
        429: {"description": "Too many attempts from this client."},
    },
)
async def change_own_password(
    request: Request,
    response: Response,
    payload: ChangePasswordRequest,
) -> None:
    """Verify the current password, rotate it, and revoke all sessions."""
    service = _identity(request)
    account = await _require_account(request)
    key = _client_key(request, "password", str(account.id))
    if not service.rate_limiter.allow(
        key,
        limit=PASSWORD_RATE_LIMIT,
        window_seconds=PASSWORD_RATE_WINDOW_SECONDS,
    ):
        raise AuthProblemError(
            status_code=429,
            code="rate_limited",
            detail="Too many attempts. Try again later.",
        )
    try:
        await service.change_password(
            account_id=account.id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except InvalidCredentialsError as error:
        raise AuthProblemError(
            status_code=401,
            code="invalid_credentials",
            detail="Invalid username or password.",
        ) from error
    except PasswordPolicyError as error:
        raise AuthProblemError(
            status_code=422,
            code="invalid_password",
            detail="The new password is invalid.",
        ) from error
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.post(
    "/sessions/revoke-all",
    status_code=204,
    operation_id="revokeOwnSessions",
    summary="Revoke every session of the account",
    responses={
        401: {"description": "Authentication is required."},
        415: {"description": "Mutations require a JSON content type."},
    },
)
async def revoke_own_sessions(request: Request, response: Response) -> None:
    """Revoke all sessions including the current one."""
    service = _identity(request)
    account = await _require_account(request)
    await service.revoke_all_sessions(account.id)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.post(
    "/account/disable",
    status_code=204,
    operation_id="disableOwnAccount",
    summary="Disable the authenticated account",
    responses={
        401: {"description": "Authentication is required."},
        415: {"description": "Mutations require a JSON content type."},
    },
)
async def disable_own_account(request: Request, response: Response) -> None:
    """Mark the account inactive and revoke all sessions."""
    service = _identity(request)
    account = await _require_account(request)
    await service.disable_account(account.id)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.post(
    "/account/delete",
    status_code=204,
    operation_id="deleteOwnAccount",
    summary="Soft-delete the authenticated account",
    responses={
        401: {"description": "Authentication is required."},
        415: {"description": "Mutations require a JSON content type."},
    },
)
async def delete_own_account(request: Request, response: Response) -> None:
    """Mark the account deleted and revoke all sessions."""
    service = _identity(request)
    account = await _require_account(request)
    await service.delete_account(account.id)
    response.delete_cookie(SESSION_COOKIE, path="/")
