"""Owner-console Starlette Admin custom views."""

from __future__ import annotations

import contextlib
from html import escape
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from starlette.responses import RedirectResponse, Response
from starlette_admin import CustomView
from starlette_admin.routing import route
from starlette_admin.security.csrf import csrf_input
from starlette_admin.widgets import HtmlWidget, TableWidget

from wef_backend.features.admin.application.admin_ops import AdminDeniedError, AdminService

if TYPE_CHECKING:
    from starlette.requests import Request


def _admin(request: Request) -> AdminService:
    admin: AdminService = request.state.admin
    return admin


class UsersAdminView(CustomView):
    """List accounts and run owner-authorized account actions."""

    def __init__(self) -> None:
        """Initialize the collaborator."""
        super().__init__(
            menu_label="Users",
            icon="fa fa-users",
            path="/users",
            widget=self._users_widget,
        )

    async def _users_widget(self, request: Request) -> HtmlWidget:
        accounts = await _admin(request).list_accounts(limit=100)
        rows = "".join(
            (
                "<tr>"
                f"<td>{escape(account.username)}</td>"
                f"<td>{escape(account.role.value)}</td>"
                f"<td>{'active' if account.is_active else 'disabled'}</td>"
                f"<td>{'yes' if account.must_change_password else 'no'}</td>"
                f"<td><code>{escape(str(account.id))}</code></td>"
                "<td class='admin-actions'>"
                f"{_action_form(request, 'disable', account.id, 'Disable')}"
                f"{_action_form(request, 'reactivate', account.id, 'Reactivate')}"
                f"{_action_form(request, 'revoke', account.id, 'Revoke sessions')}"
                f"{_reset_form(request, account.id)}"
                "</td></tr>"
            )
            for account in accounts
        )
        html = (
            "<table><thead><tr>"
            "<th>Username</th><th>Role</th><th>Status</th>"
            "<th>Must change</th><th>Id</th><th>Actions</th>"
            f"</tr></thead><tbody>{rows or '<tr><td colspan=6>No accounts</td></tr>'}"
            "</tbody></table>"
        )
        return HtmlWidget(html=html)

    @route("/disable", methods=["POST"], name="disable")
    async def disable(self, request: Request) -> Response:
        """Disable one account through the owner interactor."""
        return await _run_user_action(request, "disable")

    @route("/reactivate", methods=["POST"], name="reactivate")
    async def reactivate(self, request: Request) -> Response:
        """Reactivate one account through the owner interactor."""
        return await _run_user_action(request, "reactivate")

    @route("/revoke", methods=["POST"], name="revoke")
    async def revoke(self, request: Request) -> Response:
        """Revoke sessions for one account through the owner interactor."""
        return await _run_user_action(request, "revoke")

    @route("/reset", methods=["POST"], name="reset")
    async def reset(self, request: Request) -> Response:
        """Force-reset one account password through the owner interactor."""
        form = await request.form()
        target = UUID(str(form.get("user_id")))
        temporary = str(form.get("temporary_password") or "")
        with contextlib.suppress(AdminDeniedError):
            await _admin(request).force_reset_password(
                owner_id=request.state.admin_owner_id,
                target_user_id=target,
                temporary_password=temporary,
                request_id=getattr(request.state, "admin_request_id", uuid4()),
            )
        return RedirectResponse(url="/admin/users", status_code=303)


async def _run_user_action(request: Request, action: str) -> Response:
    form = await request.form()
    target = UUID(str(form.get("user_id")))
    admin = _admin(request)
    owner_id = request.state.admin_owner_id
    request_id = getattr(request.state, "admin_request_id", uuid4())
    with contextlib.suppress(AdminDeniedError):
        if action == "disable":
            await admin.disable_user(
                owner_id=owner_id,
                target_user_id=target,
                request_id=request_id,
            )
        elif action == "reactivate":
            await admin.reactivate_user(
                owner_id=owner_id,
                target_user_id=target,
                request_id=request_id,
            )
        elif action == "revoke":
            await admin.revoke_user_sessions(
                owner_id=owner_id,
                target_user_id=target,
                request_id=request_id,
            )
    return RedirectResponse(url="/admin/users", status_code=303)


def _action_form(request: Request, action: str, user_id: UUID, label: str) -> str:
    return (
        f"<form method='post' action='/admin/users/{action}' style='display:inline'>"
        f"{csrf_input(request)}"
        f"<input type='hidden' name='user_id' value='{user_id}'/>"
        f"<button type='submit'>{escape(label)}</button></form> "
    )


def _reset_form(request: Request, user_id: UUID) -> str:
    return (
        "<form method='post' action='/admin/users/reset' style='display:inline'>"
        f"{csrf_input(request)}"
        f"<input type='hidden' name='user_id' value='{user_id}'/>"
        "<input type='password' name='temporary_password' "
        "placeholder='temporary password' minlength='10' required/>"
        "<button type='submit'>Force reset</button></form>"
    )


class RevealAuditsView(CustomView):
    """Read-only minimized contact reveal audits."""

    def __init__(self) -> None:
        """Initialize the collaborator."""
        super().__init__(
            menu_label="Reveal audits",
            icon="fa fa-eye",
            path="/reveal-audits",
            widget=TableWidget(
                title="Contact reveal audits",
                columns=["User", "Offer", "Outcome", "When", "Request"],
                rows_callback=_reveal_rows,
            ),
        )


async def _reveal_rows(request: Request) -> list[list[Any]]:
    rows = await _admin(request).list_reveal_audits(limit=100)
    return [
        [
            str(row.user_id),
            str(row.offer_id),
            row.outcome,
            row.revealed_at.isoformat(),
            str(row.request_id),
        ]
        for row in rows
    ]


class AdminAuditsView(CustomView):
    """Read-only redacted admin action history."""

    def __init__(self) -> None:
        """Initialize the collaborator."""
        super().__init__(
            menu_label="Admin audits",
            icon="fa fa-clipboard-list",
            path="/admin-audits",
            widget=TableWidget(
                title="Admin audits",
                columns=["Owner", "Action", "Target", "Outcome", "When"],
                rows_callback=_admin_audit_rows,
            ),
        )


async def _admin_audit_rows(request: Request) -> list[list[Any]]:
    rows = await _admin(request).list_admin_audits(limit=100)
    return [
        [
            str(row.owner_user_id),
            row.action,
            row.target_id or "",
            row.outcome.value,
            row.occurred_at.isoformat(),
        ]
        for row in rows
    ]
