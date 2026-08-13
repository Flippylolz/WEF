"""Compatibility adapter for the retired E0 list proof."""

from collections.abc import Sequence

from wef_backend.features.estates.application import EstateQueryPort, EstateRecord


class RetiredEstateQueryAdapter(EstateQueryPort):
    """Keep the deprecated additive contract inert until frontend replacement."""

    async def list_estate_records(self) -> Sequence[EstateRecord]:
        """Return no proof records without touching obsolete persistence."""
        return ()
