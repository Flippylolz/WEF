"""Build redacted Telegram worker status and reconciliation reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from wef_backend.features.ingestion.domain.telegram_channel import (
    default_live_channel_identity,
)
from wef_backend.features.ingestion.domain.telegram_worker_ops import (
    COMPOSE_SERVICE,
    DEFAULT_STALE_AFTER,
    FreshnessInput,
    TelegramWorkerStatus,
    classify_freshness,
    reconcile_checkpoints,
    session_rotation_rehearsal_steps,
)


class TelegramWorkerStatusStore(Protocol):
    """Read-only snapshot inputs for worker ops status."""

    async def max_external_message_id(self, *, channel_external_id: str) -> int:
        """Return the highest persisted Telegram message id for the channel."""
        ...

    async def latest_live_checkpoint(
        self,
        *,
        channel_external_id: str,
    ) -> tuple[int | None, datetime | None]:
        """Return (checkpoint last_source_index, finished_at) for the latest live run."""
        ...


@dataclass(frozen=True, slots=True)
class WorkerStatusOptions:
    """Optional overrides for building a worker status report."""

    credentials_ready: bool = False
    session_ready: bool = False
    stale_after: timedelta = DEFAULT_STALE_AFTER
    now: datetime | None = None


async def build_telegram_worker_status(
    store: TelegramWorkerStatusStore,
    *,
    options: WorkerStatusOptions | None = None,
) -> TelegramWorkerStatus:
    """Assemble a redacted worker ops report from env credentials + DB checkpoints."""
    opts = options or WorkerStatusOptions()
    identity = default_live_channel_identity()
    max_id = await store.max_external_message_id(channel_external_id=identity.channel_id)
    live_checkpoint, finished_at = await store.latest_live_checkpoint(
        channel_external_id=identity.channel_id,
    )
    checkpoint_id = live_checkpoint or 0
    reconciliation = reconcile_checkpoints(
        channel_id=identity.channel_id,
        max_persisted_external_id=max_id,
        live_checkpoint_external_id=checkpoint_id,
    )
    current = opts.now or datetime.now(UTC)
    freshness = classify_freshness(
        FreshnessInput(
            credentials_ready=opts.credentials_ready,
            last_committed_at=finished_at,
            connected=None,
            now=current,
            stale_after=opts.stale_after,
        ),
    )
    notes: list[str] = [
        "Public API readiness is independent of telegram-worker freshness.",
    ]
    if not opts.credentials_ready:
        notes.append("Set WEF_TELEGRAM_API_ID and WEF_TELEGRAM_API_HASH in the env file.")
    elif not opts.session_ready:
        notes.append(
            "String session will be generated on first authorized login "
            "(WEF_TELEGRAM_PHONE / WEF_TELEGRAM_LOGIN_CODE).",
        )
    if reconciliation.unexplained:
        notes.append("Live checkpoint is ahead of persisted source messages.")
    return TelegramWorkerStatus(
        compose_service=COMPOSE_SERVICE,
        credentials_ready=opts.credentials_ready,
        session_ready=opts.session_ready,
        freshness=freshness,
        stale_after_seconds=int(opts.stale_after.total_seconds()),
        last_live_run_finished_at=finished_at,
        last_live_checkpoint_external_id=live_checkpoint,
        max_persisted_external_id=max_id,
        reconciliation=reconciliation,
        notes=tuple(notes),
    )


def rotation_rehearsal_report() -> dict[str, object]:
    """Return a JSON-serializable session rotation dry-run checklist."""
    return {
        "mode": "dry_run",
        "steps": [asdict(step) for step in session_rotation_rehearsal_steps()],
        "note": (
            "Rotate by replacing WEF_TELEGRAM_SESSION; the worker generates a new string session."
        ),
    }
