"""Identity use cases owned by the application layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from wef_backend.features.identity.domain.model import (
    Account,
    AccountSession,
    PasswordPolicyError,
    UserRole,
    normalize_username,
    validate_password,
)

_REGISTRATION_DECLINED = "registration declined"
_USERNAME_UNAVAILABLE = "username unavailable"
_INVALID_CREDENTIALS = "invalid credentials"
_NEW_CREDENTIAL_INVALID = "password is invalid"
_MAX_RAW_TOKEN_LENGTH = 128


class RegistrationDeclinedError(ValueError):
    """Raised when a registration request cannot create an account."""


class InvalidCredentialsError(ValueError):
    """The single indistinguishable authentication failure."""


class BootstrapOwnerError(RuntimeError):
    """Raised when the one-time owner bootstrap cannot proceed."""


class PasswordHasher(Protocol):
    """Password hashing contract with verified-parameter Argon2."""

    def hash(self, password: str) -> str:
        """Return one Argon2 hash for an accepted password."""
        ...

    def verify(self, password: str, hashed: str) -> bool:
        """Verify a password against a stored hash."""
        ...


class TokenService(Protocol):
    """Opaque session token issuance contract."""

    def issue(self) -> tuple[str, str]:
        """Return a raw token and the persistable hash of that token."""
        ...

    def hash(self, raw_token: str) -> str:
        """Return the persistable hash for one raw token."""
        ...


class Clock(Protocol):
    """Application-owned time source."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC time."""
        ...


