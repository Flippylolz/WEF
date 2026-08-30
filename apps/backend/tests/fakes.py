"""Small explicit test doubles for application and app-state boundaries."""

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from wef_backend.features.admin.application.admin_ops import (
    AcceptPlaceCandidate,
    AdminAuditEvent,
    AdminService,
    DisableUser,
    ForceResetUserPassword,
    GetLocationForEdit,
    ListAdminAccounts,
    ListAdminAudits,
    ListLocations,
    ListRevealAudits,
    LocationAdminSummary,
    LocationEditDetail,
    LocationStatusFilter,
    ReactivateUser,
    RejectPlace,
    RevealAuditSummary,
    RevokeUserSessions,
    SetPlacePoint,
    UnresolvePlace,
)
from wef_backend.features.catalog.application import (
    FacetSnapshot,
    ListingBrowseRecord,
    ListingCursor,
    MapFilters,
    MapLocationRecord,
    MapQuerySnapshot,
    OfferBrowseRecord,
    OfferBrowseSnapshot,
    OfferCursor,
    OfferDetailRecord,
    ViewportListingSnapshot,
)
from wef_backend.features.contacts.application.reveal import (
    ContactCipher,
    ContactCryptoUnavailableError,
    ContactService,
    PersistOfferContacts,
    RevealOfferContacts,
)
from wef_backend.features.contacts.domain.model import (
    ContactKind,
    ContactPointRecord,
    RevealOutcome,
)
from wef_backend.features.estates.application import EstateRecord
from wef_backend.features.identity.application.favorites import (
    AddFavoriteLocation,
    FavoriteLocationView,
    FavoriteService,
    ListFavoriteLocations,
    RemoveFavoriteLocation,
)
from wef_backend.features.identity.application.identity import (
    AccountView,
    AuthenticateAccount,
    ChangeAccountPassword,
    DeleteOwnAccount,
    DisableOwnAccount,
    IdentityService,
    LogoutSession,
    PasswordHasher,
    RegisterAccount,
    ResolveSession,
    RevokeAllAccountSessions,
)
from wef_backend.features.identity.application.view_history import (
    AccountVisitView,
    ListViewedOffers,
    MarkOfferViewed,
    StartAccountVisit,
    ViewedOfferView,
    ViewHistoryService,
)
from wef_backend.features.identity.domain.model import Account, AccountSession, UserRole


@dataclass(frozen=True, slots=True)
class FakeEstateQuery:
    """In-memory implementation of the application-owned query port."""

    records: tuple[EstateRecord, ...]

    async def list_estate_records(self) -> tuple[EstateRecord, ...]:
        """Return deterministic fake records."""
        return self.records


@dataclass(frozen=True, slots=True)
class FakeMapQuery:
    """In-memory implementation of the grouped map query port."""

    records: tuple[MapLocationRecord, ...] = ()

    async def query_map(self, _: MapFilters) -> MapQuerySnapshot:
        """Return deterministic grouped records without a database."""
        return MapQuerySnapshot(records=self.records, data_version=None)


@dataclass(frozen=True, slots=True)
class FakeCatalogBrowse:
    """In-memory facets, location-offer, and viewport-listing adapter."""

    facets: FacetSnapshot
    records: tuple[OfferBrowseRecord, ...] = ()
    location_exists: bool = True
    matching_count: int = 0
    total_count: int = 0
    viewport_records: tuple[ListingBrowseRecord, ...] = ()
    viewport_matching_count: int = 0

    async def query_facets(self) -> FacetSnapshot:
        """Return deterministic facet values."""
        return self.facets

    async def query_viewport_listings(
        self,
        *,
        filters: MapFilters,
        cursor: ListingCursor | None,
        limit: int,
    ) -> ViewportListingSnapshot:
        """Return deterministic listing records while satisfying the port."""
        del filters, cursor
        return ViewportListingSnapshot(
            records=self.viewport_records[:limit],
            matching_count=self.viewport_matching_count,
        )

    async def query_location_offers(
        self,
        *,
        location_id: object,
        filters: MapFilters,
        include_non_matching: bool,
        cursor: OfferCursor | None,
        limit: int,
    ) -> OfferBrowseSnapshot:
        """Return deterministic records while satisfying the port shape."""
        del location_id, filters, include_non_matching, cursor
        return OfferBrowseSnapshot(
            location_exists=self.location_exists,
            records=self.records[:limit],
            matching_count=self.matching_count,
            total_count=self.total_count,
        )


