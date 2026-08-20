"""Contact application use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from wef_backend.features.contacts.domain.model import (
    ContactKind,
    ContactPointRecord,
    RevealedContact,
    RevealOutcome,
    mask_contact_value,
    normalize_contact_value,
)

CONTACT_SET_VERSION = "v1"
REVEAL_RATE_LIMIT = 10
REVEAL_RATE_WINDOW_SECONDS = 600


class ContactCryptoUnavailableError(RuntimeError):
    """Raised when encryption keys are missing or decrypt fails closed."""


class ContactCipher(Protocol):
    """Authenticated encryption and keyed fingerprinting for contacts."""

    @property
    def available(self) -> bool:
        """Report whether encrypt/decrypt can proceed."""
        ...

    def encrypt(self, plaintext: str) -> str:
        """Return a persistable ciphertext encoding."""
        ...

    def decrypt(self, ciphertext: str) -> str:
        """Return plaintext or raise when unavailable/invalid."""
        ...

    def fingerprint(self, *, kind: ContactKind, normalized_value: str) -> str:
        """Return a keyed HMAC fingerprint without storing plaintext."""
        ...


class ContactStore(Protocol):
    """Persistence for encrypted contacts and reveal audits."""

    async def replace_offer_contacts(
        self,
        *,
        offer_id: UUID,
        source_message_id: UUID | None,
        contacts: tuple[ContactPointRecord, ...],
    ) -> None:
        """Replace all contact points for one offer."""
        ...

    async def list_revealable_for_offer(
        self,
        offer_id: UUID,
    ) -> tuple[ContactPointRecord, ...]:
        """Return revealable contacts for one offer."""
        ...

    async def offer_is_publicly_visible(self, offer_id: UUID) -> bool:
        """Report whether the offer is visible to anonymous clients."""
        ...

    async def record_reveal(
        self,
        *,
        user_id: UUID,
        offer_id: UUID,
        source_message_id: UUID | None,
        request_id: UUID,
        outcome: RevealOutcome,
    ) -> None:
        """Persist one minimized reveal audit row."""
        ...


class RateLimiter(Protocol):
    """Bounded fixed-window throttle."""

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Consume one allowance for the key inside the window."""
        ...


@dataclass(frozen=True, slots=True)
class ContactInput:
    """One extracted contact before encryption."""

    kind: ContactKind
    value: str


@dataclass(frozen=True, slots=True)
class RevealResult:
    """Authorized reveal payload or a refused outcome."""

    outcome: RevealOutcome
    contacts: tuple[RevealedContact, ...] = ()
    not_found: bool = False


def build_contact_records(
    cipher: ContactCipher,
    *,
    offer_id: UUID,
    source_message_id: UUID | None,
    contacts: tuple[ContactInput, ...],
) -> tuple[ContactPointRecord, ...]:
    """Encrypt and mask contacts for persistence."""
    if not contacts:
        return ()
    if not cipher.available:
        message = "contact encryption keys are unavailable"
        raise ContactCryptoUnavailableError(message)
    records: list[ContactPointRecord] = []
    seen: set[str] = set()
    for item in contacts:
        normalized = normalize_contact_value(item.kind, item.value)
        fingerprint = cipher.fingerprint(kind=item.kind, normalized_value=normalized)
        dedupe_key = f"{item.kind.value}:{fingerprint}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        records.append(
            ContactPointRecord(
                id=uuid4(),
                offer_id=offer_id,
                source_message_id=source_message_id,
                kind=item.kind,
                value_ciphertext=cipher.encrypt(item.value.strip()),
                masked_value=mask_contact_value(item.kind, item.value),
                fingerprint_hmac=fingerprint,
                is_revealable=True,
            ),
        )
    return tuple(records)


