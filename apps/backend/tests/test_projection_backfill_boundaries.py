"""Catalog media projection and guarded geocode/display backfill boundaries."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from tests.test_geocoding import _result
from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_location_display_name_backfill import (
    _backfill_row,
    _BackfillSessionFactory,
    _location_row,
)
from wef_backend.features.catalog.application import ConfidenceIndicator
from wef_backend.features.catalog.infrastructure.models import LocationRow
from wef_backend.features.catalog.infrastructure.offer_detail_adapter import (
    SQLAlchemyOfferDetailAdapter,
)
from wef_backend.features.ingestion.application.geocoding import CachedGeocode
from wef_backend.features.ingestion.domain.geocoding import GeocodeProvider, normalize_geocode_query
from wef_backend.features.ingestion.infrastructure.accept_pending_geocode_pins_adapter import (
    SQLAlchemyAcceptPendingGeocodePinsAdapter,
)
from wef_backend.features.ingestion.infrastructure.location_display_name_backfill import (
    _apply_display_name,
    _payload_for_message,
    _row_to_raw,
    backfill_location_display_names,
)
from wef_backend.features.ingestion.infrastructure.models import (
    DevelopmentRow,
    GeocodeResultRow,
    SourceChannelRow,
    SourceMessageRow,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _transaction_factory(session: MagicMock) -> MagicMock:
    factory = _factory(session)
    factory.begin.return_value = factory()
    return factory


async def test_development_projection_preserves_confidence_indicator() -> None:
    row = DevelopmentRow(
        id=uuid4(), display_name="Synthetic development", name_confidence=Decimal("0.95")
    )
    session = MagicMock(
        execute=AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=row)))
    )
    adapter = SQLAlchemyOfferDetailAdapter(MagicMock())
    projected = await adapter._load_development(session, uuid4())  # noqa: SLF001 - SQL row projection
    assert projected is not None
    assert projected.id == row.id
    assert projected.display_name == row.display_name
    assert projected.name_confidence is ConfidenceIndicator.HIGH


async def test_media_projection_groups_public_variants_in_stable_asset_order() -> None:
    first, second, third = uuid4(), uuid4(), uuid4()
    rows = [
        SimpleNamespace(
            id=identity,
            position=position,
            media_type="image",
            mime_type="image/jpeg",
            width=40,
            height=80,
            duration_seconds=None,
            variant=variant,
            storage_key=key,
        )
        for identity, position, variant, key in (
            (first, 2, "thumbnail_webp_v1", "v1/public_derivative/ab/cd/thumb.webp"),
            (first, 2, "thumbnail_jpeg_v1", "v1/public_derivative/ab/cd/content.jpg"),
            (second, 0, None, None),
            (third, 1, "thumbnail_webp_v1", None),
        )
    ]
    session = MagicMock(execute=AsyncMock(return_value=MagicMock(all=MagicMock(return_value=rows))))
    result = await SQLAlchemyOfferDetailAdapter(MagicMock())._load_media(session, uuid4())  # noqa: SLF001 - SQL row projection
    assert [item.media_asset_id for item in result] == [second, third, first]
    assert result[0].thumbnail_url is result[0].content_url is None
    assert result[1].thumbnail_url is None
    assert result[2].thumbnail_url == "/media/v1/public_derivative/ab/cd/thumb.webp"
    assert result[2].content_url == "/media/v1/public_derivative/ab/cd/content.jpg"


def test_field_confidence_ignores_absent_scores_and_sorts_public_indicators() -> None:
    primary = {
        "extraction_json": {
            "rooms": {"confidence": 0.95},
            "price": {"confidence": "high"},
            "area": {"confidence": 0.8},
            "floor": {},
        }
    }
    assert SQLAlchemyOfferDetailAdapter._field_confidence(primary) == (  # noqa: SLF001 - extraction projection
        ("area", ConfidenceIndicator.MEDIUM),
        ("rooms", ConfidenceIndicator.HIGH),
    )


@pytest.mark.parametrize(
    "payload", ['{"id": 7, "text": "synthetic"}', ["legacy"], '["legacy"]', 3, None]
)
def test_legacy_payload_reconstruction_accepts_only_object_shapes(payload: object) -> None:
    result = _payload_for_message(payload=payload, external_message_id=7)
    assert result == (
        {"id": 7, "text": "synthetic"}
        if isinstance(payload, str) and payload.startswith("{")
        else {"id": 7}
    )


@pytest.mark.parametrize("mode", ["missing", "changed"])
async def test_display_backfill_refuses_disappeared_or_changed_location_identity(mode: str) -> None:
    location = LocationRow(
        normalized_address_hash="changed", display_name="Original", display_address="Original"
    )
    session = MagicMock(get=AsyncMock(return_value=None if mode == "missing" else location))
    factory = _transaction_factory(session)
    if mode == "missing":
        await _apply_display_name(
            factory, location_id=uuid4(), display_name="New", expected_hash="original"
        )
    else:
        with pytest.raises(RuntimeError, match="identity hash changed"):
            await _apply_display_name(
                factory, location_id=uuid4(), display_name="New", expected_hash="original"
            )
    assert location.display_name == "Original"


async def test_display_backfill_limits_locations_after_selecting_current_source() -> None:
    rows = [
        _backfill_row(location=_location_row(display_name="unknown"), text="synthetic")
        for _ in range(2)
    ]
    factory = cast("async_sessionmaker[AsyncSession]", _BackfillSessionFactory(rows))
    report = await backfill_location_display_names(factory, limit=1, apply=False)
    assert report.total == 1


def test_retained_display_payload_must_freeze_as_an_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "wef_backend.features.ingestion.infrastructure.location_display_name_backfill.freeze_json",
        lambda _value: (),
    )
    with pytest.raises(TypeError, match="payload must freeze as an object"):
        _row_to_raw(
            message=SourceMessageRow(raw_payload_json={"id": 7}, external_message_id=7),
            channel=SourceChannelRow(),
        )


@pytest.mark.parametrize("mode", ["cache_missing", "selected", "not_committed", "location_missing"])
async def test_pending_pin_backfill_counts_only_acknowledged_current_selection(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    query = normalize_geocode_query("ul. Marszałkowska 1, Warszawa")
    location = LocationRow(id=uuid4(), display_address=query.original, district=None)
    result_id = uuid4()
    result = GeocodeResultRow(
        provider=GeocodeProvider.FIXTURE.value,
        query_normalized=query.normalized,
        normalizer_version="test",
        scope_version="test",
        request_version="test",
    )
    session = MagicMock(
        execute=AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[(location, result)]))),
        get=AsyncMock(
            return_value=None
            if mode == "location_missing"
            else LocationRow(
                selected_geocode_result_id=result_id if mode == "selected" else uuid4()
            )
        ),
    )
    store = MagicMock(
        get_cached=AsyncMock(
            return_value=None
            if mode == "cache_missing"
            else CachedGeocode(result_id, _result(), None)
        ),
        select_for_location=AsyncMock(),
    )
    monkeypatch.setattr(
        "wef_backend.features.ingestion.infrastructure.accept_pending_geocode_pins_adapter.SQLAlchemyGeocodeStore",
        lambda _factory: store,
    )
    adapter = SQLAlchemyAcceptPendingGeocodePinsAdapter(_factory(session))
    assert await adapter.accept_in_scope_pending_pins() == int(mode == "selected")
    assert store.select_for_location.await_count == int(mode != "cache_missing")
    if mode != "cache_missing":
        assert store.select_for_location.await_args.kwargs["actor_type"] == "automatic_policy"


async def test_pending_pin_aggregate_counts_default_missing_results_to_zero() -> None:
    session = MagicMock(scalar=AsyncMock(side_effect=[3, None, 2]))
    adapter = SQLAlchemyAcceptPendingGeocodePinsAdapter(_factory(session))
    assert await adapter.count_map_eligible_locations() == 3
    assert await adapter.count_needs_review_without_point() == 0
    assert await adapter.count_ungeocoded() == 2
