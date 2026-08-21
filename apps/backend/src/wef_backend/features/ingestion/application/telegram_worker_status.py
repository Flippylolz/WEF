"""Build redacted Telegram worker status and reconciliation reports."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from wef_backend.features.ingestion.domain.telegram_channel import (
    TelegramWorkerSecretPaths,
    default_live_channel_identity,
    inspect_secret_file,
)
from wef_backend.features.ingestion.domain.telegram_worker_ops import (
    ACTIVATION_ENV,
    COMPOSE_PROFILE,
    DEFAULT_STALE_AFTER,
    LIVE_LOOP_ENV,
    FreshnessInput,
    TelegramWorkerStatus,
    classify_freshness,
    production_activation_allowed,
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

    activation_enabled: bool | None = None
    live_loop_enabled: bool | None = None
    owner_gate_open: bool = False
    stale_after: timedelta = DEFAULT_STALE_AFTER
    now: datetime | None = None


async def build_telegram_worker_status(
    store: TelegramWorkerStatusStore,
    *,
    secret_paths: TelegramWorkerSecretPaths,
    options: WorkerStatusOptions | None = None,
) -> TelegramWorkerStatus:
    """Assemble a redacted worker ops report from secrets + DB checkpoints."""
    opts = options or WorkerStatusOptions()
    identity = default_live_channel_identity()
    secret_files = tuple(inspect_secret_file(path) for path in secret_paths.required_files())
    secrets_ready = all(item.present and item.owner_readable_only for item in secret_files)
    activation = (
        opts.activation_enabled
        if opts.activation_enabled is not None
        else os.environ.get(ACTIVATION_ENV) == "1"
    )
    live_loop = (
        opts.live_loop_enabled
        if opts.live_loop_enabled is not None
        else os.environ.get(LIVE_LOOP_ENV) == "1"
    )
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
            secrets_ready=secrets_ready,
            activation_enabled=activation,
            last_committed_at=finished_at,
            connected=None,
            now=current,
            stale_after=opts.stale_after,
        ),
    )
    gate_open = production_activation_allowed(
        secrets_ready=secrets_ready,
        owner_gate_open=opts.owner_gate_open,
    )
    notes: list[str] = [
        "Public API readiness is independent of telegram-worker freshness.",
        f"Compose profile `{COMPOSE_PROFILE}` is disabled by default.",
    ]
    if not secrets_ready:
        notes.append("Telegram worker secrets are missing or not mode 0600 (B-003).")
    if not activation:
        notes.append(f"Set {ACTIVATION_ENV}=1 only after owner activation approval.")
    if reconciliation.unexplained:
        notes.append("Live checkpoint is ahead of persisted source messages.")
    return TelegramWorkerStatus(
        compose_profile=COMPOSE_PROFILE,
        activation_env=ACTIVATION_ENV,
        activation_enabled=activation,
        live_loop_enabled=live_loop,
        secrets_ready=secrets_ready,
        secret_files=secret_files,
        freshness=freshness,
        stale_after_seconds=int(opts.stale_after.total_seconds()),
        last_live_run_finished_at=finished_at,
        last_live_checkpoint_external_id=live_checkpoint,
        max_persisted_external_id=max_id,
        reconciliation=reconciliation,
        production_activation_gate_open=gate_open,
        notes=tuple(notes),
    )


def rotation_rehearsal_report() -> dict[str, object]:
    """Return a JSON-serializable session rotation dry-run checklist."""
    return {
        "mode": "dry_run",
        "steps": [asdict(step) for step in session_rotation_rehearsal_steps()],
        "note": (
            "Do not rotate in production until secrets exist and the worker profile is approved."
        ),
    }
