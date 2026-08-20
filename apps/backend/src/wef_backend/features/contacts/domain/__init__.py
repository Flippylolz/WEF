"""Contact domain exports."""

from wef_backend.features.contacts.domain.model import (
    ContactKind,
    ContactPointRecord,
    RevealedContact,
    RevealOutcome,
    mask_contact_value,
    normalize_contact_value,
)

__all__ = [
    "ContactKind",
    "ContactPointRecord",
    "RevealOutcome",
    "RevealedContact",
    "mask_contact_value",
    "normalize_contact_value",
]
