"""SQLAlchemy adapter for public offer detail lookups."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

from sqlalchemy import and_, select

from wef_backend.features.catalog.application.offer_detail import (
    DevelopmentSummaryDTO,
    LocationSummaryDTO,
    OfferDetailQueryPort,
    OfferDetailRecord,
    OfferMediaDTO,
    SourceHistoryEntryDTO,
    build_public_media_url,
    build_verified_source_url,
    confidence_indicator_from_score,
)
from wef_backend.features.catalog.domain import (
    ContentType,
    LocationReviewStatus,
    MarketType,
    OfferVisibility,
)
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.ingestion.infrastructure.models import (
    DevelopmentRow,
    MediaAssetRow,
    MediaDerivativeRow,
    OfferMediaRow,
    OfferSourceRow,
    SourceChannelRow,
    SourceMessageRow,
    StoredMediaObjectRow,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.catalog.application.map_query import ConfidenceIndicator

_THUMBNAIL_WEBP = "thumbnail_webp_v1"
_THUMBNAIL_JPEG = "thumbnail_jpeg_v1"


class SQLAlchemyOfferDetailAdapter(OfferDetailQueryPort):
    """Load one public offer detail with source and media context."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy async session factory."""
        self._session_factory = session_factory

    async def query_offer_detail(self, offer_id: UUID) -> OfferDetailRecord | None:
        """Return one visible offer detail or null when absent/non-public."""
        offer_statement = (
            select(OfferRow, LocationRow)
            .join(LocationRow, LocationRow.id == OfferRow.location_id)
            .where(
                OfferRow.id == offer_id,
                OfferRow.visibility == OfferVisibility.VISIBLE.value,
                LocationRow.review_status == LocationReviewStatus.ACCEPTED.value,
                LocationRow.out_of_scope.is_(False),
                LocationRow.point.is_not(None),
            )
        )
        async with self._session_factory() as session:
            offer_row = (await session.execute(offer_statement)).one_or_none()
            if offer_row is None:
                return None
            offer, location = offer_row
            development = await self._load_development(session, location.id)
            sources = await self._load_sources(session, offer.id)
            media = await self._load_media(session, offer.id)
        primary = next(
            (item for item in sources if item["relationship"] == "primary"),
            sources[0] if sources else None,
        )
        field_confidence = self._field_confidence(primary)
        source_message_id = primary["source_message_id"] if primary else None
        verified_source_url = (
            build_verified_source_url(
                verified_link_base=primary["verified_link_base"],
                username=primary["username"],
                external_message_id=primary["external_message_id"],
            )
            if primary is not None
            else None
        )
        return OfferDetailRecord(
            id=offer.id,
            content_type=ContentType(offer.content_type),
            market_type=MarketType(offer.market_type),
            published_at=offer.published_at,
            currency=offer.currency,
            price_min_minor=offer.price_min_minor,
            price_max_minor=offer.price_max_minor,
            parking_price_min_minor=offer.parking_price_min_minor,
            parking_price_max_minor=offer.parking_price_max_minor,
            parking_included_in_price=offer.parking_included_in_price,
            storage_price_min_minor=offer.storage_price_min_minor,
            storage_price_max_minor=offer.storage_price_max_minor,
            storage_included_in_price=offer.storage_included_in_price,
            area_min_sqm=offer.area_min_sqm,
            area_max_sqm=offer.area_max_sqm,
            rooms_min=offer.rooms_min,
            rooms_max=offer.rooms_max,
            floor_label=offer.floor_label,
            delivery_label=offer.delivery_label,
            public_source_text=offer.source_text_public_masked,
            parser_version=offer.parser_version,
            location=LocationSummaryDTO(
                id=location.id,
                display_name=location.display_name,
                display_address=location.display_address,
                district=location.district,
                coordinate_precision=location.precision,
                confidence=confidence_indicator_from_score(float(location.confidence)),
            ),
            development=development,
            field_confidence=field_confidence,
            media=media,
            source_message_id=source_message_id,
            verified_source_url=verified_source_url,
            source_history=tuple(
                SourceHistoryEntryDTO(
                    source_message_id=item["source_message_id"],
                    relationship=item["relationship"],
                    published_at=item["published_at"],
                    edited_at=item["edited_at"],
                )
                for item in sources
            ),
        )

    async def _load_development(
        self,
        session: AsyncSession,
        location_id: UUID,
    ) -> DevelopmentSummaryDTO | None:
        """Return the highest-confidence development for the location."""
        statement = (
            select(DevelopmentRow)
            .where(DevelopmentRow.location_id == location_id)
            .order_by(DevelopmentRow.name_confidence.desc(), DevelopmentRow.display_name)
            .limit(1)
        )
        row = (await session.execute(statement)).scalar_one_or_none()
        if row is None:
            return None
        return DevelopmentSummaryDTO(
            id=row.id,
            display_name=row.display_name,
            name_confidence=confidence_indicator_from_score(float(row.name_confidence)),
        )

    async def _load_sources(
        self,
        session: AsyncSession,
        offer_id: UUID,
    ) -> list[dict[str, Any]]:
        """Return related source rows ordered newest-first."""
        statement = (
            select(
                OfferSourceRow.relationship,
                OfferSourceRow.extraction_json,
                SourceMessageRow.id,
                SourceMessageRow.external_message_id,
                SourceMessageRow.published_at,
                SourceMessageRow.edited_at,
                SourceChannelRow.verified_link_base,
                SourceChannelRow.username,
            )
            .join(
                SourceMessageRow,
                SourceMessageRow.id == OfferSourceRow.source_message_id,
            )
            .join(
                SourceChannelRow,
                SourceChannelRow.id == SourceMessageRow.source_channel_id,
            )
            .where(OfferSourceRow.offer_id == offer_id)
            .order_by(SourceMessageRow.published_at.desc(), OfferSourceRow.created_at.desc())
        )
        rows = (await session.execute(statement)).all()
        return [
            {
                "relationship": row.relationship,
                "extraction_json": row.extraction_json,
                "source_message_id": row.id,
                "external_message_id": row.external_message_id,
                "published_at": row.published_at,
                "edited_at": row.edited_at,
                "verified_link_base": row.verified_link_base,
                "username": row.username,
            }
            for row in rows
        ]

    async def _load_media(
        self,
        session: AsyncSession,
        offer_id: UUID,
    ) -> tuple[OfferMediaDTO, ...]:
        """Return ordered public media metadata for one offer."""
        statement = (
            select(
                OfferMediaRow.position,
                MediaAssetRow.id,
                MediaAssetRow.media_type,
                MediaAssetRow.mime_type,
                MediaAssetRow.width,
                MediaAssetRow.height,
                MediaAssetRow.duration_seconds,
                MediaDerivativeRow.variant,
                StoredMediaObjectRow.storage_key,
            )
            .join(MediaAssetRow, MediaAssetRow.id == OfferMediaRow.media_asset_id)
            .outerjoin(
                MediaDerivativeRow,
                and_(
                    MediaDerivativeRow.media_asset_id == MediaAssetRow.id,
                    MediaDerivativeRow.variant.in_((_THUMBNAIL_WEBP, _THUMBNAIL_JPEG)),
                ),
            )
            .outerjoin(
                StoredMediaObjectRow,
                and_(
                    StoredMediaObjectRow.id == MediaDerivativeRow.stored_object_id,
                    StoredMediaObjectRow.storage_class
                    == MediaDerivativeRow.stored_object_storage_class,
                ),
            )
            .where(OfferMediaRow.offer_id == offer_id)
            .order_by(OfferMediaRow.position, MediaDerivativeRow.variant)
        )
        rows = (await session.execute(statement)).all()
        grouped: dict[UUID, dict[str, Any]] = {}
        for row in rows:
            bucket = grouped.setdefault(
                row.id,
                {
                    "position": row.position,
                    "media_asset_id": row.id,
                    "media_type": row.media_type,
                    "mime_type": row.mime_type,
                    "width": row.width,
                    "height": row.height,
                    "duration_seconds": row.duration_seconds,
                    "thumbnail_url": None,
                    "content_url": None,
                },
            )
            if row.storage_key is None or row.variant is None:
                continue
            url = build_public_media_url(row.storage_key)
            if row.variant == _THUMBNAIL_WEBP:
                bucket["thumbnail_url"] = url
            elif row.variant == _THUMBNAIL_JPEG:
                bucket["content_url"] = url
        return tuple(
            OfferMediaDTO(
                media_asset_id=item["media_asset_id"],
                position=item["position"],
                media_type=cast("Literal['image', 'video']", item["media_type"]),
                mime_type=item["mime_type"],
                width=item["width"],
                height=item["height"],
                duration_seconds=item["duration_seconds"],
                thumbnail_url=item["thumbnail_url"],
                content_url=item["content_url"],
            )
            for item in sorted(grouped.values(), key=lambda value: value["position"])
        )

    @staticmethod
    def _field_confidence(
        primary: dict[str, Any] | None,
    ) -> tuple[tuple[str, ConfidenceIndicator], ...]:
        """Map primary extraction provenance to public field indicators."""
        if primary is None:
            return ()
        extraction = cast("dict[str, dict[str, Any]]", primary["extraction_json"] or {})
        indicators: list[tuple[str, ConfidenceIndicator]] = []
        for field_name, payload in sorted(extraction.items()):
            score = payload.get("confidence")
            if not isinstance(score, (int, float)):
                continue
            indicators.append(
                (field_name, confidence_indicator_from_score(float(score))),
            )
        return tuple(indicators)