class PersistOfferContacts:
    """Replace encrypted contact points for one offer."""

    def __init__(self, store: ContactStore, cipher: ContactCipher) -> None:
        """Store persistence and crypto ports."""
        self._store = store
        self._cipher = cipher

    async def __call__(
        self,
        *,
        offer_id: UUID,
        source_message_id: UUID | None,
        contacts: tuple[ContactInput, ...],
    ) -> None:
        """Encrypt then replace contacts; no-op when the offer has none."""
        if not contacts:
            await self._store.replace_offer_contacts(
                offer_id=offer_id,
                source_message_id=source_message_id,
                contacts=(),
            )
            return
        records = build_contact_records(
            self._cipher,
            offer_id=offer_id,
            source_message_id=source_message_id,
            contacts=contacts,
        )
        await self._store.replace_offer_contacts(
            offer_id=offer_id,
            source_message_id=source_message_id,
            contacts=records,
        )


class RevealOfferContacts:
    """Authorize, rate-limit, decrypt, and audit one contact reveal."""

    def __init__(
        self,
        store: ContactStore,
        cipher: ContactCipher,
        rate_limiter: RateLimiter,
    ) -> None:
        """Store ports used by the reveal interactor."""
        self._store = store
        self._cipher = cipher
        self._rate_limiter = rate_limiter

    async def __call__(
        self,
        *,
        user_id: UUID,
        offer_id: UUID,
        request_id: UUID,
        must_change_password: bool,
    ) -> RevealResult:
        """Reveal contacts for a visible offer or return a refused outcome."""
        if must_change_password:
            await self._store.record_reveal(
                user_id=user_id,
                offer_id=offer_id,
                source_message_id=None,
                request_id=request_id,
                outcome=RevealOutcome.FORBIDDEN,
            )
            return RevealResult(outcome=RevealOutcome.FORBIDDEN)

        rate_key = f"reveal:{user_id}"
        if not self._rate_limiter.allow(
            rate_key,
            limit=REVEAL_RATE_LIMIT,
            window_seconds=REVEAL_RATE_WINDOW_SECONDS,
        ):
            await self._store.record_reveal(
                user_id=user_id,
                offer_id=offer_id,
                source_message_id=None,
                request_id=request_id,
                outcome=RevealOutcome.RATE_LIMITED,
            )
            return RevealResult(outcome=RevealOutcome.RATE_LIMITED)

        if not await self._store.offer_is_publicly_visible(offer_id):
            await self._store.record_reveal(
                user_id=user_id,
                offer_id=offer_id,
                source_message_id=None,
                request_id=request_id,
                outcome=RevealOutcome.FORBIDDEN,
            )
            return RevealResult(outcome=RevealOutcome.FORBIDDEN, not_found=True)

        if not self._cipher.available:
            await self._store.record_reveal(
                user_id=user_id,
                offer_id=offer_id,
                source_message_id=None,
                request_id=request_id,
                outcome=RevealOutcome.UNAVAILABLE,
            )
            return RevealResult(outcome=RevealOutcome.UNAVAILABLE)

        rows = await self._store.list_revealable_for_offer(offer_id)
        revealed: list[RevealedContact] = []
        source_message_id: UUID | None = None
        try:
            for row in rows:
                source_message_id = source_message_id or row.source_message_id
                plaintext = self._cipher.decrypt(row.value_ciphertext)
                revealed.append(
                    RevealedContact(
                        kind=row.kind,
                        value=plaintext,
                        masked_value=row.masked_value,
                    ),
                )
        except ContactCryptoUnavailableError:
            await self._store.record_reveal(
                user_id=user_id,
                offer_id=offer_id,
                source_message_id=source_message_id,
                request_id=request_id,
                outcome=RevealOutcome.UNAVAILABLE,
            )
            return RevealResult(outcome=RevealOutcome.UNAVAILABLE)

        await self._store.record_reveal(
            user_id=user_id,
            offer_id=offer_id,
            source_message_id=source_message_id,
            request_id=request_id,
            outcome=RevealOutcome.ALLOWED,
        )
        return RevealResult(
            outcome=RevealOutcome.ALLOWED,
            contacts=tuple(revealed),
        )


@dataclass(frozen=True, slots=True)
class ContactService:
    """Composition-root bundle for contact persistence and reveal."""

    persist: PersistOfferContacts
    reveal: RevealOfferContacts
    rate_limiter: RateLimiter
