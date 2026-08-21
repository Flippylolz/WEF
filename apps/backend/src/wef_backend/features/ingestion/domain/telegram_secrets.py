"""Worker-only Telegram credential loading without echoing secret bytes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_OWNER_READABLE_MODE = 0o600


class TelegramSecretError(RuntimeError):
    """Raised when secret files are missing, unreadable, or wrongly permissioned."""


@dataclass(frozen=True, slots=True)
class TelegramWorkerSecrets:
    """In-memory secret material loaded from mode-0600 worker files."""

    api_id: int
    api_hash: str
    session: str


def load_telegram_worker_secrets(
    *,
    api_id_file: Path,
    api_hash_file: Path,
    session_file: Path,
) -> TelegramWorkerSecrets:
    """Load API ID/hash/session from files; never include contents in exceptions."""
    api_id_text = _read_secret_text(api_id_file, label="api_id")
    api_hash = _read_secret_text(api_hash_file, label="api_hash")
    session = _read_secret_text(session_file, label="session")
    try:
        api_id = int(api_id_text)
    except ValueError as error:
        message = "Telegram api_id file is not a valid integer"
        raise TelegramSecretError(message) from error
    if api_id <= 0:
        message = "Telegram api_id must be a positive integer"
        raise TelegramSecretError(message)
    if not api_hash:
        message = "Telegram api_hash file is empty"
        raise TelegramSecretError(message)
    if not session:
        message = "Telegram session file is empty"
        raise TelegramSecretError(message)
    return TelegramWorkerSecrets(api_id=api_id, api_hash=api_hash, session=session)


def _read_secret_text(path: Path, *, label: str) -> str:
    if not path.is_file():
        message = f"Telegram {label} secret file is missing"
        raise TelegramSecretError(message)
    mode = path.stat().st_mode & 0o777
    if mode != _OWNER_READABLE_MODE:
        message = f"Telegram {label} secret file must be mode 0600"
        raise TelegramSecretError(message)
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as error:
        message = f"Telegram {label} secret file is unreadable"
        raise TelegramSecretError(message) from error
