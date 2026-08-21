"""Tests for promoting historical offers and hiding synthetic M1 seed."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from wef_backend.features.catalog.application.promote_public_catalog import (
    PromotePublicCatalog,
    PromotePublicCatalogResult,
)


@dataclass
class _FakeStore:
    promoted: int = 10
    hidden: int = 5
    rejected: int = 4
    visible: int = 10
    map_locations: int = 8
    calls: list[str] = field(default_factory=list)

    async def promote_reviewed_offers(self) -> int:
        self.calls.append("promote")
        return self.promoted

    async def hide_synthetic_offers(self) -> int:
        self.calls.append("hide")
        return self.hidden

    async def reject_synthetic_locations(self) -> int:
        self.calls.append("reject")
        return self.rejected

    async def count_visible_offers(self) -> int:
        self.calls.append("visible")
        return self.visible

    async def count_map_eligible_locations(self) -> int:
        self.calls.append("map")
        return self.map_locations


@pytest.mark.asyncio
async def test_promote_public_catalog_orders_store_calls() -> None:
    store = _FakeStore()
    result = await PromotePublicCatalog(store)()
    assert result == PromotePublicCatalogResult(
        offers_promoted=10,
        synthetic_offers_hidden=5,
        synthetic_locations_rejected=4,
        visible_offers=10,
        map_eligible_locations=8,
    )
    assert store.calls == ["promote", "hide", "reject", "visible", "map"]
