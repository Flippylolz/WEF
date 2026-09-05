"""Unit tests for E8-T2 Telegram secrets, entity verify, and fake backfill."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest
from telethon.errors import FloodWaitError

from wef_backend.features.ingestion.application.persistence import (
    DeletionOutcomeKind,
    MessageOutcome,
    MessagePersistOutcome,
    PersistableMessage,
    PersistenceBatchError,
    RunCheckpoint,
    RunCounts,
    RunLockHeldError,
    RunMode,
    RunStatus,
    SourceDeletionOutcome,
)
from wef_backend.features.ingestion.application.telegram_backfill import (
    LiveBackfillRequest,
    LiveTelegramBackfill,
)
from wef_backend.features.ingestion.application.telegram_events import (
    LiveEventHandlerError,
    LiveEventQueue,
)
from wef_backend.features.ingestion.application.telegram_live import (
    LiveTelegramMessage,
    TelegramChannelEntity,
    TelegramEntityMismatchError,
    live_message_to_raw,
    source_identity_from_channel,
    verify_channel_entity,
)
from wef_backend.features.ingestion.domain.telegram_channel import (
    default_live_channel_identity,
)
from wef_backend.features.ingestion.domain.telegram_secrets import (
    TelegramLoginCodeError,
    TelegramSecretError,
    TelegramWorkerSecrets,
    load_telegram_worker_secrets,
    persist_telegram_session,
)
from wef_backend.features.ingestion.infrastructure import telethon_client as telethon_module
from wef_backend.features.ingestion.infrastructure.fake_telegram_client import (
    FakeTelegramLiveClient,
)
from wef_backend.features.ingestion.infrastructure.telethon_client import _to_live_message

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
    from pathlib import Path
    from uuid import UUID

    from wef_backend.features.ingestion.domain.extraction import ListingCandidate


def test_load_telegram_worker_secrets_from_env_values() -> None:
    secrets = load_telegram_worker_secrets(
        api_id=12345,
        api_hash="hash-value",
        session="session-string",
    )
    assert secrets.api_id == 12345
    assert secrets.api_hash == "hash-value"
    assert secrets.session == "session-string"


def test_load_telegram_worker_secrets_allows_empty_session() -> None:
    secrets = load_telegram_worker_secrets(api_id=1, api_hash="hash", session="")
    assert secrets.session == ""


def test_load_telegram_worker_secrets_rejects_bad_api_id() -> None:
    with pytest.raises(TelegramSecretError, match="positive integer"):
        load_telegram_worker_secrets(api_id=None, api_hash="hash", session="session")
    with pytest.raises(TelegramSecretError, match="positive integer"):
        load_telegram_worker_secrets(api_id=0, api_hash="hash", session="session")


def test_load_telegram_worker_secrets_rejects_empty_hash() -> None:
    with pytest.raises(TelegramSecretError, match="api_hash"):
        load_telegram_worker_secrets(api_id=1, api_hash="  ", session="session")


def test_load_telegram_worker_secrets_reads_session_path(tmp_path: Path) -> None:
    session_path = tmp_path / "session"
    session_path.write_text("from-file", encoding="utf-8")
    secrets = load_telegram_worker_secrets(
        api_id=1,
        api_hash="hash",
        session=None,
        session_path=session_path,
    )
    assert secrets.session == "from-file"


def test_persist_telegram_session_writes_env_and_path(tmp_path: Path) -> None:
    session_path = tmp_path / "nested" / "session"
    env_file = tmp_path / ".env"
    env_file.write_text("WEF_ENV=development\nWEF_TELEGRAM_SESSION=old\n", encoding="utf-8")
    persist_telegram_session("generated-session", session_path=session_path, env_file=env_file)
    assert session_path.read_text(encoding="utf-8") == "generated-session"
    assert "WEF_TELEGRAM_SESSION=generated-session" in env_file.read_text(encoding="utf-8")
    assert "WEF_ENV=development" in env_file.read_text(encoding="utf-8")
    assert oct(session_path.stat().st_mode & 0o777) == "0o600"


def test_verify_channel_entity_rejects_mismatches() -> None:
    expected = default_live_channel_identity()
    with pytest.raises(TelegramEntityMismatchError, match="channel id"):
        verify_channel_entity(
            expected,
            TelegramChannelEntity(
                username=expected.username,
                channel_id="999",
                title=expected.channel_title,
            ),
        )
    with pytest.raises(TelegramEntityMismatchError, match="username"):
        verify_channel_entity(
            expected,
            TelegramChannelEntity(
                username="other",
                channel_id=expected.channel_id,
                title=expected.channel_title,
            ),
        )
    with pytest.raises(TelegramEntityMismatchError, match="title"):
        verify_channel_entity(
            expected,
            TelegramChannelEntity(
                username=expected.username,
                channel_id=expected.channel_id,
                title="Other Title",
            ),
        )


def test_live_message_to_raw_builds_checksum() -> None:
    identity = source_identity_from_channel(default_live_channel_identity())
    published = datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC)
    edited = datetime(2024, 1, 2, 4, 4, 5, tzinfo=UTC)
    raw = live_message_to_raw(
        LiveTelegramMessage(
            external_message_id=42,
            text="Cena: 5000 PLN, 2 pokoje, Mokotów",
            published_at=published,
            edited_at=edited,
            media_group_id="album-1",
        ),
        identity=identity,
    )
    assert raw.external_message_id == 42
    assert len(raw.checksum) == 64
    assert raw.text.startswith("Cena:")
    assert raw.edited_at == edited
    assert raw.media_group_id == "album-1"


class _FakeStore:
    """Minimal persistence port for restartable/idempotent backfill tests."""

    def __init__(self) -> None:
        self.messages: dict[int, PersistableMessage] = {}
        self.checkpoints: list[RunCheckpoint] = []
        self.runs: list[tuple[UUID, RunMode, RunStatus]] = []
        self.lock_held = False

    @asynccontextmanager
    async def run_lock(self, source_key: str) -> AsyncIterator[None]:
        if self.lock_held:
            raise RunLockHeldError(source_key)
        self.lock_held = True
        try:
            yield
        finally:
            self.lock_held = False

    async def ensure_channel(
        self,
        *,
        platform: str,
        external_id: str,
        display_name: str,
    ) -> UUID:
        _ = (platform, external_id, display_name)
        return uuid4()

    async def start_run(
        self,
        *,
        channel_id: UUID,
        mode: RunMode,
        parser_version: str,
        source_checksum: str | None,
        release_sha: str | None,
    ) -> UUID:
        _ = (channel_id, parser_version, source_checksum, release_sha)
        run_id = uuid4()
        self.runs.append((run_id, mode, RunStatus.RUNNING))
        return run_id

    async def persist_batch(
        self,
        *,
        channel_id: UUID,
        run_id: UUID,
        batch: Sequence[tuple[PersistableMessage, int]],
        checkpoint: RunCheckpoint,
        counts: RunCounts,
    ) -> tuple[Sequence[MessagePersistOutcome], RunCheckpoint, RunCounts, int]:
        _ = (channel_id, run_id)
        outcomes: list[MessagePersistOutcome] = []
        acknowledged = checkpoint
        acknowledged_counts = counts
        for persistable, source_index in batch:
            existing = self.messages.get(persistable.raw.external_message_id)
            if existing is None:
                outcome = MessageOutcome.CREATED
                self.messages[persistable.raw.external_message_id] = persistable
            elif existing.raw.checksum == persistable.raw.checksum:
                outcome = MessageOutcome.UNCHANGED
            else:
                outcome = MessageOutcome.REVISED
                self.messages[persistable.raw.external_message_id] = persistable
            message_outcome = MessagePersistOutcome(
                external_message_id=persistable.raw.external_message_id,
                outcome=outcome,
                revision_number=1,
            )
            outcomes.append(message_outcome)
            acknowledged = acknowledged.advances(source_index, persistable.raw.checksum)
            acknowledged_counts = acknowledged_counts.with_outcome(
                outcome=message_outcome,
                offer_created=outcome is MessageOutcome.CREATED,
            )
        self.checkpoints.append(acknowledged)
        return outcomes, acknowledged, acknowledged_counts, 0

    async def persist_live_upsert(
        self,
        *,
        channel_id: UUID,
        run_id: UUID,
        message: PersistableMessage,
        checkpoint: RunCheckpoint,
        counts: RunCounts,
        advance_checkpoint: bool,
    ) -> tuple[MessagePersistOutcome, RunCheckpoint, RunCounts, int]:
        outcomes, acknowledged, acknowledged_counts, offers = await self.persist_batch(
            channel_id=channel_id,
            run_id=run_id,
            batch=((message, message.raw.external_message_id),),
            checkpoint=checkpoint,
            counts=counts,
        )
        if not advance_checkpoint:
            acknowledged = checkpoint
        return outcomes[0], acknowledged, acknowledged_counts, offers

    async def mark_source_deleted(
        self,
        *,
        channel_id: UUID,
        external_message_ids: Sequence[int],
        archive_event_ids: dict[int, UUID] | None = None,  # noqa: ARG002 - protocol parity
    ) -> Sequence[SourceDeletionOutcome]:
        _ = channel_id
        return tuple(
            SourceDeletionOutcome(
                external_message_id=external_id,
                outcome=DeletionOutcomeKind.MISSING,
                offers_hidden=0,
            )
            for external_id in external_message_ids
        )

    async def persist_owner_ai_listing(
        self,
        *,
        source_message_revision_id: UUID,
        listing: ListingCandidate,
    ) -> UUID:
        """Stub owner AI listing persistence for protocol conformance."""
        _ = (source_message_revision_id, listing)
        return uuid4()

    async def finish_run(
        self,
        *,
        run_id: UUID,
        status: RunStatus,
        counts: RunCounts,
        checkpoint: RunCheckpoint,
        error_summary: str | None,
    ) -> None:
        _ = (counts, checkpoint, error_summary)
        self.runs.append((run_id, RunMode.LIVE, status))


def _listing_messages() -> tuple[LiveTelegramMessage, ...]:
    base = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
    texts = (
        "Cena: 4500 PLN, 2 pokoje, Mokotów ul. Puławska",
        "Cena: 5200 PLN, 3 pokoje, Wilanów",
        "Hello world not a listing",
        "Cena: 6100 PLN, 1 pokój, Śródmieście",
    )
    return tuple(
        LiveTelegramMessage(
            external_message_id=index,
            text=text,
            published_at=base,
            edited_at=None,
        )
        for index, text in enumerate(texts, start=10)
    )


def test_telethon_message_adapter_maps_fields() -> None:
    published = datetime(2024, 2, 3, 4, 5, 6, tzinfo=UTC)
    live = _to_live_message(
        SimpleNamespace(
            id=99,
            message="hello",
            text=None,
            date=published,
            edit_date=None,
            grouped_id=123,
        ),
    )
    assert live.external_message_id == 99
    assert live.text == "hello"
    assert live.media_group_id == "123"
    assert live.published_at == published


def test_telethon_message_adapter_rejects_missing_date() -> None:
    with pytest.raises(TypeError, match="published timestamp"):
        _to_live_message(SimpleNamespace(id=1, message="x", date=None, edit_date=None))


def test_telethon_message_adapter_normalizes_naive_dates() -> None:
    published = datetime(2024, 2, 3, 4, 5, 6)  # noqa: DTZ001 — intentional naive input
    edited = datetime(2024, 2, 3, 5, 5, 6)  # noqa: DTZ001 — intentional naive input
    live = _to_live_message(
        SimpleNamespace(
            id=7,
            message=None,
            text="body",
            date=published,
            edit_date=edited,
            grouped_id=None,
        ),
    )
    assert live.text == "body"
    assert live.published_at.tzinfo is UTC
    assert live.edited_at is not None
    assert live.edited_at.tzinfo is UTC
    assert live.media_group_id is None


@pytest.mark.asyncio
async def test_fake_client_error_paths() -> None:
    identity = default_live_channel_identity()
    client = FakeTelegramLiveClient(
        entity=TelegramChannelEntity(
            username=identity.username,
            channel_id=identity.channel_id,
            title=identity.channel_title,
        ),
        messages=(),
    )
    with pytest.raises(RuntimeError, match="not connected"):
        async for _ in client.iter_messages(username=identity.username, min_id=0):
            pass
    await client.connect()
    with pytest.raises(LookupError, match="username"):
        await client.resolve_channel("missing")
    with pytest.raises(LookupError, match="username"):
        async for _ in client.iter_messages(username="missing", min_id=0):
            pass
    await client.disconnect()


class _FakeTelethon:
    """Minimal Telethon stand-in for flood-wait unit tests."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self._authorized = True
        self.flood_on_entity = False
        self.flood_on_iter = False
        self.session = SimpleNamespace(save=lambda: "session")
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def is_user_authorized(self) -> bool:
        return self._authorized

    async def get_entity(self, username: str) -> SimpleNamespace:
        if self.flood_on_entity:
            self.flood_on_entity = False
            raise FloodWaitError(request=None, capture=2)
        return SimpleNamespace(
            id=2180077318,
            title="El Estate | Покупка Варшава",
            username=username,
        )

    def iter_messages(self, *_args: object, **_kwargs: object) -> object:
        async def _gen() -> AsyncIterator[SimpleNamespace]:
            if self.flood_on_iter:
                self.flood_on_iter = False
                raise FloodWaitError(request=None, capture=1)
            yield SimpleNamespace(
                id=10,
                message="hi",
                text=None,
                date=datetime(2024, 1, 1, tzinfo=UTC),
                edit_date=None,
                grouped_id=None,
            )

        return _gen()


