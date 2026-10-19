"""Independent, bounded media recovery with durable ownership and safe outcomes."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from uuid import UUID  # noqa: TC003 — runtime dataclass annotation

from wef_backend.features.ingestion.application.archive_retry import (
    ArchiveFailure,
    classify_archive_failure,
)
from wef_backend.features.ingestion.domain.media_storage import TRANSFORM_VERSION, VERIFIER_VERSION

if TYPE_CHECKING:
    from wef_backend.features.ingestion.application.media_storage import MediaWorkItem
    from wef_backend.features.ingestion.application.telegram_live import MediaLease
    from wef_backend.features.ingestion.domain.model import MediaDescriptor, RawMessage

MEDIA_RECOVERY_POLICY = f"media-recovery-v1:{VERIFIER_VERSION}:{TRANSFORM_VERSION}"
LEASE_SECONDS = 120


class MediaSourceUnprovenError(ValueError):
    """Remote bytes cannot safely satisfy the intended immutable media identity."""


class MediaUnsupportedError(ValueError):
    """The descriptor is outside the existing supported media policy."""


class MediaSourcePort(Protocol):
    """Acquire source-equivalent bytes while retaining an inward-owned cleanup lease."""

    async def acquire_media(
        self, raw: RawMessage, ordinal: int
    ) -> tuple[MediaDescriptor, MediaLease]:
        """Return verified source metadata and exclusive staging ownership."""
        ...


@dataclass(frozen=True, slots=True)
class MediaClaim:
    """Immutable source intention and fenced execution token."""

    id: UUID
    token: UUID
    channel_id: UUID
    raw: RawMessage
    item: MediaWorkItem
    association_revision_id: UUID | None


@dataclass(frozen=True, slots=True)
class MediaRecoveryOutcome:
    """Safe media-only disposition, independent of canonical source completion."""

    state: str
    reason: str | None = None


class MediaRecoveryStore(Protocol):
    """Durable discovery, claims and token-checked transitions."""

    async def discover(self, limit: int = 100) -> int:
        """Resolve at most one bounded page of canonical intentions."""
        ...

    async def claim(self) -> MediaClaim | None:
        """Claim one due item without retaining a transaction during acquisition."""
        ...

    async def renew(self, claim: MediaClaim) -> bool:
        """Renew unexpired ownership; stale tokens cannot revive a lease."""
        ...

    async def finish(self, claim: MediaClaim, outcome: MediaRecoveryOutcome) -> bool:
        """Record a terminal outcome only while ownership is valid."""
        ...

    async def pause(self, reason: str) -> None:
        """Persist a media-only systemic pause while preserving canonical ingestion."""
        ...

    async def fail(self, claim: MediaClaim, failure: ArchiveFailure) -> bool:
        """Persist independent media retry or pause without rewinding text work."""
        ...


class RecoverMedia(Protocol):
    """Acquire or reuse verified bytes and persist missing derivatives."""

    async def __call__(self, claim: MediaClaim) -> MediaRecoveryOutcome:
        """Use the claim's immutable source and association evidence."""
        ...


@dataclass(frozen=True, slots=True)
class MediaRecoveryRunner:
    """One active item, ten claims per cycle, independently supervised retries."""

    store: MediaRecoveryStore
    recover: RecoverMedia

    async def run_once(self) -> int:
        """Do bounded discovery and fair recovery without blocking canonical ingestion."""
        await self.store.discover(100)
        completed = 0
        for _ in range(10):
            claim = await self.store.claim()
            if claim is None:
                break
            try:
                outcome = await self._owned_attempt(claim)
            except asyncio.CancelledError:
                raise
            except Exception as error:  # noqa: BLE001 — persist safe per-item recovery failures
                await self.store.fail(claim, classify_archive_failure(error))
            else:
                if outcome is not None and await self.store.finish(claim, outcome):
                    completed += int(outcome.state == "completed")
        return completed

    async def _owned_attempt(self, claim: MediaClaim) -> MediaRecoveryOutcome | None:
        """Cancel acquisition after lease loss and always await staging cleanup."""
        task = asyncio.create_task(self.recover(claim))
        try:
            while True:
                done, _ = await asyncio.wait({task}, timeout=LEASE_SECONDS / 3)
                if done:
                    return await task
                if not await self.store.renew(claim):
                    return None
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def run(self, stop: asyncio.Event) -> None:
        """Repeat while the worker is connected; shutdown leaves recoverable leases."""
        while not stop.is_set():
            try:
                await self.run_once()
            except Exception as error:  # noqa: BLE001 — isolate unexpected media stage failures
                await self.store.pause(classify_archive_failure(error).category)
            with suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=5)
