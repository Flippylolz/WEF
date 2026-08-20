"""Starlette Admin auth provider backed by identity sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from starlette.responses import RedirectResponse, Response
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed

from wef_backend.features.identity.application.identity import (
    IdentityService,
    InvalidCredentialsError,
)
from wef_backend.features.identity.domain.model import UserRole
from wef_backend.features.identity.interface.router import SESSION_COOKIE

if TYPE_CHECKING:
    from starlette.requests import Request

    from wef_backend.features.admin.application.admin_ops import AdminService

LOGIN_RATE_LIMIT = 10
LOGIN_RATE_WINDOW_SECONDS = 600


class OwnerAuthProvider(AuthProvider):
    """Authenticate owners through the existing opaque session cookie."""

    def __init__(
        self,
        identity: IdentityService,
        admin: AdminService,
        *,
        cookie_secure: bool,
    ) -> None:
        """Initialize the collaborator."""
        super().__init__()
        self._identity = identity
        self._admin = admin
        self._cookie_secure = cookie_secure

    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,  # noqa: FBT001 - required by AuthProvider.login
        request: Request,
    ) -> Response | None:
        """Validate owner credentials and set the identity session cookie."""
        del remember_me
        key = f"admin-login:{username[:64]}"
        if not self._identity.rate_limiter.allow(
            key,
            limit=LOGIN_RATE_LIMIT,
            window_seconds=LOGIN_RATE_WINDOW_SECONDS,
        ):
            msg = "Too many attempts. Try again later."
            raise LoginFailed(msg)
        try:
            result = await self._identity.authenticate(
                username=username,
                password=password,
            )
        except InvalidCredentialsError as error:
            msg = "Invalid username or password"
            raise LoginFailed(msg) from error
        account = result.account
        if account.role is not UserRole.OWNER:
            msg = "Invalid username or password"
            raise LoginFailed(msg)
        if account.must_change_password:
            msg = "Password change is required before using admin."
            raise LoginFailed(msg)
        response = RedirectResponse(url="/admin/", status_code=303)
        response.set_cookie(
            SESSION_COOKIE,
            result.raw_token,
            max_age=result.ttl_seconds,
            httponly=True,
            secure=self._cookie_secure,
            samesite="lax",
            path="/",
        )
        request.session["admin_owner_id"] = str(account.id)
        request.session["admin_username"] = account.username
        return response

    async def logout(self, request: Request) -> Response | None:
        """Revoke the identity session and clear admin cookies."""
        raw = request.cookies.get(SESSION_COOKIE, "")
        await self._identity.logout(raw)
        request.session.clear()
        response = RedirectResponse(url="/admin/login", status_code=303)
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    async def authenticate(self, request: Request) -> AdminUser | None:
        """Resolve the owner identity session for admin access."""
        raw = request.cookies.get(SESSION_COOKIE, "")
        account = await self._identity.resolve_session(raw)
        if account is None:
            return None
        if account.role is not UserRole.OWNER:
            return None
        if account.must_change_password:
            return None
        request.state.admin_owner_id = account.id
        request.state.admin_request_id = uuid4()
        request.state.admin = self._admin
        return AdminUser(username=account.username)