@pytest.mark.asyncio
async def test_telethon_live_client_resolve_waits_on_flood(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(telethon_module, "TelegramClient", _FakeTelethon)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)

    async def _sleep(seconds: float) -> None:
        sleeps.append(seconds)

    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session="session"),
        sleep=_sleep,
    )
    client._client.flood_on_entity = True  # noqa: SLF001
    assert client.is_connected() is False
    await client.connect()
    assert client.is_connected() is True
    entity = await client.resolve_channel("elestate_warszawa")
    assert entity.channel_id == "2180077318"
    assert sleeps == [2]
    await client.disconnect()


@pytest.mark.asyncio
async def test_telethon_live_client_iter_waits_on_flood(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(telethon_module, "TelegramClient", _FakeTelethon)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)

    async def _sleep(seconds: float) -> None:
        sleeps.append(seconds)

    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session="session"),
        sleep=_sleep,
    )
    client._client.flood_on_iter = True  # noqa: SLF001
    await client.connect()
    messages = [item async for item in client.iter_messages(username="elestate_warszawa", min_id=0)]
    assert len(messages) == 1
    assert sleeps == [1]
    await client.disconnect()


@pytest.mark.asyncio
async def test_telethon_live_client_observes_remote_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(telethon_module, "TelegramClient", _FakeTelethon)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session="session"),
    )
    await client.connect()
    assert await client.latest_message_id("elestate_warszawa") == 10
    await client.disconnect()


