"""Bounded, versioned address evidence without provider-specific policy."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

ADDRESS_EVIDENCE_VERSION = "address-evidence-v1"
_PREFIX = re.compile(r"^(?:ulica|улица|вулиця|street|ul|ул|вул)\.?\s+", re.IGNORECASE)


def fold_address(value: str | None) -> str:
    """Fold reviewed spelling differences without fuzzy street matching."""
    value = (value or "").casefold().replace("ł", "l")
    value = "".join(
        char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char)
    )
    return " ".join(_PREFIX.sub("", value).replace("\u2013", "-").split()).strip(" .,")


@dataclass(frozen=True, slots=True)
class AddressEvidence:
    """Sanitized components; absence is not evidence of agreement."""

    street: str | None = None
    house_number: str | None = None
    neighborhood: str | None = None
    district: str | None = None
    city: str | None = None
    municipality: str | None = None
    country_code: str | None = None
    result_type: str | None = None
    version: str = ADDRESS_EVIDENCE_VERSION

    def as_json(self) -> dict[str, str | None]:
        """Return only the explicit bounded address field allowlist."""
        return {
            key: value[:240] if value is not None else None for key, value in asdict(self).items()
        }

    @classmethod
    def from_json(cls, value: object) -> AddressEvidence | None:
        """Read versioned evidence, treating legacy or malformed data as absent."""
        if not isinstance(value, dict) or value.get("version") != ADDRESS_EVIDENCE_VERSION:
            return None
        fields = cls.__dataclass_fields__
        if any(item is not None and not isinstance(item, str) for item in value.values()):
            return None
        return cls(
            **{
                key: item[:240]
                for key, item in value.items()
                if key in fields and isinstance(item, str)
            }
        )
