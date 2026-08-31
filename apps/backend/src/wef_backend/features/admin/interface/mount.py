"""Mount the owner Starlette Admin console."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_admin import BaseAdmin

from wef_backend.features.admin.interface.auth import OwnerAuthProvider
from wef_backend.features.admin.interface.enrichment_views import OfferEnrichmentAdminView
from wef_backend.features.admin.interface.guards import AdminMutationGuardMiddleware
from wef_backend.features.admin.interface.views import (
    AdminAuditsView,
    LocationsAdminView,
    RevealAuditsView,
    UsersAdminView,
)

if TYPE_CHECKING:
    from wef_backend.features.admin.application.admin_ops import AdminService
    from wef_backend.features.identity.application.identity import IdentityService

_STATIC_DIR = Path(__file__).parent / "statics"


def build_admin(
    *,
    secret_key: str,
    identity: IdentityService,
    admin: AdminService,
    cookie_secure: bool,
) -> BaseAdmin:
    """Create the owner admin app mount (not part of public OpenAPI)."""
    admin_app = BaseAdmin(
        title="WEF Owner Admin",
        base_url="/admin",
        route_name="admin",
        auth_provider=OwnerAuthProvider(
            identity,
            admin,
            cookie_secure=cookie_secure,
        ),
        secret_key=secret_key,
        static_dir=str(_STATIC_DIR),
        middlewares=[
            Middleware(AdminMutationGuardMiddleware, identity=identity),
            Middleware(
                SessionMiddleware,
                secret_key=secret_key,
                session_cookie="wef_admin_session",
                same_site="lax",
                https_only=cookie_secure,
            ),
        ],
    )
    admin_app.add_view(UsersAdminView())
    admin_app.add_view(LocationsAdminView())
    admin_app.add_view(OfferEnrichmentAdminView())
    admin_app.add_view(RevealAuditsView())
    admin_app.add_view(AdminAuditsView())
    return admin_app
