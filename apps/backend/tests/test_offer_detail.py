"""Unit tests for offer detail application helpers and decoration."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from wef_backend.features.catalog.application import (
    ConfidenceIndicator,
    GetOfferDetail,
    OfferDetailRecord,
    OfferMediaDTO,
    build_public_media_url,
    build_verified_source_url,
    confidence_indicator_from_score,
)
from wef_backend.features.catalog.application.offer_detail import (
    DevelopmentSummaryDTO,
    LocationSummaryDTO,
)
from wef_backend.features.catalog.domain import ContentType, MarketType


def test_confidence_indicator_thresholds() -> None:
    """Map numeric extraction confidence to coarse public indicators."""
    assert confidence_indicator_from_score(0.95) is ConfidenceIndicator.HIGH
    assert confidence_indicator_from_score(0.90) is ConfidenceIndicator.HIGH
    assert confidence_indicator_from_score(0.80) is ConfidenceIndicator.MEDIUM
    assert confidence_indicator_from_score(0.75) is ConfidenceIndicator.MEDIUM
    assert confidence_indicator_from_score(0.50) is ConfidenceIndicator.LOW


def test_verified_source_url_requires_verified_channel() -> None:
    """Build only verified Telegram message URLs."""
    assert (
        build_verified_source_url(
            verified_link_base=None,
            username="elestate_warszawa",
            external_message_id=42,
        )
        == "https://t.me/elestate_warszawa/42"
    )
    assert (
        build_verified_source_url(
            verified_link_base="https://t.me/elestate_warszawa",
            username=None,
            external_message_id=7,
        )
        == "https://t.me/elestate_warszawa/7"
    )
    assert (
        build_verified_source_url(
            verified_link_base=None,
            username="unknown_channel",
            external_message_id=1,
        )
        is None
    )


def test_public_media_url_is_opaque_and_same_origin() -> None:
    """Return bounded same-origin media paths without exposing host paths."""
    assert (
        build_public_media_url("v1/public_derivative/ab/cd/hash.webp")
        == "/media/v1/public_derivative/ab/cd/hash.webp"
    )
    assert (
        build_public_media_url("/v1/public_derivative/ab/cd/hash.webp")
        == "/media/v1/public_derivative/ab/cd/hash.webp"
    )


async def test_get_offer_detail_decorates_summary_fields() -> None:
    """Decorate one persistence-neutral record into a public detail DTO."""

    class FakeOfferDetailQuery:
        async def query_offer_detail(self, offer_id: UUID) -> OfferDetailRecord | None:
            del offer_id
            return OfferDetailRecord(
                id=UUID("20000000-0000-4000-8000-000000000002"),
                content_type=ContentType.UNIT,
                market_type=MarketType.SECONDARY,
                published_at=datetime(2026, 7, 18, 9, 30, tzinfo=UTC),
                currency="PLN",
                price_min_minor=105_000_000,
                price_max_minor=105_000_000,
                parking_price_min_minor=None,
                parking_price_max_minor=None,
                parking_included_in_price=False,
                storage_price_min_minor=None,
                storage_price_max_minor=None,
                storage_included_in_price=False,
                area_min_sqm=Decimal("48.20"),
                area_max_sqm=Decimal("48.20"),
                rooms_min=2,
                rooms_max=2,
                floor_label="Synthetic floor 4",
                delivery_label=None,
                public_source_text="Masked public text only.",
                parser_version="synthetic-m1-v1",
                location=LocationSummaryDTO(
                    id=UUID("10000000-0000-4000-8000-000000000001"),
                    display_name="Synthetic Central Residence",
                    display_address="Synthetic address 1",
                    district="srodmiescie",
                    coordinate_precision="building",
                    confidence=ConfidenceIndicator.HIGH,
                ),
                development=DevelopmentSummaryDTO(
                    id=UUID("30000000-0000-4000-8000-000000000001"),
                    display_name="Synthetic Project",
                    name_confidence=ConfidenceIndicator.MEDIUM,
                ),
                field_confidence=(("area_sqm", ConfidenceIndicator.HIGH),),
                media=(
                    OfferMediaDTO(
                        media_asset_id=UUID("40000000-0000-4000-8000-000000000001"),
                        position=0,
                        media_type="image",
                        mime_type="image/webp",
                        width=320,
                        height=240,
                        duration_seconds=None,
                        thumbnail_url="/media/v1/public_derivative/ab/cd/thumb.webp",
                        content_url="/media/v1/public_derivative/ab/cd/full.jpg",
                    ),
                ),
                source_message_id=None,
                verified_source_url=None,
                source_history=(),
            )

    detail = await GetOfferDetail(FakeOfferDetailQuery())(
        UUID("20000000-0000-4000-8000-000000000002"),
    )
    assert detail is not None
    assert detail.display_name == "unit · secondary"
    assert detail.data_origin == "parser"
    assert detail.data_confidence.value == "complete"
    assert detail.public_source_text == "Masked public text only."
    assert detail.development is not None
    assert detail.media[0].thumbnail_url is not None
    assert detail.media[0].thumbnail_url.startswith("/media/")


async def test_get_offer_detail_marks_active_ai_origin() -> None:
    """Expose ai_assisted when persistence reports an active AI-origin field."""

    class FakeOfferDetailQuery:
        async def query_offer_detail(self, offer_id: UUID) -> OfferDetailRecord | None:
            del offer_id
            return OfferDetailRecord(
                id=UUID("20000000-0000-4000-8000-000000000002"),
                content_type=ContentType.UNIT,
                market_type=MarketType.SECONDARY,
                published_at=datetime(2026, 7, 18, 9, 30, tzinfo=UTC),
                currency="PLN",
                price_min_minor=105_000_000,
                price_max_minor=105_000_000,
                parking_price_min_minor=None,
                parking_price_max_minor=None,
                parking_included_in_price=False,
                storage_price_min_minor=None,
                storage_price_max_minor=None,
                storage_included_in_price=False,
                area_min_sqm=Decimal("48.20"),
                area_max_sqm=Decimal("48.20"),
                rooms_min=2,
                rooms_max=2,
                floor_label="4",
                delivery_label=None,
                public_source_text="Masked public text only.",
                parser_version="synthetic-m1-v1",
                location=LocationSummaryDTO(
                    id=UUID("10000000-0000-4000-8000-000000000001"),
                    display_name="Synthetic Central Residence",
                    display_address="Synthetic address 1",
                    district="srodmiescie",
                    coordinate_precision="building",
                    confidence=ConfidenceIndicator.HIGH,
                ),
                development=None,
                field_confidence=(),
                media=(),
                source_message_id=None,
                verified_source_url=None,
                source_history=(),
                has_active_ai_origin=True,
            )

    detail = await GetOfferDetail(FakeOfferDetailQuery())(
        UUID("20000000-0000-4000-8000-000000000002"),
    )
    assert detail is not None
    assert detail.data_origin == "ai_assisted"
