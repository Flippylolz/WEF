"""Failure classification and bounded retry delays without persistence dependencies."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from wef_backend.features.ingestion.application.persistence import RunLockHeldError
from wef_backend.features.ingestion.domain.telegram_worker_ops import safe_error_category

RETRY_POLICY_VERSION = "archive-retry-v1"
MAX_DATA_FAILURES = 5
MAX_RETRY_SECONDS = 300


@dataclass(frozen=True, slots=True)
class ArchiveFailure:
    """Safe durable retry input; raw exceptions and source payloads stay out of the ledger."""

    kind: Literal["data", "deferred", "systemic"]
    category: str
    retry_after_seconds: float = 0


def classify_archive_failure(error: BaseException) -> ArchiveFailure:
    """Inspect wrapped causes so transport/lock failure never spends the data budget."""
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        category = safe_error_category(current)
        name = type(current).__name__
        if name in {
            "TelegramSecretError",
            "TelegramEntityMismatchError",
            "AuthKeyUnregisteredError",
            "ChannelPrivateError",
        }:
            return ArchiveFailure("systemic", category)
        if isinstance(current, RunLockHeldError | OSError | TimeoutError) or name in {
            "OperationalError",
            "InterfaceError",
            "ConnectionDoesNotExistError",
            "FloodWaitError",
        }:
            delay = getattr(current, "retry_after_seconds", getattr(current, "seconds", 0))
            minimum = float(delay) if isinstance(delay, int | float) and math.isfinite(delay) else 0
            return ArchiveFailure("deferred", category, max(0, minimum))
        current = current.__cause__ or current.__context__
    return ArchiveFailure("data", safe_error_category(error))


def retry_delay(failures: int, jitter: float, minimum: float = 0) -> float:
    """Exponential positive jitter with bounded arithmetic and provider delay floor."""
    base = min(MAX_RETRY_SECONDS, 5 * 2 ** min(max(failures - 1, 0), 6))
    return float(max(min(MAX_RETRY_SECONDS, base * (1 + 0.2 * max(0, min(jitter, 1)))), minimum))
