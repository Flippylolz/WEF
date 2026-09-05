"""Recover derivatives from verified originals or source-equivalent leased downloads."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from sqlalchemy import select

from wef_backend.features.ingestion.application.media_recovery import (
    MediaClaim,
    MediaRecoveryOutcome,
    MediaSourceUnprovenError,
    MediaUnsupportedError,
)
from wef_backend.features.ingestion.application.media_storage import ProcessMedia
from wef_backend.features.ingestion.domain.media_storage import (
    TRANSFORM_VERSION,
    DerivativeVariant,
    MediaObservation,
    ObservationReason,
    descriptor_identity,
)
from wef_backend.features.ingestion.infrastructure.media_repository import (
    MediaRecoveryOwnershipLostError,
    SQLAlchemyMediaRepository,
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

    from wef_backend.features.ingestion.application.media_recovery import MediaSourcePort
    from wef_backend.features.ingestion.application.media_storage import MediaProcessResult
    from wef_backend.features.ingestion.domain.media_storage import (
        PublicDerivative,
        VerifiedOriginal,
    )
    from wef_backend.features.ingestion.domain.model import MediaDescriptor
    from wef_backend.features.ingestion.infrastructure.media_filesystem import LocalMediaStorage


@dataclass(frozen=True, slots=True)
class _RecoveryFilesystem:
    """Read actual local bytes while retaining the immutable intended descriptor identity."""

    filesystem: LocalMediaStorage
    actual: MediaDescriptor
    intended_identity: str

    def observe_and_store(
        self, descriptor: MediaDescriptor, expected_checksum_sha256: str | None = None
    ) -> MediaObservation:
        """Verify the acquisition path, then retain the original source replay identity."""
        if descriptor_identity(descriptor) != self.intended_identity:
            raise MediaSourceUnprovenError
        observation = self.filesystem.observe_and_store(self.actual, expected_checksum_sha256)
        return replace(observation, descriptor_identity=self.intended_identity)

    def create_derivatives(self, original: VerifiedOriginal) -> tuple[PublicDerivative, ...]:
        """Use the established restricted-original/public-derivative separation."""
        return self.filesystem.create_derivatives(original)


@dataclass(frozen=True, slots=True)
class RecoverStoredMedia:
    """Keep canonical ingestion independent of acquisition and transform failure."""

    factory: async_sessionmaker[AsyncSession]
    filesystem: LocalMediaStorage
    source: MediaSourcePort

    async def __call__(self, claim: MediaClaim) -> MediaRecoveryOutcome:
        """Reuse exact verified evidence first; release downloaded files on every outcome."""
        existing = await self._original(claim)
        lease = None
        checksum = None
        filesystem = self.filesystem
        try:
            if existing is not None:
                path, checksum = existing
                try:
                    if await self._completed(claim, path, checksum):
                        return MediaRecoveryOutcome("completed")
                except MediaRecoveryOwnershipLostError:
                    return MediaRecoveryOutcome("superseded", "source_or_lease_changed")
                actual = replace(claim.item.descriptor, path=path)
                filesystem = replace(filesystem, source_root=filesystem.originals_root)
            else:
                try:
                    actual, lease = await self.source.acquire_media(
                        claim.raw, claim.item.source_ordinal
                    )
                except MediaUnsupportedError:
                    return MediaRecoveryOutcome("unsupported", "unsupported_source_media")
                except MediaSourceUnprovenError:
                    return MediaRecoveryOutcome("quarantined", "source_media_equivalence_unproven")
            item = replace(
                claim.item,
                expected_checksum_sha256=checksum,
                recovery_work_id=claim.id,
                recovery_token=claim.token,
                association_revision_id=claim.association_revision_id,
            )
            processor = ProcessMedia(
                _RecoveryFilesystem(filesystem, actual, descriptor_identity(item.descriptor)),
                SQLAlchemyMediaRepository(self.factory),
            )
            try:
                result = await processor(item)
            except MediaRecoveryOwnershipLostError:
                return MediaRecoveryOutcome("superseded", "source_or_lease_changed")
            return _outcome(result)
        finally:
            if lease is not None:
                lease.release()

    async def _original(self, claim: MediaClaim) -> tuple[str, str] | None:
        """Match revision and checksum, not merely the current logical asset ordinal."""
        async with self.factory() as session:
            row = (
                await session.execute(
                    select(
                        StoredMediaObjectRow.storage_key,
                        StoredMediaObjectRow.checksum_sha256,
                    )
                    .select_from(MediaDispositionAttemptRow)
                    .join(
                        MediaAssetRow,
                        MediaAssetRow.id == MediaDispositionAttemptRow.media_asset_id,
                    )
                    .join(
                        StoredMediaObjectRow,
                        StoredMediaObjectRow.id == MediaAssetRow.stored_object_id,
                    )
                    .where(
                        MediaDispositionAttemptRow.source_message_revision_id
                        == claim.item.source_message_revision_id,
                        MediaDispositionAttemptRow.source_ordinal == claim.item.source_ordinal,
                        MediaDispositionAttemptRow.source_descriptor_identity
                        == descriptor_identity(claim.item.descriptor),
                        MediaDispositionAttemptRow.observed_checksum_sha256
                        == StoredMediaObjectRow.checksum_sha256,
                        StoredMediaObjectRow.storage_class == "restricted_original",
                    )
                    .limit(1)
                )
            ).first()
            return (row[0], row[1]) if row else None

    async def _completed(self, claim: MediaClaim, original_path: str, checksum: str) -> bool:
        """Skip successful variants while repairing missing files or attempts."""
        async with self.factory() as session, session.begin():
            await SQLAlchemyMediaRepository.validate_recovery(
                session,
                replace(
                    claim.item,
                    recovery_work_id=claim.id,
                    recovery_token=claim.token,
                    association_revision_id=claim.association_revision_id,
                ),
            )
            rows = (
                await session.execute(
                    select(
                        MediaDerivativeRow.variant,
                        StoredMediaObjectRow.storage_key,
                    )
                    .select_from(MediaDerivativeAttemptRow)
                    .join(
                        MediaDerivativeRow,
                        MediaDerivativeRow.id == MediaDerivativeAttemptRow.media_derivative_id,
                    )
                    .join(MediaAssetRow, MediaAssetRow.id == MediaDerivativeRow.media_asset_id)
                    .join(
                        OfferMediaRow,
                        OfferMediaRow.media_asset_id == MediaAssetRow.id,
                    )
                    .join(
                        StoredMediaObjectRow,
                        StoredMediaObjectRow.id == MediaDerivativeRow.stored_object_id,
                    )
                    .where(
                        MediaAssetRow.source_message_id == claim.item.source_message_id,
                        MediaAssetRow.source_ordinal == claim.item.source_ordinal,
                        OfferMediaRow.offer_id == claim.item.offer_id,
                        MediaDerivativeAttemptRow.status == "succeeded",
                        MediaDerivativeAttemptRow.transform_version == TRANSFORM_VERSION,
                        MediaDerivativeAttemptRow.source_object_checksum_sha256 == checksum,
                        StoredMediaObjectRow.storage_class == "public_derivative",
                    )
                )
            ).all()
        paths = {str(variant): str(key) for variant, key in rows}
        if set(paths) != {variant.value for variant in DerivativeVariant}:
            return False
        return await asyncio.to_thread(
            lambda: (
                (self.filesystem.originals_root / original_path).is_file()
                and all(
                    (self.filesystem.derivatives_root / path).is_file() for path in paths.values()
                )
            )
        )


def _outcome(result: MediaProcessResult) -> MediaRecoveryOutcome:
    """Classify storage, transform and unsupported outcomes independently."""
    reason = result.observation.reason
    if reason in {
        ObservationReason.MISSING,
        ObservationReason.STORAGE_FAILED,
        ObservationReason.CHANGED_DURING_READ,
    }:
        message = "media storage temporarily unavailable"
        raise OSError(message)
    if reason is not ObservationReason.VERIFIED:
        return MediaRecoveryOutcome("unsupported", reason.value)
    if result.derivative_failure is not None:
        message = "media derivative attempt failed"
        if result.derivative_failure is ObservationReason.STORAGE_FAILED:
            raise OSError(message)
        raise ValueError(message)
    return MediaRecoveryOutcome("completed")
