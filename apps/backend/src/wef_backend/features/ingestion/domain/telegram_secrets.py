"""Telegram credentials from environment, with in-app session generation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_OWNER_READABLE_MODE = 0o600
_TELEGRAM_SESSION_ENV = "WEF_TELEGRAM_SESSION"


class TelegramSecretError(RuntimeError):
    """Raised when Telegram credentials are missing or invalid."""


class TelegramLoginCodeError(TelegramSecretError):
    """Raised after Telegram sends a login code; restart with WEF_TELEGRAM_LOGIN_CODE."""


@dataclass(frozen=True, slots=True)
class TelegramWorkerSecrets:
    """In-memory Telegram API credentials. Session may be empty until generated."""

    api_id: int
    api_hash: str
    session: str


def unwrap_secret(value: str | None) -> str | None:
    """Return stripped secret text, or None when unset/empty. Never log the value."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def load_telegram_worker_secrets(
    *,
    api_id: int | None,
    api_hash: str | None,
    session: str | None = None,
    session_path: Path | None = None,
) -> TelegramWorkerSecrets:
    """Load API credentials from env values; session may be generated later."""
    if api_id is None or api_id <= 0:
        message = "Telegram api_id must be a positive integer"
        raise TelegramSecretError(message)
    hash_text = (api_hash or "").strip()
    if not hash_text:
        message = "Telegram api_hash is missing"
        raise TelegramSecretError(message)
    session_text = (session or "").strip()
    if not session_text and session_path is not None and session_path.is_file():
        session_text = _read_secret_text(session_path, label="session")
    return TelegramWorkerSecrets(api_id=api_id, api_hash=hash_text, session=session_text)


def persist_telegram_session(
    session: str,
    *,
    session_path: Path | None = None,
    env_file: Path | None = None,
) -> None:
    """Write a generated string session to a 0600 file and/or .env assignment."""
    text = session.strip()
    if not text:
        message = "cannot persist an empty Telegram session"
        raise TelegramSecretError(message)
    if session_path is not None:
        _write_secret_file(session_path, text)
    if env_file is not None:
        upsert_env_assignment(env_file, _TELEGRAM_SESSION_ENV, text)


def credentials_present(*, api_id: int | None, api_hash: str | None) -> bool:
    """Return True when API id/hash are configured (session may still be generated)."""
    return api_id is not None and api_id > 0 and bool(api_hash)


def upsert_env_assignment(path: Path, key: str, value: str) -> None:
    """Replace or append KEY=value in an env file without echoing the value."""
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = existing.splitlines()
    assignment = f"{key}={value}"
    prefix = f"{key}="
    export_prefix = f"export {prefix}"
    replaced = False
    updated: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith((prefix, export_prefix)):
            updated.append(assignment)
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        if updated and updated[-1] != "":
            updated.append(assignment)
        else:
            updated.append(assignment)
    _write_secret_file(path, "\n".join(updated) + "\n")


def _read_secret_text(path: Path, *, label: str) -> str:
    if not path.is_file():
        message = f"Telegram {label} secret file is missing"
        raise TelegramSecretError(message)
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as error:
        message = f"Telegram {label} secret file is unreadable"
        raise TelegramSecretError(message) from error


def _write_secret_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            _OWNER_READABLE_MODE,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        temporary.replace(path)
        path.chmod(_OWNER_READABLE_MODE)
    finally:
        temporary.unlink(missing_ok=True)
