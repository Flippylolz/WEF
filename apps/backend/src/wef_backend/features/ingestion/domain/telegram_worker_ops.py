"""Telegram worker activation, staleness, and checkpoint reconciliation contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wef_backend.features.ingestion.domain.telegram_channel import SecretFileStatus

DEFAULT_STALE_AFTER = timedelta(minutes=15)
ACTIVATION_ENV = "WEF_TELEGRAM_WORKER_ACTIVATE"
LIVE_LOOP_ENV = "WEF_TELEGRAM_WORKER_LIVE_LOOP"
COMPOSE_PROFILE = "telegram-worker"


class WorkerFreshness(StrEnum):
    """Worker freshness classification (never gates public API readiness)."""

    NEVER_STARTED = "never_started"
    SECRETS_PENDING = "secrets_pending"
    ACTIVATION_CLOSED = "activation_closed"
    FRESH = "fresh"
    STALE = "stale"
    DISCONNECTED = "disconnected"


class ReconciliationStatus(StrEnum):
    """Export vs live checkpoint reconciliation outcome."""

    ALIGNED = "aligned"
    LIVE_BEHIND = "live_behind"
    LIVE_AHEAD_UNEXPLAINED = "live_ahead_unexplained"
    NO_SOURCE_DATA = "no_source_data"


@dataclass(frozen=True, slots=True)
class CheckpointReconciliation:
    """Compare durable live cursor to persisted source message ids."""

    channel_id: str
    max_persisted_external_id: int
    live_checkpoint_external_id: int
    status: ReconciliationStatus
    unexplained: bool


@dataclass(frozen=True, slots=True)
class FreshnessInput:
    """Inputs for worker freshness classification."""

    secrets_ready: bool
    activation_enabled: bool
    last_committed_at: datetime | None
    connected: bool | None
    now: datetime
    stale_after: timedelta = DEFAULT_STALE_AFTER


@dataclass(frozen=True, slots=True)
class TelegramWorkerStatus:
    """Redacted operator-facing worker ops report."""

    compose_profile: str
    activation_env: str
    activation_enabled: bool
    live_loop_enabled: bool
    secrets_ready: bool
    secret_files: tuple[SecretFileStatus, ...]
    freshness: WorkerFreshness
    stale_after_seconds: int
    last_live_run_finished_at: datetime | None
    last_live_checkpoint_external_id: int | None
    max_persisted_external_id: int
    reconciliation: CheckpointReconciliation
    production_activation_gate_open: bool
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SessionRotationStep:
    """One redacted rotation rehearsal step (dry-run friendly)."""

    order: int
    action: str
    requires_live_secrets: bool


def classify_freshness(inputs: FreshnessInput) -> WorkerFreshness:
    """Classify worker freshness without implying API unreadiness."""
    if not inputs.secrets_ready:
        return WorkerFreshness.SECRETS_PENDING
    if not inputs.activation_enabled:
        return WorkerFreshness.ACTIVATION_CLOSED
    if inputs.connected is False:
        return WorkerFreshness.DISCONNECTED
    if inputs.last_committed_at is None:
        return WorkerFreshness.NEVER_STARTED
    age = inputs.now - inputs.last_committed_at.astimezone(UTC)
    if age > inputs.stale_after:
        return WorkerFreshness.STALE
    return WorkerFreshness.FRESH


def reconcile_checkpoints(
    *,
    channel_id: str,
    max_persisted_external_id: int,
    live_checkpoint_external_id: int,
) -> CheckpointReconciliation:
    """Explain live cursor vs highest persisted source message id."""
    if max_persisted_external_id <= 0 and live_checkpoint_external_id <= 0:
        status = ReconciliationStatus.NO_SOURCE_DATA
        unexplained = False
    elif live_checkpoint_external_id > max_persisted_external_id:
        status = ReconciliationStatus.LIVE_AHEAD_UNEXPLAINED
        unexplained = True
    elif live_checkpoint_external_id < max_persisted_external_id:
        status = ReconciliationStatus.LIVE_BEHIND
        unexplained = False
    else:
        status = ReconciliationStatus.ALIGNED
        unexplained = False
    return CheckpointReconciliation(
        channel_id=channel_id,
        max_persisted_external_id=max_persisted_external_id,
        live_checkpoint_external_id=live_checkpoint_external_id,
        status=status,
        unexplained=unexplained,
    )


def session_rotation_rehearsal_steps() -> tuple[SessionRotationStep, ...]:
    """Return the ordered session-rotation rehearsal checklist."""
    return (
        SessionRotationStep(
            order=1,
            action="Stop the telegram-worker Compose service",
            requires_live_secrets=False,
        ),
        SessionRotationStep(
            order=2,
            action="Atomically replace the mode-0600 session secret file",
            requires_live_secrets=True,
        ),
        SessionRotationStep(
            order=3,
            action="Run wef-verify-telegram-channel (public + secret paths)",
            requires_live_secrets=False,
        ),
        SessionRotationStep(
            order=4,
            action="Run bounded wef-telegram-backfill --overlap",
            requires_live_secrets=True,
        ),
        SessionRotationStep(
            order=5,
            action="Start telegram-worker with activation gate enabled",
            requires_live_secrets=True,
        ),
        SessionRotationStep(
            order=6,
            action="Revoke the previous Telegram authorization",
            requires_live_secrets=True,
        ),
    )


def production_activation_allowed(*, secrets_ready: bool, owner_gate_open: bool) -> bool:
    """Double-gate production worker enablement (secrets + explicit owner gate)."""
    return secrets_ready and owner_gate_open
