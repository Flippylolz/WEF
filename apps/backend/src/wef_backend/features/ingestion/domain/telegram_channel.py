"""Non-secret Telegram channel identity for live ingestion."""

from __future__ import annotations

from dataclasses import dataclass


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


def default_live_channel_identity() -> TelegramChannelIdentity:
    """Return the verified public WEF channel identity from D-003 / historical import."""
    return TelegramChannelIdentity(
        username="elestate_warszawa",
        channel_id="2180077318",
        channel_title="El Estate | Покупка Варшава",
        message_link_template="https://t.me/elestate_warszawa/{message_id}",
    )
