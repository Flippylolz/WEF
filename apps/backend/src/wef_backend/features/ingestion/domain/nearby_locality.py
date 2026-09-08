"""Explicit locality and municipality evidence, never marketing proximity prose."""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD = r"[A-ZĄĆĘŁŃÓŚŹŻ][A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż-]*"
_NAME = rf"{_WORD}(?: {_WORD}){{0,3}}"
_LOCALITY = re.compile(
    rf"^(?P<city>{_NAME}),\s*(?:gmina|гмина)\s+(?P<municipality>{_NAME})"
    r"(?:,\s*(?:PL|Polska|Мазовецкое воеводство|woj\.? mazowieckie))?$"
)


@dataclass(frozen=True, slots=True)
class NearbyLocality:
    """Exact source identity; coordinates still require independent provider proof."""

    city: str
    municipality: str

    @property
    def display(self) -> str:
        """Preserve the municipality needed to disambiguate same-name towns."""
        return f"{self.city}, gmina {self.municipality}"


def nearby_locality(value: str) -> NearbyLocality | None:
    """Recognize a complete pin/address value with an explicit Polish municipality."""
    match = _LOCALITY.fullmatch(" ".join(value.strip().split()))
    return NearbyLocality(match["city"], match["municipality"]) if match else None
