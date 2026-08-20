"""Contact domain value objects and masking rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final
from uuid import UUID  # noqa: TC003

_TELEGRAM_VISIBLE_PREFIX: Final = 2
_PHONE_MIN_DIGITS: Final = 4


class ContactKind(StrEnum):
    """Persisted contact kinds matching the public data model."""

    PHONE = "phone"
    TELEGRAM = "telegram"


class RevealOutcome(StrEnum):
    """Minimized audit outcomes for contact reveal attempts."""

    ALLOWED = "allowed"
    RATE_LIMITED = "rate_limited"
    FORBIDDEN = "forbidden"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ContactPointRecord:
    """One encrypted contact attached to a visible offer."""

    id: UUID
    offer_id: UUID
    source_message_id: UUID | None
    kind: ContactKind
    value_ciphertext: str
    masked_value: str
    fingerprint_hmac: str
    is_revealable: bool


@dataclass(frozen=True, slots=True)
class RevealedContact:
    """Plaintext contact returned only after authorization."""

    kind: ContactKind
    value: str
    masked_value: str


def mask_contact_value(kind: ContactKind, value: str) -> str:
    """Return a safe anonymous rendering for one contact value."""
    cleaned = value.strip()
    if not cleaned:
        return "••••"
    if kind is ContactKind.TELEGRAM:
        handle = cleaned if cleaned.startswith("@") else f"@{cleaned}"
        body = handle[1:]
        if len(body) <= _TELEGRAM_VISIBLE_PREFIX:
            return "@••••"
        return f"@{body[:_TELEGRAM_VISIBLE_PREFIX]}••••••"
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    if len(digits) < _PHONE_MIN_DIGITS:
        return "••••"
    prefix = "+48 " if cleaned.startswith("+") or digits.startswith("48") else ""
    return f"{prefix}••• ••• {digits[-2:]}"


def normalize_contact_value(kind: ContactKind, value: str) -> str:
    """Normalize a contact for fingerprinting without changing display ciphertext."""
    cleaned = " ".join(value.strip().split())
    if kind is ContactKind.TELEGRAM:
        handle = cleaned.lstrip("@").casefold()
        return f"@{handle}"
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    if cleaned.startswith("+") and digits:
        return f"+{digits}"
    return digits or cleaned.casefold()
