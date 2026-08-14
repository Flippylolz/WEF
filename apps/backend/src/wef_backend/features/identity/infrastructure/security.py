"""Concrete hashing, token, clock, and rate-limit adapters."""

from __future__ import annotations

import hashlib
import secrets
import threading
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from pwdlib import PasswordHash

_RAW_TOKEN_BYTES = 32
_MAX_TRACKED_KEYS = 10_000


class PwdlibPasswordHasher:
    """Argon2 password hashing with pwdlib recommended parameters."""

    def __init__(self) -> None:
        """Configure the Argon2 hasher once."""
        self._hasher = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        """Return one Argon2 hash for an accepted password."""
        return self._hasher.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        """Verify a password against a stored Argon2 hash."""
        return self._hasher.verify(password, hashed)


class SecretsTokenService:
    """Opaque URL-safe tokens persisted only as SHA-256 hashes."""

    def issue(self) -> tuple[str, str]:
        """Return a fresh raw token and its persistable hash."""
        raw = secrets.token_urlsafe(_RAW_TOKEN_BYTES)
        return raw, self.hash(raw)

    def hash(self, raw_token: str) -> str:
        """Hash one raw token for storage or lookup."""
        return hashlib.sha256(raw_token.encode()).hexdigest()


class SystemClock:
    """Production timezone-aware UTC clock."""

    def now(self) -> datetime:
        """Return the current UTC time."""
        return datetime.now(UTC)


class MemoryRateLimiter:
    """Bounded in-process fixed-window throttle without persistence."""

    def __init__(self) -> None:
        """Start with empty windows and no background tasks."""
        self._lock = threading.Lock()
        self._hits: dict[str, list[datetime]] = defaultdict(list)

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Consume one allowance for the key inside the rolling window."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=window_seconds)
        with self._lock:
            hits = [stamp for stamp in self._hits[key] if stamp > cutoff]
            if len(hits) >= limit:
                self._hits[key] = hits
                if len(self._hits) > _MAX_TRACKED_KEYS:
                    self._prune_locked(now)
                return False
            hits.append(now)
            self._hits[key] = hits
            if len(self._hits) > _MAX_TRACKED_KEYS:
                self._prune_locked(now)
            return True

    def _prune_locked(self, now: datetime) -> None:
        """Drop the oldest window entries while holding the lock."""
        stale = [
            key
            for key, hits in self._hits.items()
            if not any(stamp > now - timedelta(days=1) for stamp in hits)
        ]
        for key in stale[: len(stale) // 2]:
            del self._hits[key]