@pytest.mark.asyncio
async def test_telethon_live_client_generates_session_with_login_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _LoginClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.session = SimpleNamespace(save=lambda: "generated")
            self._authorized = False
            self.signed_in: list[str] = []

        def is_connected(self) -> bool:
            return True

        async def connect(self) -> None:
            return None

        async def is_user_authorized(self) -> bool:
            return self._authorized

        async def sign_in(self, phone: str, code: str) -> None:
            self.signed_in.append(f"{phone}:{code}")
            self._authorized = True

    monkeypatch.setattr(telethon_module, "TelegramClient", _LoginClient)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session=""),
    )
    await client.connect()
    session = await client.ensure_authorized(phone="+48111", login_code="12345")
    assert session == "generated"


@pytest.mark.asyncio
async def test_telethon_live_client_requests_login_code_without_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Pending:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.session = SimpleNamespace(save=lambda: "")
            self.code_requested = False

        def is_connected(self) -> bool:
            return True

        async def connect(self) -> None:
            return None

        async def is_user_authorized(self) -> bool:
            return False

        async def send_code_request(self, phone: str) -> None:
            assert phone == "+48111"
            self.code_requested = True

    monkeypatch.setattr(telethon_module, "TelegramClient", _Pending)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session=""),
    )
    await client.connect()
    with pytest.raises(TelegramLoginCodeError, match="login code sent"):
        await client.ensure_authorized(phone="+48111")


