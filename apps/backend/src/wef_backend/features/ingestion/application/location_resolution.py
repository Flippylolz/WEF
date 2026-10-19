"""Municipal-first resolution with bounded, source-grounded address recovery."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeErrorCode,
    SelectionReason,
    normalize_geocode_query,
)

if TYPE_CHECKING:
    from uuid import UUID

    from wef_backend.features.ingestion.application.geocoding import (
        GeocodeResolution,
        GeocodeStorePort,
        ResolveGeocode,
    )


_MIN_STREET = 2
_MAX_STREET = 120


class MunicipalUnavailableError(RuntimeError):
    """The municipal source could not be read or validated."""


class AddressRecoveryPort(Protocol):
    """Recover address text only; coordinates never cross this boundary."""

    async def recover(self, source: str, district: str | None) -> str | None:
        """Return a source-supported address or no recovery."""
        ...


@dataclass(frozen=True, slots=True)
class ResolveLocation:
    """Try authoritative geometry, hosted lookup, then one recovery pass."""

    municipal: ResolveGeocode
    hosted: ResolveGeocode
    store: GeocodeStorePort
    recovery: AddressRecoveryPort | None = None

    async def __call__(
        self, *, source_query: str, district: str | None = None, location_id: UUID | None = None
    ) -> GeocodeResolution:
        """Select only after all bounded lookups finish; preserve caller source."""
        result = await self._lookup(source_query, district)
        if (
            not result.decision.select_result
            and result.cached.result.error_code in {None, GeocodeErrorCode.NO_RESULT}
            and result.decision.reason is not SelectionReason.AMBIGUOUS_CANDIDATES
            and self.recovery is not None
        ):
            recovered = await self.recovery.recover(source_query, district)
            if recovered and recovered != source_query:
                result = await self._lookup(recovered, district)
        if location_id is not None:
            await self.store.select_for_location(
                location_id=location_id,
                cached=result.cached,
                decision=result.decision,
                actor_type="automatic_policy",
                actor_id=None,
            )
        return result

    async def _lookup(self, source: str, district: str | None) -> GeocodeResolution:
        municipal = None
        unavailable = None
        try:
            municipal = await self.municipal(source_query=source, district=district)
        except MunicipalUnavailableError as error:
            unavailable = error
        if municipal is not None and (
            municipal.decision.select_result
            or municipal.decision.reason is SelectionReason.AMBIGUOUS_CANDIDATES
        ):
            return municipal
        hosted = await self.hosted(source_query=source, district=district)
        if hosted.decision.select_result:
            return hosted
        # An authoritative source outage is not a durable quality verdict.
        if unavailable is not None:
            raise unavailable
        return hosted


def recovered_address(source: str, district: str | None, street: object) -> str | None:
    """Require an exact source quote and retain all existing locality/number constraints."""
    if not isinstance(street, str) or not _MIN_STREET <= len(street.strip()) <= _MAX_STREET:
        return None
    street = street.strip()
    if street not in source or any(char.isdigit() for char in street):
        return None
    query = normalize_geocode_query(source, district)
    if query.address is None:
        return None
    if not _grounded_street(source, query.address.street, street):
        return None
    address = replace(query.address, street=street)
    parts = [
        "ul. " + street + (" " + address.house_number if address.house_number else ""),
        address.neighborhood,
        address.district,
        address.city,
    ]
    return ", ".join(part for part in parts if part)


def _grounded_street(source: str, original: str | None, street: str) -> bool:
    """Never shorten a legitimate multiword street into another street name."""
    if original:
        original = re.sub(r"^(?:ul\.?|ulica)\s+", "", original, flags=re.IGNORECASE)
        if not original.startswith(street):
            return False
        remainder = original[len(street) :]
        return not remainder or remainder.startswith((" obok ", " przy ", " near ", " - ", " — "))
    return (
        re.search(
            r"(?:ul\.?|ulica|ул\.?|вул\.?)\s+"
            + re.escape(street)
            + r"(?=$|[,;|]|\s+\d|\s+(?:obok|przy|near)\s)",
            source,
            re.IGNORECASE,
        )
        is not None
    )
