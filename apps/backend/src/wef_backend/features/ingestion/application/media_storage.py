"""Media verification/storage orchestration owned by ingestion application."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from wef_backend.features.ingestion.domain.media_storage import (
    MediaObservation,
    ObservationReason,
    OriginalDisposition,
    PublicDerivative,
)

_SHA256_LENGTH = 64

if TYPE_CHECKING:
    from uuid import UUID

    from wef_backend.features.ingestion.domain.media_grouping import MediaAssociationRule
    from wef_backend.features.ingestion.domain.media_storage import VerifiedOriginal
    from wef_backend.features.ingestion.domain.model import MediaDescriptor


@dataclass(frozen=True, slots=True)
class MediaWorkItem:
    """Revision-anchored expected source media and optional offer association."""

    source_message_id: UUID
    source_message_revision_id: UUID
    source_ordinal: int
    descriptor: MediaDescriptor
    association_version: str
    offer_id: UUID | None = None
    association_rule: MediaAssociationRule | None = None
    association_confidence: float | None = None
    expected_checksum_sha256: str | None = None

    def __post_init__(self) -> None:
        """Retain non-negative E2 ordinals and complete association shapes."""
        if self.source_ordinal < 0 or not self.association_version:
            message = "media work item requires a non-negative ordinal and association version"
            raise ValueError(message)
        associated = self.offer_id is not None
        if associated != (self.association_rule is not None) or associated != (
            self.association_confidence is not None
        ):
            message = "media association identity, rule, and confidence must be complete"
            raise ValueError(message)
        if self.association_confidence is not None and not 0 <= self.association_confidence <= 1:
            message = "media association confidence must be between zero and one"
            raise ValueError(message)
        if self.expected_checksum_sha256 is not None and (
            len(self.expected_checksum_sha256) != _SHA256_LENGTH
            or any(char not in "0123456789abcdef" for char in self.expected_checksum_sha256)
        ):
            message = "expected media checksum must be a lowercase SHA-256"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class MediaProcessResult:
    """Persisted result of one expected source media item."""

    disposition: OriginalDisposition
    observation: MediaObservation
    derivatives: tuple[PublicDerivative, ...]
    derivative_failure: ObservationReason | None
    replayed: bool


class MediaFilesystemPort(Protocol):
    """Safe source reading and class-separated atomic object storage."""

    def observe_and_store(
        self,
        descriptor: MediaDescriptor,
        expected_checksum_sha256: str | None = None,
    ) -> MediaObservation:
        """Verify and publish an original or return a pre-read rejection."""
        ...

    def create_derivatives(self, original: VerifiedOriginal) -> tuple[PublicDerivative, ...]:
        """Create independently auditable public derivatives."""
        ...


class MediaPersistencePort(Protocol):
    """Durable disposition/asset/derivative attempt repository."""

    async def persist_media_result(
        self,
        *,
        item: MediaWorkItem,
        observation: MediaObservation,
        disposition: OriginalDisposition,
        derivatives: tuple[PublicDerivative, ...],
        derivative_failure: ObservationReason | None,
    ) -> bool:
        """Persist or reuse the terminal replay identity and return replay state."""
        ...


@dataclass(frozen=True, slots=True)
class ProcessMedia:
    """Verify, atomically publish, derive, and durably reconcile one item."""

    filesystem: MediaFilesystemPort
    repository: MediaPersistencePort

    async def __call__(self, item: MediaWorkItem) -> MediaProcessResult:
        """Keep original disposition independent from derivative failures."""
        observation = await asyncio.to_thread(
            self.filesystem.observe_and_store,
            item.descriptor,
            item.expected_checksum_sha256,
        )
        disposition = _disposition(item, observation)
        derivatives: tuple[PublicDerivative, ...] = ()
        derivative_failure: ObservationReason | None = None
        if observation.original is not None:
            try:
                derivatives = await asyncio.to_thread(
                    self.filesystem.create_derivatives,
                    observation.original,
                )
            except RuntimeError as error:
                reason = getattr(error, "reason", ObservationReason.DECODE_FAILED)
                derivative_failure = (
                    reason
                    if isinstance(reason, ObservationReason)
                    else ObservationReason.DECODE_FAILED
                )
        replayed = await self.repository.persist_media_result(
            item=item,
            observation=observation,
            disposition=disposition,
            derivatives=derivatives,
            derivative_failure=derivative_failure,
        )
        return MediaProcessResult(
            disposition=disposition,
            observation=observation,
            derivatives=derivatives,
            derivative_failure=derivative_failure,
            replayed=replayed,
        )


def _disposition(item: MediaWorkItem, observation: MediaObservation) -> OriginalDisposition:
    """Map verification and association evidence to one stable outcome."""
    if item.offer_id is None:
        return OriginalDisposition.UNASSOCIATED
    if observation.original is not None:
        return OriginalDisposition.STORED
    if observation.reason is ObservationReason.MISSING:
        return OriginalDisposition.MISSING
    if observation.reason is ObservationReason.UNSUPPORTED_DESCRIPTOR:
        return OriginalDisposition.UNSUPPORTED
    return OriginalDisposition.REJECTED