@pytest.mark.asyncio
async def test_telethon_live_client_requires_phone_when_unauthorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Unauthorized:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        def is_connected(self) -> bool:
            return True

        async def connect(self) -> None:
            return None

        async def is_user_authorized(self) -> bool:
            return False

    monkeypatch.setattr(telethon_module, "TelegramClient", _Unauthorized)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session=""),
    )
    await client.connect()
    with pytest.raises(TelegramSecretError, match="WEF_TELEGRAM_PHONE"):
        await client.ensure_authorized()


@pytest.mark.asyncio
async def test_telethon_live_client_sign_in_uses_2fa_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _NeedPasswordError(Exception):
        pass

    class _Session:
        def save(self) -> str:
            return "sess-2fa"

    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.session = _Session()
            self.authorized = False

        def is_connected(self) -> bool:
            return True

        async def connect(self) -> None:
            return None

        async def is_user_authorized(self) -> bool:
            return self.authorized

        async def sign_in(
            self,
            phone: str | None = None,
            code: str | None = None,
            password: str | None = None,
        ) -> None:
            if password is None:
                assert phone == "+48111"
                assert code == "22222"
                raise _NeedPasswordError
            self.authorized = True

    monkeypatch.setattr(telethon_module, "TelegramClient", _Client)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    monkeypatch.setattr(telethon_module, "SessionPasswordNeededError", _NeedPasswordError)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session=""),
    )
    await client.connect()
    two_factor = "2fa-secret"
    session = await client.ensure_authorized(
        phone="+48111",
        login_code="22222",
        password=two_factor,
    )
    assert session == "sess-2fa"
    assert client.save_session() == "sess-2fa"


