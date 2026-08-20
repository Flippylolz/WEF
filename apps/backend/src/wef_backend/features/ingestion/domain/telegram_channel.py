"""Non-secret Telegram channel identity and worker secret-path contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_OWNER_READABLE_MODE = 0o600


@dataclass(frozen=True, slots=True)
class TelegramChannelIdentity:
    """Expected public channel identity for live ingestion (non-secret)."""

    username: str
    channel_id: str
    channel_title: str
    message_link_template: str

    def public_channel_url(self) -> str:
        """Return the public t.me channel URL."""
        return f"https://t.me/{self.username}"

    def public_message_url(self, message_id: int) -> str:
        """Return one public message URL for the configured template."""
        if message_id < 1:
            message = "message_id must be a positive integer"
            raise ValueError(message)
        return self.message_link_template.format(message_id=message_id)


@dataclass(frozen=True, slots=True)
class TelegramWorkerSecretPaths:
    """Worker-only secret file locations (paths are not secret; contents are)."""

    api_id_file: Path
    api_hash_file: Path
    session_file: Path

    def required_files(self) -> tuple[Path, Path, Path]:
        """Return the three required secret files in stable order."""
        return (self.api_id_file, self.api_hash_file, self.session_file)


@dataclass(frozen=True, slots=True)
class SecretFileStatus:
    """Redacted presence/mode status for one secret path."""

    path: str
    present: bool
    mode: str | None
    owner_readable_only: bool | None


def inspect_secret_file(path: Path) -> SecretFileStatus:
    """Report presence and mode without reading secret contents."""
    display = str(path)
    if not path.exists():
        return SecretFileStatus(
            path=display,
            present=False,
            mode=None,
            owner_readable_only=None,
        )
    if not path.is_file():
        return SecretFileStatus(
            path=display,
            present=True,
            mode=None,
            owner_readable_only=False,
        )
    mode = path.stat().st_mode & 0o777
    return SecretFileStatus(
        path=display,
        present=True,
        mode=oct(mode),
        owner_readable_only=mode == _OWNER_READABLE_MODE,
    )


def default_live_channel_identity() -> TelegramChannelIdentity:
    """Return the verified public WEF channel identity from D-003 / historical import."""
    return TelegramChannelIdentity(
        username="elestate_warszawa",
        channel_id="2180077318",
        channel_title="El Estate | Покупка Варшава",
        message_link_template="https://t.me/elestate_warszawa/{message_id}",
    )
