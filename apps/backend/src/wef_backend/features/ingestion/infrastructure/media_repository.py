"""SQLAlchemy media disposition, object, derivative, and association repository."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from wef_backend.features.ingestion.application.media_storage import (
    MediaPersistencePort,
    MediaWorkItem,
)
from wef_backend.features.ingestion.domain.media_storage import (
    TRANSFORM_VERSION,
    VERIFIER_VERSION,
    DerivativeStatus,
    DerivativeVariant,
    MediaObservation,
    MediaType,
    ObservationReason,
    OriginalDisposition,
    PublicDerivative,
    StorageClass,
    StoredObject,
)
from wef_backend.features.ingestion.infrastructure.models import (
    MediaAssetRow,
    MediaDerivativeAttemptRow,
    MediaDerivativeRow,
    MediaDispositionAttemptRow,
    OfferMediaRow,
    StoredMediaObjectRow,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class MediaPersistenceError(RuntimeError):
    """Redacted database failure with bounded orphan-object cleanup keys."""

    def __init__(self, orphaned_keys: tuple[str, ...]) -> None:
        """Expose only application-owned opaque keys, never source paths."""
        self.orphaned_keys = orphaned_keys
        super().__init__("media persistence failed after object publication")


class SQLAlchemyMediaRepository(MediaPersistencePort):
    """Persist replay identities and class-constrained references atomically."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def persist_media_result(
        self,
        *,
        item: MediaWorkItem,
        observation: MediaObservation,
        disposition: OriginalDisposition,
        derivatives: tuple[PublicDerivative, ...],
        derivative_failure: ObservationReason | None,
    ) -> bool:
        """Persist or reuse one terminal original and its independent derivatives."""
        orphaned = tuple(
            item.storage_key
            for item in (
                *(
                    (observation.original.stored_object,)
                    if observation.original is not None
                    else ()
                ),
                *(derivative.stored_object for derivative in derivatives),
            )
        )
        try:
            async with self._session_factory() as session, session.begin():
                existing = await session.scalar(
                    select(MediaDispositionAttemptRow.id).where(
                        MediaDispositionAttemptRow.source_message_id == item.source_message_id,
                        MediaDispositionAttemptRow.source_ordinal == item.source_ordinal,
                        MediaDispositionAttemptRow.source_message_revision_id
                        == item.source_message_revision_id,
                        MediaDispositionAttemptRow.source_descriptor_identity
                        == observation.descriptor_identity,
                        MediaDispositionAttemptRow.content_identity == observation.content_identity,
                        MediaDispositionAttemptRow.verifier_version == VERIFIER_VERSION,
                        MediaDispositionAttemptRow.association_version == item.association_version,
                    ),
                )
                if existing is not None:
                    return True
                asset = await self._upsert_asset(session, item, observation)
                session.add(
                    MediaDispositionAttemptRow(
                        id=uuid4(),
                        source_message_id=item.source_message_id,
                        source_ordinal=item.source_ordinal,
                        source_message_revision_id=item.source_message_revision_id,
                        source_descriptor_identity=observation.descriptor_identity,
                        observation_status=observation.status.value,
                        observation_reason_code=observation.reason.value,
                        observed_checksum_sha256=observation.observed_checksum_sha256,
                        observed_byte_size=observation.observed_byte_size,
                        content_identity=observation.content_identity,
                        attempt_number=1,
                        verifier_version=VERIFIER_VERSION,
                        association_version=item.association_version,
                        disposition=disposition.value,
                        reason_code=_disposition_reason(disposition, observation),
                        media_asset_id=asset.id if asset is not None else None,
                        attempted_at=datetime.now(UTC),
                    ),
                )
                if asset is not None:
                    await self._associate_offer(session, item, asset.id)
                    await self._record_derivatives(
                        session,
                        asset.id,
                        observation,
                        derivatives,
                        derivative_failure,
                    )
            return False  # noqa: TRY300
        except SQLAlchemyError as error:
            raise MediaPersistenceError(orphaned) from error

    async def _upsert_asset(
        self,
        session: AsyncSession,
        item: MediaWorkItem,
        observation: MediaObservation,
    ) -> MediaAssetRow | None:
        original = observation.original
        if original is None:
            return None
        stored_id = await self._upsert_object(session, original.stored_object)
        asset = await session.scalar(
            select(MediaAssetRow)
            .where(
                MediaAssetRow.source_message_id == item.source_message_id,
                MediaAssetRow.source_ordinal == item.source_ordinal,
            )
            .with_for_update(),
        )
        descriptor_json = {
            "duration_seconds": item.descriptor.duration_seconds,
            "height": item.descriptor.height,
            "kind": item.descriptor.kind.value,
            "mime_type": item.descriptor.mime_type,
            "path": item.descriptor.path,
            "size_bytes": item.descriptor.size_bytes,
            "width": item.descriptor.width,
        }
        if asset is None:
            asset = MediaAssetRow(
                id=uuid4(),
                source_message_id=item.source_message_id,
                source_ordinal=item.source_ordinal,
                source_descriptor_json=descriptor_json,
                stored_object_id=stored_id,
                stored_object_storage_class=StorageClass.RESTRICTED_ORIGINAL.value,
                media_type=original.media_type.value,
                mime_type=original.mime_type,
                byte_size=original.stored_object.byte_size,
                width=original.width,
                height=original.height,
                duration_seconds=original.duration_seconds,
            )
            session.add(asset)
        else:
            asset.source_descriptor_json = descriptor_json
            asset.stored_object_id = stored_id
            asset.stored_object_storage_class = StorageClass.RESTRICTED_ORIGINAL.value
            asset.media_type = original.media_type.value
            asset.mime_type = original.mime_type
            asset.byte_size = original.stored_object.byte_size
            asset.width = original.width
            asset.height = original.height
            asset.duration_seconds = original.duration_seconds
        await session.flush()
        return asset

    async def _upsert_object(self, session: AsyncSession, stored: StoredObject) -> UUID:
        object_id = uuid4()
        inserted = await session.scalar(
            insert(StoredMediaObjectRow)
            .values(
                id=object_id,
                storage_backend="local_filesystem",
                storage_key=stored.storage_key,
                storage_class=stored.storage_class.value,
                checksum_sha256=stored.checksum_sha256,
                mime_type=stored.mime_type,
                byte_size=stored.byte_size,
            )
            .on_conflict_do_nothing(
                constraint="uq_stored_media_objects_class_checksum",
            )
            .returning(StoredMediaObjectRow.id),
        )
        if inserted is not None:
            return inserted
        existing = await session.scalar(
            select(StoredMediaObjectRow.id).where(
                StoredMediaObjectRow.storage_backend == "local_filesystem",
                StoredMediaObjectRow.storage_class == stored.storage_class.value,
                StoredMediaObjectRow.checksum_sha256 == stored.checksum_sha256,
                StoredMediaObjectRow.byte_size == stored.byte_size,
            ),
        )
        if existing is None:
            message = "stored media deduplication produced no durable row"
            raise RuntimeError(message)
        return existing

    async def _associate_offer(
        self,
        session: AsyncSession,
        item: MediaWorkItem,
        asset_id: UUID,
    ) -> None:
        if item.offer_id is None or item.association_rule is None:
            return
        existing = await session.scalar(
            select(OfferMediaRow).where(
                OfferMediaRow.offer_id == item.offer_id,
                OfferMediaRow.media_asset_id == asset_id,
            ),
        )
        if existing is not None:
            return
        position = await session.scalar(
            select(func.max(OfferMediaRow.position)).where(OfferMediaRow.offer_id == item.offer_id),
        )
        session.add(
            OfferMediaRow(
                offer_id=item.offer_id,
                media_asset_id=asset_id,
                position=(position if position is not None else -1) + 1,
                association_rule=item.association_rule.value,
                association_confidence=Decimal(str(item.association_confidence)),
            ),
        )

    async def _record_derivatives(
        self,
        session: AsyncSession,
        asset_id: UUID,
        observation: MediaObservation,
        derivatives: tuple[PublicDerivative, ...],
        derivative_failure: ObservationReason | None,
    ) -> None:
        if observation.original is None or observation.original.media_type is not MediaType.IMAGE:
            return
        for derivative in derivatives:
            await self._record_derivative_success(session, asset_id, derivative)
        if derivative_failure is not None:
            for variant in DerivativeVariant:
                await self._record_derivative_failure(
                    session,
                    asset_id,
                    variant,
                    observation.original.stored_object.checksum_sha256,
                    derivative_failure,
                )

    async def _record_derivative_success(
        self,
        session: AsyncSession,
        asset_id: UUID,
        derivative: PublicDerivative,
    ) -> None:
        existing_attempt = await session.scalar(
            select(MediaDerivativeAttemptRow.id).where(
                MediaDerivativeAttemptRow.media_asset_id == asset_id,
                MediaDerivativeAttemptRow.variant == derivative.variant.value,
                MediaDerivativeAttemptRow.transform_version == TRANSFORM_VERSION,
                MediaDerivativeAttemptRow.source_object_checksum_sha256
                == derivative.source_checksum_sha256,
                MediaDerivativeAttemptRow.status == DerivativeStatus.SUCCEEDED.value,
            ),
        )
        if existing_attempt is not None:
            return
        object_id = await self._upsert_object(session, derivative.stored_object)
        current = await session.scalar(
            select(MediaDerivativeRow)
            .where(
                MediaDerivativeRow.media_asset_id == asset_id,
                MediaDerivativeRow.variant == derivative.variant.value,
            )
            .with_for_update(),
        )
        if current is None:
            current = MediaDerivativeRow(
                id=uuid4(),
                media_asset_id=asset_id,
                stored_object_id=object_id,
                stored_object_storage_class=StorageClass.PUBLIC_DERIVATIVE.value,
                variant=derivative.variant.value,
                width=derivative.width,
                height=derivative.height,
            )
            session.add(current)
        else:
            current.stored_object_id = object_id
            current.stored_object_storage_class = StorageClass.PUBLIC_DERIVATIVE.value
            current.width = derivative.width
            current.height = derivative.height
        await session.flush()
        attempt_number = await self._next_derivative_attempt(
            session,
            asset_id,
            derivative.variant,
        )
        now = datetime.now(UTC)
        session.add(
            MediaDerivativeAttemptRow(
                id=uuid4(),
                media_asset_id=asset_id,
                variant=derivative.variant.value,
                attempt_number=attempt_number,
                transform_version=TRANSFORM_VERSION,
                status=DerivativeStatus.SUCCEEDED.value,
                reason_code=None,
                source_object_checksum_sha256=derivative.source_checksum_sha256,
                media_derivative_id=current.id,
                started_at=now,
                finished_at=now,
            ),
        )

    async def _record_derivative_failure(
        self,
        session: AsyncSession,
        asset_id: UUID,
        variant: DerivativeVariant,
        source_checksum: str,
        reason: ObservationReason,
    ) -> None:
        existing = await session.scalar(
            select(MediaDerivativeAttemptRow.id).where(
                MediaDerivativeAttemptRow.media_asset_id == asset_id,
                MediaDerivativeAttemptRow.variant == variant.value,
                MediaDerivativeAttemptRow.transform_version == TRANSFORM_VERSION,
                MediaDerivativeAttemptRow.source_object_checksum_sha256 == source_checksum,
                MediaDerivativeAttemptRow.status == DerivativeStatus.FAILED.value,
            ),
        )
        if existing is not None:
            return
        attempt_number = await self._next_derivative_attempt(session, asset_id, variant)
        now = datetime.now(UTC)
        session.add(
            MediaDerivativeAttemptRow(
                id=uuid4(),
                media_asset_id=asset_id,
                variant=variant.value,
                attempt_number=attempt_number,
                transform_version=TRANSFORM_VERSION,
                status=DerivativeStatus.FAILED.value,
                reason_code=reason.value,
                source_object_checksum_sha256=source_checksum,
                media_derivative_id=None,
                started_at=now,
                finished_at=now,
            ),
        )

    @staticmethod
    async def _next_derivative_attempt(
        session: AsyncSession,
        asset_id: UUID,
        variant: DerivativeVariant,
    ) -> int:
        latest = await session.scalar(
            select(func.max(MediaDerivativeAttemptRow.attempt_number)).where(
                MediaDerivativeAttemptRow.media_asset_id == asset_id,
                MediaDerivativeAttemptRow.variant == variant.value,
            ),
        )
        return (latest or 0) + 1


def _disposition_reason(
    disposition: OriginalDisposition,
    observation: MediaObservation,
) -> str:
    if disposition is OriginalDisposition.STORED:
        return ObservationReason.VERIFIED.value
    if disposition is OriginalDisposition.UNASSOCIATED:
        return OriginalDisposition.UNASSOCIATED.value
    return observation.reason.value
