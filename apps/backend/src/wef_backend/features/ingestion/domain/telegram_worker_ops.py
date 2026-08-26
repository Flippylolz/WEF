"""Telegram worker staleness and checkpoint reconciliation contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

DEFAULT_STALE_AFTER = timedelta(minutes=15)
DEFAULT_HEARTBEAT_MAX_AGE = timedelta(seconds=45)
HEARTBEAT_INTERVAL_SECONDS = 10.0
COMPOSE_SERVICE = "telegram-worker"


class WorkerFreshness(StrEnum):
    """Worker freshness classification (never gates public API readiness)."""

    NEVER_STARTED = "never_started"
    CREDENTIALS_PENDING = "credentials_pending"
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

    credentials_ready: bool
    last_committed_at: datetime | None
    connected: bool | None
    now: datetime
    stale_after: timedelta = DEFAULT_STALE_AFTER


@dataclass(frozen=True, slots=True)
class TelegramWorkerStatus:
    """Redacted operator-facing worker ops report."""

    compose_service: str
    credentials_ready: bool
    session_ready: bool
    freshness: WorkerFreshness
    stale_after_seconds: int
    last_live_run_finished_at: datetime | None
    last_live_checkpoint_external_id: int | None
    max_persisted_external_id: int
    reconciliation: CheckpointReconciliation
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SessionRotationStep:
    """One redacted rotation rehearsal step (dry-run friendly)."""

    order: int
    action: str
    requires_live_secrets: bool


def parse_heartbeat_timestamp(text: str) -> datetime:
    """Parse a heartbeat timestamp; naive values are treated as UTC."""
    stripped = text.strip()
    if not stripped:
        message = "heartbeat is empty"
        raise ValueError(message)
    parsed = datetime.fromisoformat(stripped)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def heartbeat_is_fresh(
    written_at: datetime,
    *,
    now: datetime,
    max_age: timedelta = DEFAULT_HEARTBEAT_MAX_AGE,
) -> bool:
    """Return True when the listen-loop heartbeat is still within max_age."""
    return now.astimezone(UTC) - written_at.astimezone(UTC) <= max_age


def classify_freshness(inputs: FreshnessInput) -> WorkerFreshness:
    """Classify worker freshness without implying API unreadiness."""
    if not inputs.credentials_ready:
        return WorkerFreshness.CREDENTIALS_PENDING
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
            action="Replace WEF_TELEGRAM_SESSION in the env file",
            requires_live_secrets=True,
        ),
        SessionRotationStep(
            order=3,
            action="Run wef-verify-telegram-channel",
            requires_live_secrets=False,
        ),
        SessionRotationStep(
            order=4,
            action="Run bounded wef-telegram-backfill --overlap",
            requires_live_secrets=True,
        ),
        SessionRotationStep(
            order=5,
            action="Start telegram-worker so it generates or loads the string session",
            requires_live_secrets=True,
        ),
        SessionRotationStep(
            order=6,
            action="Revoke the previous Telegram authorization",
            requires_live_secrets=True,
        ),
    )