@dataclass(frozen=True, slots=True)
class FakeOfferDetailQuery:
    """In-memory offer detail query adapter."""

    record: OfferDetailRecord | None = None

    async def query_offer_detail(self, offer_id: object) -> OfferDetailRecord | None:
        """Return one deterministic offer detail record."""
        del offer_id
        return self.record


def empty_facet_snapshot() -> FacetSnapshot:
    """Return an empty valid facet response for app-state tests."""
    return FacetSnapshot(
        districts=(),
        rooms=(),
        market_types=(),
        content_types=(),
        price_min_minor=None,
        price_max_minor=None,
        area_min_sqm=None,
        area_max_sqm=None,
        published_from=None,
        published_to=None,
    )


async def always_ready() -> bool:
    """Return a healthy readiness result."""
    return True


async def never_ready() -> bool:
    """Return an unhealthy readiness result."""
    return False


async def close_nothing() -> None:
    """Satisfy resource cleanup without external resources."""
    return


@dataclass
class FakeIdentityStore:
    """In-memory identity persistence with scripted state."""

    accounts: dict[str, Account] = field(default_factory=dict)
    sessions: dict[str, AccountSession] = field(default_factory=dict)

    async def owner_exists(self) -> bool:
        """Report whether any undeleted owner exists."""
        return any(
            a.role == UserRole.OWNER and a.deleted_at is None for a in self.accounts.values()
        )

    async def username_exists(self, username_normalized: str) -> bool:
        """Report whether the normalized username is taken."""
        return username_normalized in self.accounts

    async def create_account(
        self,
        *,
        username_normalized: str,
        username_display: str,
        hashed_password: str,
        role: UserRole,
        must_change_password: bool,
    ) -> Account:
        """Insert one in-memory account."""
        now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
        account = Account(
            id=uuid4(),
            username_normalized=username_normalized,
            username_display=username_display,
            hashed_password=hashed_password,
            role=role,
            is_active=True,
            must_change_password=must_change_password,
            created_at=now,
            updated_at=now,
            last_login_at=None,
            disabled_at=None,
            deleted_at=None,
        )
        self.accounts[username_normalized] = account
        return account

    async def find_account_by_username(self, username_normalized: str) -> Account | None:
        """Return the in-memory account for the normalized username."""
        return self.accounts.get(username_normalized)

    async def find_account_by_id(self, account_id: UUID) -> Account | None:
        """Return the in-memory account with the identifier."""
        return next(
            (a for a in self.accounts.values() if a.id == account_id),
            None,
        )

    async def list_accounts(self, *, limit: int = 100) -> tuple[Account, ...]:
        """Return recent non-deleted in-memory accounts."""
        accounts = [a for a in self.accounts.values() if a.deleted_at is None]
        accounts.sort(key=lambda item: item.created_at, reverse=True)
        return tuple(accounts[:limit])

    async def count_active_owners(self) -> int:
        """Count active non-deleted owners in memory."""
        return sum(
            1
            for account in self.accounts.values()
            if account.role is UserRole.OWNER and account.is_active and account.deleted_at is None
        )

    async def update_account(self, account: Account) -> None:
        """Persist mutable fields in memory."""
        self.accounts[account.username_normalized] = account

    async def create_session(
        self,
        *,
        account_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """Insert one in-memory session record."""
        self.sessions[token_hash] = AccountSession(
            id=uuid4(),
            account_id=account_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
            created_at=datetime(2026, 8, 14, 12, 0, tzinfo=UTC),
            last_used_at=None,
        )

    async def find_session_by_token_hash(self, token_hash: str) -> AccountSession | None:
        """Return the in-memory session for the token hash."""
        return self.sessions.get(token_hash)

    async def revoke_session(self, session_id: UUID) -> None:
        """Revoke one in-memory session."""
        for token_hash, session in self.sessions.items():
            if session.id == session_id:
                self.sessions[token_hash] = replace(
                    session,
                    revoked_at=datetime(2026, 8, 14, 12, 5, tzinfo=UTC),
                )

    async def revoke_all_sessions(self, account_id: UUID) -> int:
        """Revoke every live in-memory session of the account."""
        count = 0
        for token_hash, session in self.sessions.items():
            if session.account_id == account_id and session.revoked_at is None:
                self.sessions[token_hash] = replace(
                    session,
                    revoked_at=datetime(2026, 8, 14, 12, 5, tzinfo=UTC),
                )
                count += 1
        return count


@dataclass
class FakeHasher:
    """Deterministic reversible hasher for fast tests."""

    def hash(self, password: str) -> str:
        """Return a deterministic fake hash."""
        return f"fakehash:{password}"

    def verify(self, password: str, hashed: str) -> bool:
        """Compare against the deterministic fake hash."""
        return hashed == f"fakehash:{password}"


@dataclass
class FakeTokens:
    """Deterministic sequential token issuer."""

    counter: int = 0

    def issue(self) -> tuple[str, str]:
        """Return the next sequential token pair."""
        self.counter += 1
        raw = f"raw-token-{self.counter}"
        return raw, self.hash(raw)

    def hash(self, raw_token: str) -> str:
        """Return a deterministic fake hash."""
        return f"hashed:{raw_token}"


@dataclass
class FakeClock:
    """Deterministic UTC clock with optional travel."""

    moment: datetime = field(
        default_factory=lambda: datetime(2026, 8, 14, 12, 0, tzinfo=UTC),
    )

    def now(self) -> datetime:
        """Return the current scripted moment."""
        return self.moment

    def advance(self, seconds: int) -> None:
        """Move the scripted moment forward."""
        self.moment = self.moment + timedelta(seconds=seconds)


@dataclass
class FakeRateLimiter:
    """Scripted rate limiter with an allowlist of blocked keys."""

    blocked: set[str] = field(default_factory=set)

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Allow every key except the scripted blocked set."""
        del limit, window_seconds
        return key not in self.blocked


def build_identity_service(
    *,
    store: FakeIdentityStore | None = None,
    hasher: FakeHasher | PasswordHasher | None = None,
    tokens: FakeTokens | None = None,
    clock: FakeClock | None = None,
    rate_limiter: FakeRateLimiter | None = None,
    session_ttl_seconds: int = 3600,
) -> IdentityService:
    """Compose one identity service fully backed by fakes."""
    store = store or FakeIdentityStore()
    hasher = hasher or FakeHasher()
    tokens = tokens or FakeTokens()
    clock = clock or FakeClock()
    return IdentityService(
        register=RegisterAccount(store, hasher),
        authenticate=AuthenticateAccount(
            store,
            hasher,
            tokens,
            clock,
            session_ttl_seconds=session_ttl_seconds,
        ),
        resolve_session=ResolveSession(store, tokens, clock),
        logout=LogoutSession(store, tokens),
        change_password=ChangeAccountPassword(store, hasher, clock),
        revoke_all_sessions=RevokeAllAccountSessions(store),
        disable_account=DisableOwnAccount(store, clock),
        delete_account=DeleteOwnAccount(store, clock),
        rate_limiter=rate_limiter or FakeRateLimiter(),
    )


@dataclass
class FakeFavoriteStore:
    """In-memory favorite store for HTTP tests."""

    items: dict[tuple[UUID, UUID], FavoriteLocationView] = field(default_factory=dict)
    public_locations: set[UUID] = field(default_factory=set)

    async def list_favorites(self, user_id: UUID) -> tuple[FavoriteLocationView, ...]:
        """Return favorites newest-first for one account."""
        return tuple(
            item
            for (owner, _), item in sorted(
                self.items.items(),
                key=lambda entry: entry[1].created_at,
                reverse=True,
            )
            if owner == user_id
        )

    async def add_favorite(self, user_id: UUID, location_id: UUID) -> bool:
        """Star one public location when present in the fake catalog."""
        if location_id not in self.public_locations:
            return False
        key = (user_id, location_id)
        if key not in self.items:
            self.items[key] = FavoriteLocationView(
                location_id=location_id,
                display_name="Sample",
                display_address="Sample address",
                district="wola",
                created_at="2026-08-19T12:00:00+00:00",
            )
        return True

    async def remove_favorite(self, user_id: UUID, location_id: UUID) -> None:
        """Remove one starred location idempotently."""
        self.items.pop((user_id, location_id), None)


def build_favorites_service(
    store: FakeFavoriteStore | None = None,
) -> FavoriteService:
    """Compose one favorites service fully backed by fakes."""
    favorite_store = store or FakeFavoriteStore()
    return FavoriteService(
        list_favorites=ListFavoriteLocations(favorite_store),
        add_favorite=AddFavoriteLocation(favorite_store),
        remove_favorite=RemoveFavoriteLocation(favorite_store),
    )


@dataclass
class FakeViewHistoryStore:
    """In-memory account visit and viewed-offer history."""

    public_offers: set[UUID] = field(default_factory=set)
    visits: dict[tuple[UUID, UUID], AccountVisitView] = field(default_factory=dict)
    viewed_offers: dict[tuple[UUID, UUID], ViewedOfferView] = field(default_factory=dict)

    async def start_visit(
        self,
        *,
        user_id: UUID,
        visit_id: UUID,
        started_at: datetime,
    ) -> AccountVisitView:
        """Create one visit and keep its baseline stable on replay."""
        key = (user_id, visit_id)
        existing = self.visits.get(key)
        if existing is not None:
            return existing
        previous = max(
            (
                visit.current_visit_at
                for (owner, _), visit in self.visits.items()
                if owner == user_id
            ),
            default=None,
        )
        created = AccountVisitView(
            visit_id=visit_id,
            current_visit_at=started_at,
            previous_visit_at=previous,
        )
        self.visits[key] = created
        return created

    async def mark_offer_viewed(
        self,
        *,
        user_id: UUID,
        offer_id: UUID,
        viewed_at: datetime,
    ) -> ViewedOfferView | None:
        """Aggregate public-offer views for one account."""
        if offer_id not in self.public_offers:
            return None
        key = (user_id, offer_id)
        existing = self.viewed_offers.get(key)
        updated = ViewedOfferView(
            offer_id=offer_id,
            first_viewed_at=(existing.first_viewed_at if existing else viewed_at),
            last_viewed_at=viewed_at,
            view_count=(existing.view_count + 1 if existing else 1),
        )
        self.viewed_offers[key] = updated
        return updated

    async def list_viewed_offers(
        self,
        user_id: UUID,
    ) -> tuple[ViewedOfferView, ...]:
        """Return most-recent-first public offer views."""
        return tuple(
            view
            for (owner, _), view in sorted(
                self.viewed_offers.items(),
                key=lambda entry: entry[1].last_viewed_at,
                reverse=True,
            )
            if owner == user_id and view.offer_id in self.public_offers
        )


def build_view_history_service(
    store: FakeViewHistoryStore | None = None,
    clock: FakeClock | None = None,
) -> ViewHistoryService:
    """Compose account view history from deterministic fakes."""
    view_store = store or FakeViewHistoryStore()
    view_clock = clock or FakeClock()
    return ViewHistoryService(
        start_visit=StartAccountVisit(view_store, view_clock),
        mark_offer_viewed=MarkOfferViewed(view_store, view_clock),
        list_viewed_offers=ListViewedOffers(view_store),
    )


@dataclass
class FakeContactCipher:
    """Deterministic reversible stand-in for AES-GCM."""

    available: bool = True

    def encrypt(self, plaintext: str) -> str:
        """Prefix plaintext so tests can spot accidental leakage."""
        if not self.available:
            message = "contact encryption key is unavailable"
            raise ContactCryptoUnavailableError(message)
        return f"enc:{plaintext}"

    def decrypt(self, ciphertext: str) -> str:
        """Strip the fake prefix."""
        if not self.available or not ciphertext.startswith("enc:"):
            message = "contact ciphertext is invalid"
            raise ContactCryptoUnavailableError(message)
        return ciphertext.removeprefix("enc:")

    def fingerprint(self, *, kind: ContactKind, normalized_value: str) -> str:
        """Return a deterministic fake fingerprint."""
        if not self.available:
            message = "contact HMAC key is unavailable"
            raise ContactCryptoUnavailableError(message)
        return f"fp:{kind.value}:{normalized_value}"


@dataclass
class FakeContactStore:
    """In-memory contact points and reveal audits for HTTP tests."""

    contacts: dict[UUID, list[ContactPointRecord]] = field(default_factory=dict)
    visible_offers: set[UUID] = field(default_factory=set)
    audits: list[dict[str, object]] = field(default_factory=list)

    async def replace_offer_contacts(
        self,
        *,
        offer_id: UUID,
        source_message_id: UUID | None,
        contacts: tuple[ContactPointRecord, ...],
    ) -> None:
        """Replace contacts for one offer."""
        del source_message_id
        self.contacts[offer_id] = list(contacts)

    async def list_revealable_for_offer(
        self,
        offer_id: UUID,
    ) -> tuple[ContactPointRecord, ...]:
        """Return revealable contacts for one offer."""
        return tuple(item for item in self.contacts.get(offer_id, []) if item.is_revealable)

    async def offer_is_publicly_visible(self, offer_id: UUID) -> bool:
        """Report whether the offer is in the visible set."""
        return offer_id in self.visible_offers

    async def record_reveal(
        self,
        *,
        user_id: UUID,
        offer_id: UUID,
        source_message_id: UUID | None,
        request_id: UUID,
        outcome: RevealOutcome,
    ) -> None:
        """Append one minimized audit row."""
        self.audits.append(
            {
                "user_id": user_id,
                "offer_id": offer_id,
                "source_message_id": source_message_id,
                "request_id": request_id,
                "outcome": outcome.value,
            },
        )


def build_contact_service(
    *,
    store: FakeContactStore | None = None,
    cipher: ContactCipher | None = None,
    rate_limiter: FakeRateLimiter | None = None,
) -> ContactService:
    """Compose one contact service fully backed by fakes."""
    contact_store = store or FakeContactStore()
    contact_cipher: ContactCipher = cipher or FakeContactCipher()
    limiter = rate_limiter or FakeRateLimiter()
    return ContactService(
        persist=PersistOfferContacts(contact_store, contact_cipher),
        reveal=RevealOfferContacts(contact_store, contact_cipher, limiter),
        rate_limiter=limiter,
    )


@dataclass
class FakeAdminAuditStore:
    """In-memory admin audit store."""

    events: list[AdminAuditEvent] = field(default_factory=list)

    async def record(self, event: AdminAuditEvent) -> None:
        self.events.append(event)

    async def list_recent(self, *, limit: int = 100) -> tuple[AdminAuditEvent, ...]:
        return tuple(reversed(self.events[-limit:]))


@dataclass
class FakeRevealAuditReader:
    """In-memory reveal audit reader."""

    rows: list[RevealAuditSummary] = field(default_factory=list)

    async def list_recent(self, *, limit: int = 100) -> tuple[RevealAuditSummary, ...]:
        return tuple(self.rows[:limit])


@dataclass
class FakeLocationAdminStore:
    """In-memory location admin reader and decision store."""

    summaries: list[LocationAdminSummary] = field(default_factory=list)
    details: dict[UUID, LocationEditDetail] = field(default_factory=dict)
    denied_actions: set[str] = field(default_factory=set)
    applied: list[str] = field(default_factory=list)

    async def list_locations(
        self,
        *,
        status: LocationStatusFilter,
        search: str | None,
        limit: int = 100,
    ) -> tuple[LocationAdminSummary, ...]:
        """Filter summaries by review-status slice and casefolded substring."""
        rows = list(self.summaries)
        if status is LocationStatusFilter.PENDING:
            rows = [
                summary
                for summary in rows
                if summary.review_status in ("needs_review", "ungeocoded")
            ]
        elif status is not LocationStatusFilter.ALL:
            rows = [summary for summary in rows if summary.review_status == status.value]
        if search is not None:
            needle = search.casefold()
            rows = [
                summary
                for summary in rows
                if needle in summary.display_address.casefold()
                or needle in summary.display_name.casefold()
            ]
        return tuple(rows[:limit])

    async def get_edit_detail(self, location_id: UUID) -> LocationEditDetail | None:
        """Return the scripted detail, or None when unknown."""
        return self.details.get(location_id)

    async def apply_accept_candidate(
        self,
        *,
        location_id: UUID,  # noqa: ARG002 - contract parity
        actor_id: str,  # noqa: ARG002 - contract parity
        decided_at: datetime,  # noqa: ARG002 - contract parity
    ) -> bool:
        """Record the decision unless the action is scripted to fail."""
        self.applied.append("accept")
        return "accept" not in self.denied_actions

    async def apply_reject(
        self,
        *,
        location_id: UUID,  # noqa: ARG002 - contract parity
        actor_id: str,  # noqa: ARG002 - contract parity
        decided_at: datetime,  # noqa: ARG002 - contract parity
    ) -> bool:
        """Record the decision unless the action is scripted to fail."""
        self.applied.append("reject")
        return "reject" not in self.denied_actions

    async def apply_unresolve(
        self,
        *,
        location_id: UUID,  # noqa: ARG002 - contract parity
        actor_id: str,  # noqa: ARG002 - contract parity
        decided_at: datetime,  # noqa: ARG002 - contract parity
    ) -> bool:
        """Record the decision unless the action is scripted to fail."""
        self.applied.append("unresolve")
        return "unresolve" not in self.denied_actions

    async def apply_set_point(
        self,
        *,
        location_id: UUID,  # noqa: ARG002 - contract parity
        longitude: Decimal,  # noqa: ARG002 - contract parity
        latitude: Decimal,  # noqa: ARG002 - contract parity
        actor_id: str,  # noqa: ARG002 - contract parity
        decided_at: datetime,  # noqa: ARG002 - contract parity
    ) -> bool:
        """Record the decision unless the action is scripted to fail."""
        self.applied.append("set_point")
        return "set_point" not in self.denied_actions


def build_admin_service(
    *,
    store: FakeIdentityStore | None = None,
    audits: FakeAdminAuditStore | None = None,
    reveals: FakeRevealAuditReader | None = None,
    places: FakeLocationAdminStore | None = None,
    hasher: FakeHasher | None = None,
    clock: FakeClock | None = None,
) -> AdminService:
    """Compose one admin service fully backed by fakes."""
    identity_store = store or FakeIdentityStore()
    audit_store = audits or FakeAdminAuditStore()
    reveal_reader = reveals or FakeRevealAuditReader()
    location_store = places or FakeLocationAdminStore()
    password_hasher = hasher or FakeHasher()
    time_source = clock or FakeClock()
    return AdminService(
        list_accounts=ListAdminAccounts(identity_store),
        disable_user=DisableUser(identity_store, audit_store, time_source),
        reactivate_user=ReactivateUser(identity_store, audit_store, time_source),
        revoke_user_sessions=RevokeUserSessions(identity_store, audit_store),
        force_reset_password=ForceResetUserPassword(
            identity_store,
            audit_store,
            password_hasher,
            time_source,
        ),
        list_reveal_audits=ListRevealAudits(reveal_reader),
        list_admin_audits=ListAdminAudits(audit_store),
        list_locations=ListLocations(location_store),
        get_location_for_edit=GetLocationForEdit(location_store),
        accept_place_candidate=AcceptPlaceCandidate(location_store, audit_store, time_source),
        reject_place=RejectPlace(location_store, audit_store, time_source),
        unresolve_place=UnresolvePlace(location_store, audit_store, time_source),
        set_place_point=SetPlacePoint(location_store, audit_store, time_source),
    )


def account_view_of(account: Account) -> AccountView:
    """Project one account for assertions."""
    return AccountView(
        id=account.id,
        username=account.username_display,
        role=account.role,
        must_change_password=account.must_change_password,
        created_at=account.created_at,
        last_login_at=account.last_login_at,
    )
