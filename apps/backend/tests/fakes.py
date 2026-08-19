"""Small explicit test doubles for application and app-state boundaries."""

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from wef_backend.features.catalog.application import (
    FacetSnapshot,
    MapFilters,
    MapLocationRecord,
    MapQuerySnapshot,
    OfferBrowseRecord,
    OfferBrowseSnapshot,
    OfferCursor,
    OfferDetailRecord,
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
    RegisterAccount,
    ResolveSession,
    RevokeAllAccountSessions,
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
    """In-memory facets and selected-location query adapter."""

    facets: FacetSnapshot
    records: tuple[OfferBrowseRecord, ...] = ()
    location_exists: bool = True
    matching_count: int = 0
    total_count: int = 0

    async def query_facets(self) -> FacetSnapshot:
        """Return deterministic facet values."""
        return self.facets

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
    hasher: FakeHasher | None = None,
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