class IdentityStore(Protocol):
    """Persistence contract for accounts and opaque sessions."""

    async def owner_exists(self) -> bool:
        """Report whether any owner account exists."""
        ...

    async def username_exists(self, username_normalized: str) -> bool:
        """Report whether the normalized username is already taken."""
        ...

    async def create_account(
        self,
        *,
        username_normalized: str,
        username_display: str,
        hashed_password: str,
        role: UserRole,
        must_change_password: bool,
    ) -> Account:
        """Persist and return one new account."""
        ...

    async def find_account_by_username(self, username_normalized: str) -> Account | None:
        """Return the account owning the normalized username."""
        ...

    async def find_account_by_id(self, account_id: UUID) -> Account | None:
        """Return the account with the given identifier."""
        ...

    async def list_accounts(self, *, limit: int = 100) -> tuple[Account, ...]:
        """Return recent non-deleted accounts for owner administration."""
        ...

    async def count_active_owners(self) -> int:
        """Count active, non-deleted owner accounts."""
        ...

    async def update_account(self, account: Account) -> None:
        """Persist mutable account fields including password state."""
        ...

    async def create_session(
        self,
        *,
        account_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """Persist one opaque session token hash."""
        ...

    async def find_session_by_token_hash(self, token_hash: str) -> AccountSession | None:
        """Return the session owning the token hash."""
        ...

    async def revoke_session(self, session_id: UUID) -> None:
        """Revoke exactly one session."""
        ...

    async def revoke_all_sessions(self, account_id: UUID) -> int:
        """Revoke every live session of one account and return the count."""
        ...


class RateLimiter(Protocol):
    """Bounded fixed-window abuse throttle."""

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Consume one allowance for the key inside the window."""
        ...


@dataclass(frozen=True, slots=True)
class AccountView:
    """Minimal public projection of one account."""

    id: UUID
    username: str
    role: UserRole
    must_change_password: bool
    created_at: datetime
    last_login_at: datetime | None


@dataclass(frozen=True, slots=True)
class LoginResult:
    """One successful authentication and its fresh opaque session."""

    account: AccountView
    raw_token: str
    expires_at: datetime
    ttl_seconds: int


def _view(account: Account) -> AccountView:
    """Project one account without hash or status internals."""
    return AccountView(
        id=account.id,
        username=account.username_display,
        role=account.role,
        must_change_password=account.must_change_password,
        created_at=account.created_at,
        last_login_at=account.last_login_at,
    )


class RegisterAccount:
    """Create one pseudonymous account with a unique normalized username."""

    def __init__(self, store: IdentityStore, hasher: PasswordHasher) -> None:
        """Store the identity persistence and hashing ports."""
        self._store = store
        self._hasher = hasher

    async def __call__(self, *, username: str, password: str) -> AccountView:
        """Validate, hash, and persist one new user-role account."""
        try:
            normalized = normalize_username(username)
            validate_password(password)
        except ValueError as error:
            msg = "registration declined"
            raise RegistrationDeclinedError(msg) from error
        if await self._store.username_exists(normalized):
            msg = "username unavailable"
            raise RegistrationDeclinedError(msg)
        account = await self._store.create_account(
            username_normalized=normalized,
            username_display=username.strip(),
            hashed_password=self._hasher.hash(password),
            role=UserRole.USER,
            must_change_password=False,
        )
        return _view(account)


class AuthenticateAccount:
    """Verify credentials and establish one opaque server-side session."""

    _DUMMY_HASH = (
        "$argon2id$v=19$m=65536,t=3,p=4$qv+YgvjgTXd7vil/ikP8gQ$"
        "/f7RRZlRURT9YrzXF+ud4Q8HYD5JTsIK21HNahcyzmY"
    )
    """Full valid Argon2 hash of a constant dummy secret used to equalize
    unknown-username timing. It must stay verifiable by the configured
    hasher; the dummy verification is additionally failure-proofed below
    so any hasher refusal degrades to the single indistinguishable
    failure instead of an error response."""

    def __init__(
        self,
        store: IdentityStore,
        hasher: PasswordHasher,
        tokens: TokenService,
        clock: Clock,
        session_ttl_seconds: int,
    ) -> None:
        """Store identity ports and the explicit session lifetime."""
        self._store = store
        self._hasher = hasher
        self._tokens = tokens
        self._clock = clock
        self._session_ttl = timedelta(seconds=session_ttl_seconds)

    async def __call__(self, *, username: str, password: str) -> LoginResult:
        """Return one fresh session or the single indistinguishable failure."""
        try:
            normalized = normalize_username(username)
            validate_password(password)
        except ValueError as error:
            msg = "invalid credentials"
            raise InvalidCredentialsError(msg) from error
        account = await self._store.find_account_by_username(normalized)
        if account is None:
            _equalize_timing(self._hasher, password, self._DUMMY_HASH)
            msg = "invalid credentials"
            raise InvalidCredentialsError(msg)
        if not _verify_tolerant(self._hasher, password, account.hashed_password):
            msg = "invalid credentials"
            raise InvalidCredentialsError(msg)
        if not account.is_active or account.deleted_at is not None:
            msg = "invalid credentials"
            raise InvalidCredentialsError(msg)
        now = self._clock.now()
        logged_in = _replace_login(account, now)
        await self._store.update_account(logged_in)
        raw_token, token_hash = self._tokens.issue()
        expires_at = now + self._session_ttl
        await self._store.create_session(
            account_id=account.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        return LoginResult(
            account=_view(logged_in),
            raw_token=raw_token,
            expires_at=expires_at,
            ttl_seconds=int(self._session_ttl.total_seconds()),
        )


def _equalize_timing(hasher: PasswordHasher, password: str, hashed: str) -> None:
    """Run one hash verification for unknown usernames, failing closed.

    Any hasher refusal degrades to the single indistinguishable failure
    instead of surfacing as an error response.
    """
    try:
        hasher.verify(password, hashed)
    except Exception:  # noqa: BLE001 - hasher refusals stay indistinguishable
        return


def _verify_tolerant(hasher: PasswordHasher, password: str, hashed: str) -> bool:
    """Verify one password, treating hasher refusals as a failed match."""
    try:
        return hasher.verify(password, hashed)
    except Exception:  # noqa: BLE001 - corrupt or unknown hashes are failed matches
        return False


def _replace_login(account: Account, last_login_at: datetime) -> Account:
    """Copy one account with a new last-login timestamp."""
    return Account(
        id=account.id,
        username_normalized=account.username_normalized,
        username_display=account.username_display,
        hashed_password=account.hashed_password,
        role=account.role,
        is_active=account.is_active,
        must_change_password=account.must_change_password,
        created_at=account.created_at,
        updated_at=last_login_at,
        last_login_at=last_login_at,
        disabled_at=account.disabled_at,
        deleted_at=account.deleted_at,
    )


class ResolveSession:
    """Resolve one raw token to its active account view."""

    def __init__(self, store: IdentityStore, tokens: TokenService, clock: Clock) -> None:
        """Store identity ports."""
        self._store = store
        self._tokens = tokens
        self._clock = clock

    async def __call__(self, raw_token: str) -> AccountView | None:
        """Return the account view or None for unknown/expired sessions."""
        if not raw_token or len(raw_token) > _MAX_RAW_TOKEN_LENGTH:
            return None
        session = await self._store.find_session_by_token_hash(
            self._tokens.hash(raw_token),
        )
        if session is None or session.revoked_at is not None:
            return None
        if session.expires_at <= self._clock.now():
            return None
        account = await self._store.find_account_by_id(session.account_id)
        if account is None or not account.is_active or account.deleted_at is not None:
            return None
        return _view(account)


class LogoutSession:
    """Revoke the session behind one raw token."""

    def __init__(self, store: IdentityStore, tokens: TokenService) -> None:
        """Store identity ports."""
        self._store = store
        self._tokens = tokens

    async def __call__(self, raw_token: str) -> None:
        """Revoke the session if it exists; unknown tokens are accepted."""
        if not raw_token:
            return
        session = await self._store.find_session_by_token_hash(
            self._tokens.hash(raw_token),
        )
        if session is not None:
            await self._store.revoke_session(session.id)


class ChangeAccountPassword:
    """Change the password after verifying the current one."""

    def __init__(self, store: IdentityStore, hasher: PasswordHasher, clock: Clock) -> None:
        """Store identity ports."""
        self._store = store
        self._hasher = hasher
        self._clock = clock

    async def __call__(
        self,
        *,
        account_id: UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        """Verify, rehash, clear forced-change state, revoke all sessions."""
        account = await self._store.find_account_by_id(account_id)
        if account is None or account.deleted_at is not None:
            msg = "invalid credentials"
            raise InvalidCredentialsError(msg)
        if not self._hasher.verify(current_password, account.hashed_password):
            msg = "invalid credentials"
            raise InvalidCredentialsError(msg)
        try:
            validate_password(new_password)
        except ValueError as error:
            msg = "password is invalid"
            raise PasswordPolicyError(msg) from error
        now = self._clock.now()
        await self._store.update_account(
            Account(
                id=account.id,
                username_normalized=account.username_normalized,
                username_display=account.username_display,
                hashed_password=self._hasher.hash(new_password),
                role=account.role,
                is_active=account.is_active,
                must_change_password=False,
                created_at=account.created_at,
                updated_at=now,
                last_login_at=account.last_login_at,
                disabled_at=account.disabled_at,
                deleted_at=account.deleted_at,
            ),
        )
        await self._store.revoke_all_sessions(account_id)


class RevokeAllAccountSessions:
    """Revoke every live session of one account."""

    def __init__(self, store: IdentityStore) -> None:
        """Store the identity persistence port."""
        self._store = store

    async def __call__(self, account_id: UUID) -> None:
        """Revoke all sessions of the account."""
        await self._store.revoke_all_sessions(account_id)


class DisableOwnAccount:
    """Disable the authenticated account and revoke its sessions."""

    def __init__(self, store: IdentityStore, clock: Clock) -> None:
        """Store identity ports."""
        self._store = store
        self._clock = clock

    async def __call__(self, account_id: UUID) -> None:
        """Mark the account inactive and revoke every session."""
        account = await self._store.find_account_by_id(account_id)
        if account is None or account.deleted_at is not None:
            msg = "invalid credentials"
            raise InvalidCredentialsError(msg)
        now = self._clock.now()
        await self._store.update_account(
            Account(
                id=account.id,
                username_normalized=account.username_normalized,
                username_display=account.username_display,
                hashed_password=account.hashed_password,
                role=account.role,
                is_active=False,
                must_change_password=account.must_change_password,
                created_at=account.created_at,
                updated_at=now,
                last_login_at=account.last_login_at,
                disabled_at=now,
                deleted_at=account.deleted_at,
            ),
        )
        await self._store.revoke_all_sessions(account_id)


class DeleteOwnAccount:
    """Soft-delete the authenticated account and revoke its sessions."""

    def __init__(self, store: IdentityStore, clock: Clock) -> None:
        """Store identity ports."""
        self._store = store
        self._clock = clock

    async def __call__(self, account_id: UUID) -> None:
        """Mark the account deleted while reserving its username."""
        account = await self._store.find_account_by_id(account_id)
        if account is None:
            msg = "invalid credentials"
            raise InvalidCredentialsError(msg)
        now = self._clock.now()
        await self._store.update_account(
            Account(
                id=account.id,
                username_normalized=account.username_normalized,
                username_display=account.username_display,
                hashed_password=account.hashed_password,
                role=account.role,
                is_active=False,
                must_change_password=account.must_change_password,
                created_at=account.created_at,
                updated_at=now,
                last_login_at=account.last_login_at,
                disabled_at=account.disabled_at,
                deleted_at=now,
            ),
        )
        await self._store.revoke_all_sessions(account_id)


class BootstrapOwner:
    """Create the fixed owner account exactly once from operator secrets."""

    def __init__(
        self,
        store: IdentityStore,
        hasher: PasswordHasher,
        *,
        username: str | None,
        password: str | None,
    ) -> None:
        """Store identity ports and operator-supplied bootstrap secrets."""
        self._store = store
        self._hasher = hasher
        self._username = username
        self._password = password

    async def __call__(self) -> AccountView:
        """Create the owner or fail when one already exists."""
        if await self._store.owner_exists():
            msg = "owner already exists"
            raise BootstrapOwnerError(msg)
        if self._username is None or self._password is None:
            msg = "bootstrap credentials were not provided"
            raise BootstrapOwnerError(msg)
        try:
            normalized = normalize_username(self._username)
            validate_password(self._password)
        except ValueError as error:
            msg = "bootstrap credentials are invalid"
            raise BootstrapOwnerError(msg) from error
        if await self._store.username_exists(normalized):
            msg = "username unavailable"
            raise BootstrapOwnerError(msg)
        account = await self._store.create_account(
            username_normalized=normalized,
            username_display=self._username.strip(),
            hashed_password=self._hasher.hash(self._password),
            role=UserRole.OWNER,
            must_change_password=True,
        )
        return _view(account)


@dataclass(frozen=True, slots=True)
class IdentityService:
    """Bundle of identity interactors placed on application state."""

    register: RegisterAccount
    authenticate: AuthenticateAccount
    resolve_session: ResolveSession
    logout: LogoutSession
    change_password: ChangeAccountPassword
    revoke_all_sessions: RevokeAllAccountSessions
    disable_account: DisableOwnAccount
    delete_account: DeleteOwnAccount
    rate_limiter: RateLimiter


def new_account_id() -> UUID:
    """Return the identifier generator used for persisted accounts."""
    return uuid4()


def utc_now() -> datetime:
    """Return timezone-aware UTC now for command-line composition."""
    return datetime.now(UTC)