@pytest.mark.asyncio
async def test_telethon_live_client_subscribe_registers_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handlers: list[tuple[object, object]] = []

    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        def is_connected(self) -> bool:
            return True

        async def connect(self) -> None:
            return None

        def add_event_handler(self, callback: object, event: object) -> None:
            handlers.append((callback, event))

    monkeypatch.setattr(telethon_module, "TelegramClient", _Client)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session="sess"),
    )
    await client.connect()
    queue = LiveEventQueue()
    client.subscribe_channel("elestate_warszawa", queue)
    assert len(handlers) == 3
    callback = cast("Callable[[object], Awaitable[None]]", handlers[0][0])
    await callback(SimpleNamespace(message=SimpleNamespace(id=1, message="private source")))
    with pytest.raises(LiveEventHandlerError) as captured:
        await queue.get()
    assert captured.value.category == "TypeError"
    assert "private source" not in str(captured.value)


@pytest.mark.asyncio
async def test_fake_backfill_records_failed_run_on_batch_error() -> None:
    identity = default_live_channel_identity()
    client = FakeTelegramLiveClient(
        entity=TelegramChannelEntity(
            username=identity.username,
            channel_id=identity.channel_id,
            title=identity.channel_title,
        ),
        messages=_listing_messages()[:1],
    )
    store = _FakeStore()

    async def _fail_batch(**_kwargs: object) -> object:
        category = "test_failure"
        raise PersistenceBatchError(category)

    store.persist_batch = _fail_batch  # type: ignore[assignment]
    backfill = LiveTelegramBackfill(store=store, client=client)
    with pytest.raises(PersistenceBatchError):
        await backfill(LiveBackfillRequest(identity=identity, overlap=0))
    assert store.runs[-1][2] is RunStatus.FAILED


@pytest.mark.asyncio
async def test_fake_client_respects_limit() -> None:
    identity = default_live_channel_identity()
    client = FakeTelegramLiveClient(
        entity=TelegramChannelEntity(
            username=identity.username,
            channel_id=identity.channel_id,
            title=identity.channel_title,
        ),
        messages=_listing_messages(),
    )
    await client.connect()
    items = [
        item
        async for item in client.iter_messages(
            username=identity.username,
            min_id=0,
            limit=1,
        )
    ]
    assert len(items) == 1


@pytest.mark.asyncio
async def test_fake_backfill_is_restartable_and_idempotent() -> None:
    identity = default_live_channel_identity()
    messages = _listing_messages()
    client = FakeTelegramLiveClient(
        entity=TelegramChannelEntity(
            username=identity.username,
            channel_id=identity.channel_id,
            title=identity.channel_title,
        ),
        messages=messages,
    )
    store = _FakeStore()
    backfill = LiveTelegramBackfill(store=store, client=client)
    first = await backfill(
        LiveBackfillRequest(
            identity=identity,
            resume_after_external_id=0,
            overlap=0,
            batch_size=1,
        ),
    )
    assert first.messages_seen == 4
    assert first.checkpoint_external_message_id == 13
    assert first.created >= 1
    assert len(store.messages) == 4

    second = await backfill(
        LiveBackfillRequest(
            identity=identity,
            resume_after_external_id=first.checkpoint_external_message_id,
            overlap=2,
        ),
    )
    assert second.messages_seen == 2  # overlap only (12, 13)
    assert second.unchanged == 2
    assert second.created == 0
    assert second.checkpoint_external_message_id == 13
    assert len(store.messages) == 4
