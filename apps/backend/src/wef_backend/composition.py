"""Explicit composition root for runtime services."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from wef_backend.database import create_database_resources
from wef_backend.features.admin.application import (
    AdminService,
    DisableUser,
    ForceResetUserPassword,
    ListAdminAccounts,
    ListAdminAudits,
    ListRevealAudits,
    ReactivateUser,
    RevokeUserSessions,
)
from wef_backend.features.admin.infrastructure import (
    SQLAlchemyAdminAuditStore,
    SQLAlchemyRevealAuditReader,
)
from wef_backend.features.catalog.application import (
    BrowseLocationOffers,
    GetOfferDetail,
    QueryFacets,
    QueryMapLocations,
)
from wef_backend.features.catalog.infrastructure import (
    SQLAlchemyCatalogBrowseAdapter,
    SQLAlchemyMapQueryAdapter,
    SQLAlchemyOfferDetailAdapter,
)
from wef_backend.features.contacts.application import (
    ContactService,
    PersistOfferContacts,
    RevealOfferContacts,
)
from wef_backend.features.contacts.infrastructure import (
    AesGcmContactCipher,
    SQLAlchemyContactStore,
    decode_secret_key,
)
from wef_backend.features.estates.application import ListEstates
from wef_backend.features.estates.infrastructure import RetiredEstateQueryAdapter
from wef_backend.features.identity.application import (
    AuthenticateAccount,
    ChangeAccountPassword,
    DeleteOwnAccount,
    DisableOwnAccount,
    IdentityService,
    LogoutSession,
    RegisterAccount,
    ResolveSession,
    RevokeAllAccountSessions,
)
from wef_backend.features.identity.application.favorites import (
    AddFavoriteLocation,
    FavoriteService,
    ListFavoriteLocations,
    RemoveFavoriteLocation,
)
from wef_backend.features.identity.infrastructure import (
    MemoryRateLimiter,
    PwdlibPasswordHasher,
    SecretsTokenService,
    SQLAlchemyFavoriteStore,
    SQLAlchemyIdentityStore,
    SystemClock,
)
from wef_backend.middleware.public_rate_limit import RateLimiter
from wef_backend.migration import EXPECTED_DATABASE_REVISION
from wef_backend.settings import Settings, load_settings

ReadyCheck = Callable[[], Awaitable[bool]]
ResourceCloser = Callable[[], Awaitable[None]]

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class AppServices:
    """Fully composed services placed on FastAPI app state."""

    list_estates: ListEstates
    query_map: QueryMapLocations
    query_facets: QueryFacets
    browse_location_offers: BrowseLocationOffers
    get_offer_detail: GetOfferDetail
    is_ready: ReadyCheck
    close: ResourceCloser
    identity: IdentityService
    favorites: FavoriteService
    contacts: ContactService
    admin: AdminService
    auth_cookie_secure: bool
    admin_session_secret: str
    public_rate_limiter: RateLimiter


def build_services(settings: Settings | None = None) -> AppServices:
    """Wire concrete adapters to inward-owned application contracts."""
    runtime_settings = settings or load_settings()
    database = create_database_resources(runtime_settings.database_url)
    map_adapter = SQLAlchemyMapQueryAdapter(database.session_factory)
    browse_adapter = SQLAlchemyCatalogBrowseAdapter(database.session_factory)
    offer_detail_adapter = SQLAlchemyOfferDetailAdapter(database.session_factory)
    identity_store = SQLAlchemyIdentityStore(database.session_factory)
    favorite_store = SQLAlchemyFavoriteStore(database.session_factory)
    contact_store = SQLAlchemyContactStore(database.session_factory)
    hasher = PwdlibPasswordHasher()
    tokens = SecretsTokenService()
    clock = SystemClock()
    contact_cipher = AesGcmContactCipher(
        encryption_key=decode_secret_key(
            runtime_settings.contact_encryption_key.get_secret_value()
            if runtime_settings.contact_encryption_key is not None
            else None,
        ),
        hmac_key=decode_secret_key(
            runtime_settings.contact_hmac_key.get_secret_value()
            if runtime_settings.contact_hmac_key is not None
            else None,
        ),
    )
    contact_rate_limiter = MemoryRateLimiter()
    admin_audit_store = SQLAlchemyAdminAuditStore(database.session_factory)
    reveal_audit_reader = SQLAlchemyRevealAuditReader(database.session_factory)
    admin_secret = (
        runtime_settings.admin_session_secret.get_secret_value()
        if runtime_settings.admin_session_secret is not None
        else "dev-only-admin-session-secret"
    )
    if runtime_settings.env == "production" and runtime_settings.admin_session_secret is None:
        msg = "WEF_ADMIN_SESSION_SECRET is required in production"
        raise RuntimeError(msg)

    async def database_is_ready() -> bool:
        try:
            async with database.session_factory() as session:
                revision = await session.scalar(
                    text("SELECT version_num FROM alembic_version"),
                )
        except SQLAlchemyError as error:
            logger.warning("database_not_ready", error=str(error))
            return False
        if revision != EXPECTED_DATABASE_REVISION:
            logger.warning(
                "database_revision_mismatch",
                expected=EXPECTED_DATABASE_REVISION,
                actual=revision,
            )
            return False
        return True

    return AppServices(
        list_estates=ListEstates(RetiredEstateQueryAdapter()),
        query_map=QueryMapLocations(map_adapter),
        query_facets=QueryFacets(browse_adapter),
        browse_location_offers=BrowseLocationOffers(browse_adapter),
        get_offer_detail=GetOfferDetail(offer_detail_adapter),
        is_ready=database_is_ready,
        close=database.engine.dispose,
        identity=IdentityService(
            register=RegisterAccount(identity_store, hasher),
            authenticate=AuthenticateAccount(
                identity_store,
                hasher,
                tokens,
                clock,
                session_ttl_seconds=runtime_settings.session_ttl_seconds,
            ),
            resolve_session=ResolveSession(identity_store, tokens, clock),
            logout=LogoutSession(identity_store, tokens),
            change_password=ChangeAccountPassword(identity_store, hasher, clock),
            revoke_all_sessions=RevokeAllAccountSessions(identity_store),
            disable_account=DisableOwnAccount(identity_store, clock),
            delete_account=DeleteOwnAccount(identity_store, clock),
            rate_limiter=MemoryRateLimiter(),
        ),
        favorites=FavoriteService(
            list_favorites=ListFavoriteLocations(favorite_store),
            add_favorite=AddFavoriteLocation(favorite_store),
            remove_favorite=RemoveFavoriteLocation(favorite_store),
        ),
        contacts=ContactService(
            persist=PersistOfferContacts(contact_store, contact_cipher),
            reveal=RevealOfferContacts(
                contact_store,
                contact_cipher,
                contact_rate_limiter,
            ),
            rate_limiter=contact_rate_limiter,
        ),
        admin=AdminService(
            list_accounts=ListAdminAccounts(identity_store),
            disable_user=DisableUser(identity_store, admin_audit_store, clock),
            reactivate_user=ReactivateUser(identity_store, admin_audit_store, clock),
            revoke_user_sessions=RevokeUserSessions(identity_store, admin_audit_store),
            force_reset_password=ForceResetUserPassword(
                identity_store,
                admin_audit_store,
                hasher,
                clock,
            ),
            list_reveal_audits=ListRevealAudits(reveal_audit_reader),
            list_admin_audits=ListAdminAudits(admin_audit_store),
        ),
        auth_cookie_secure=runtime_settings.env == "production",
        admin_session_secret=admin_secret,
        public_rate_limiter=MemoryRateLimiter(),
    )
