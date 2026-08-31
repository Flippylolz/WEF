"""Coverage for env-backed Telegram credentials and in-app session generation."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr

import wef_backend.features.ingestion.infrastructure.telethon_client as telethon_module
from wef_backend import telegram_channel_command, telegram_worker_command
from wef_backend.features.ingestion.application.telegram_events import (
    LiveEventQueue,
    LiveTelegramEvent,
    LiveTelegramEventKind,
)
from wef_backend.features.ingestion.application.telegram_live import TelegramChannelEntity
from wef_backend.features.ingestion.application.telegram_worker_supervision import (
    CriticalWorkerTaskError,
)
from wef_backend.features.ingestion.domain import telegram_secrets as secrets_module
from wef_backend.features.ingestion.domain.telegram_channel import (
    default_live_channel_identity,
)
from wef_backend.features.ingestion.domain.telegram_secrets import (
    TelegramSecretError,
    TelegramWorkerSecrets,
    persist_telegram_session,
    unwrap_secret,
    upsert_env_assignment,
)
from wef_backend.settings import Settings, _load_dotenv_files
from wef_backend.telegram_credentials import secret_text, secrets_from_settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable


def test_unwrap_secret_strips_and_treats_blank_as_missing() -> None:
    assert unwrap_secret(None) is None
    assert unwrap_secret("  ") is None
    assert unwrap_secret(" token ") == "token"


def test_secret_text_supports_secretstr_and_plain_strings() -> None:
    assert secret_text(None) is None
    assert secret_text(SecretStr("from-secret")) == "from-secret"
    assert secret_text("  plain  ") == "plain"
    assert secret_text("   ") is None


def test_secrets_from_settings_maps_env_fields(tmp_path: Path) -> None:
    session_path = tmp_path / "session"
    session_path.write_text("from-path", encoding="utf-8")
    settings = Settings(
        telegram_api_id=12345678,
        telegram_api_hash=SecretStr("0123456789abcdef0123456789abcdef"),
        telegram_session=None,
        telegram_session_path=session_path,
    )
    secrets = secrets_from_settings(settings)
    assert secrets.api_id == 12345678
    assert secrets.session == "from-path"


def test_persist_telegram_session_rejects_empty() -> None:
    with pytest.raises(TelegramSecretError, match="empty Telegram session"):
        persist_telegram_session("  ")


def test_persist_telegram_session_writes_only_requested_targets(tmp_path: Path) -> None:
    session_path = tmp_path / "session"
    env_file = tmp_path / "generated.env"
    persist_telegram_session("sess-file", session_path=session_path)
    persist_telegram_session("sess-env", env_file=env_file)
    assert session_path.read_text(encoding="utf-8") == "sess-file"
    assert "WEF_TELEGRAM_SESSION=sess-env" in env_file.read_text(encoding="utf-8")


def test_upsert_env_assignment_appends_for_new_and_blank_files(tmp_path: Path) -> None:
    missing = tmp_path / "missing.env"
    upsert_env_assignment(missing, "WEF_TELEGRAM_SESSION", "one")
    assert missing.read_text(encoding="utf-8") == "WEF_TELEGRAM_SESSION=one\n"

    trailing = tmp_path / "trailing.env"
    trailing.write_text("WEF_ENV=development\n\n", encoding="utf-8")
    upsert_env_assignment(trailing, "WEF_TELEGRAM_SESSION", "two")
    assert "WEF_TELEGRAM_SESSION=two" in trailing.read_text(encoding="utf-8")

    existing = tmp_path / "existing.env"
    existing.write_text("WEF_ENV=development\n", encoding="utf-8")
    upsert_env_assignment(existing, "WEF_TELEGRAM_SESSION", "three")
    assert existing.read_text(encoding="utf-8").endswith("WEF_TELEGRAM_SESSION=three\n")


def test_read_secret_text_missing_and_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(TelegramSecretError, match="missing"):
        secrets_module._read_secret_text(tmp_path / "absent", label="session")  # noqa: SLF001

    path = tmp_path / "session"
    path.write_text("secret", encoding="utf-8")

    def _boom(_self: Path, *_args: object, **_kwargs: object) -> str:
        message = "unreadable"
        raise OSError(message)

    monkeypatch.setattr(Path, "read_text", _boom)
    with pytest.raises(TelegramSecretError, match="unreadable"):
        secrets_module._read_secret_text(path, label="session")  # noqa: SLF001


def test_load_dotenv_files_skips_under_pytest(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded: list[Path] = []

    def _load(path: Path, **_kwargs: object) -> bool:
        loaded.append(path)
        return False

    monkeypatch.setattr("dotenv.load_dotenv", _load)
    _load_dotenv_files()
    assert loaded == []


def test_load_dotenv_files_reads_cwd_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    loaded: list[Path] = []
    env_file = tmp_path / ".env"
    env_file.write_text("WEF_ENV=development\n", encoding="utf-8")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.chdir(tmp_path)

    def _load(path: Path, **_kwargs: object) -> bool:
        loaded.append(path)
        return False

    monkeypatch.setattr("dotenv.load_dotenv", _load)
    _load_dotenv_files()
    assert env_file in loaded


def test_public_message_url_rejects_non_positive_id() -> None:
    identity = default_live_channel_identity()
    with pytest.raises(ValueError, match="positive integer"):
        identity.public_message_url(0)


def test_telegram_channel_command_reads_session_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_path = tmp_path / "session"
    session_path.write_text("sess", encoding="utf-8")
    monkeypatch.setattr(
        telegram_channel_command,
        "load_settings",
        lambda: Settings(
            telegram_api_id=1,
            telegram_api_hash=SecretStr("hash"),
            telegram_session_path=session_path,
        ),
    )

    async def _ok(_url: str) -> int:
        return 200

    monkeypatch.setattr(telegram_channel_command, "fetch_public_url_status", _ok)
    telegram_channel_command.main()
    assert "public_ok_credentials_present" in capsys.readouterr().out


def test_telegram_channel_command_exits_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _boom() -> dict[str, object]:
        message = "unreachable"
        raise RuntimeError(message)

    monkeypatch.setattr(telegram_channel_command, "run", _boom)
    with pytest.raises(SystemExit) as exited:
        telegram_channel_command.main()
    assert exited.value.code == 2


@pytest.mark.asyncio
async def test_ensure_authorized_connects_and_returns_existing_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.session = SimpleNamespace(save=lambda: "existing")
            self.connected = False

        def is_connected(self) -> bool:
            return self.connected

        async def connect(self) -> None:
            self.connected = True

        async def is_user_authorized(self) -> bool:
            return True

    monkeypatch.setattr(telethon_module, "TelegramClient", _Client)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session="existing"),
    )
    session = await client.ensure_authorized()
    assert session == "existing"


@pytest.mark.asyncio
async def test_ensure_authorized_requires_2fa_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _NeedPasswordError(Exception):
        pass

    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.session = SimpleNamespace(save=lambda: "x")

        def is_connected(self) -> bool:
            return True

        async def connect(self) -> None:
            return None

        async def is_user_authorized(self) -> bool:
            return False

        async def sign_in(self, *_args: object, **_kwargs: object) -> None:
            raise _NeedPasswordError

    monkeypatch.setattr(telethon_module, "TelegramClient", _Client)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    monkeypatch.setattr(telethon_module, "SessionPasswordNeededError", _NeedPasswordError)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session=""),
    )
    await client.connect()
    with pytest.raises(TelegramSecretError, match="WEF_TELEGRAM_2FA_PASSWORD"):
        await client.ensure_authorized(phone="+48111", login_code="11111")


@pytest.mark.asyncio
async def test_ensure_authorized_rejects_failed_sign_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.session = SimpleNamespace(save=lambda: "x")

        def is_connected(self) -> bool:
            return True

        async def connect(self) -> None:
            return None

        async def is_user_authorized(self) -> bool:
            return False

        async def sign_in(self, *_args: object, **_kwargs: object) -> None:
            return None

    monkeypatch.setattr(telethon_module, "TelegramClient", _Client)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session=""),
    )
    await client.connect()
    with pytest.raises(TelegramSecretError, match="did not produce an authorized session"):
        await client.ensure_authorized(phone="+48111", login_code="11111")


@pytest.mark.asyncio
async def test_ensure_authorized_uses_tty_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.session = SimpleNamespace(save=lambda: "tty-session")
            self.started = False

        def is_connected(self) -> bool:
            return True

        async def connect(self) -> None:
            return None

        async def is_user_authorized(self) -> bool:
            return False

        async def start(
            self,
            phone: str | None = None,
            password: str | None = None,
        ) -> None:
            assert phone == "+48111"
            _ = password
            self.started = True

    monkeypatch.setattr(telethon_module, "TelegramClient", _Client)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session=""),
    )
    await client.connect()
    session = await client.ensure_authorized(phone="+48111")
    assert session == "tty-session"


@pytest.mark.asyncio
async def test_resolve_channel_rejects_incomplete_entity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.session = SimpleNamespace(save=lambda: "s")

        def is_connected(self) -> bool:
            return True

        async def connect(self) -> None:
            return None

        async def get_entity(self, username: str) -> SimpleNamespace:
            return SimpleNamespace(id="", title="", username=username)

    monkeypatch.setattr(telethon_module, "TelegramClient", _Client)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session="s"),
    )
    await client.connect()
    with pytest.raises(RuntimeError, match="missing id or title"):
        await client.resolve_channel("elestate_warszawa")


@pytest.mark.asyncio
async def test_subscribe_handlers_enqueue_new_edit_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handlers: list[Callable[[object], Awaitable[None]]] = []

    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        def is_connected(self) -> bool:
            return True

        async def connect(self) -> None:
            return None

        def add_event_handler(
            self,
            callback: Callable[[object], Awaitable[None]],
            _event: object,
        ) -> None:
            handlers.append(callback)

        async def run_until_disconnected(self) -> None:
            return None

        async def iter_messages(self, *_args: object, **_kwargs: object) -> AsyncIterator[object]:
            message = SimpleNamespace(
                id=10,
                message="hi",
                text=None,
                date=datetime(2024, 1, 1, tzinfo=UTC),
                edit_date=None,
                grouped_id=None,
            )
            yield message

    monkeypatch.setattr(telethon_module, "TelegramClient", _Client)
    monkeypatch.setattr(telethon_module, "StringSession", lambda value: value)
    client = telethon_module.TelethonLiveClient(
        TelegramWorkerSecrets(api_id=1, api_hash="hash", session="s"),
    )
    await client.connect()
    queue = LiveEventQueue()
    client.subscribe_channel("elestate_warszawa", queue)
    payload = SimpleNamespace(
        id=10,
        message="hi",
        text=None,
        date=datetime(2024, 1, 1, tzinfo=UTC),
        edit_date=None,
        grouped_id=None,
    )
    await handlers[0](SimpleNamespace(message=payload))
    await handlers[1](SimpleNamespace(message=payload))
    await handlers[2](SimpleNamespace(deleted_ids=(10, 11)))
    await queue.close()
    events = await queue.drain()
    assert [event.kind for event in events] == [
        LiveTelegramEventKind.NEW,
        LiveTelegramEventKind.EDIT,
        LiveTelegramEventKind.DELETE,
    ]
    await client.run_until_disconnected()
    items = [item async for item in client.iter_messages(username="elestate_warszawa", min_id=0)]
    assert len(items) == 1


@pytest.mark.asyncio
async def test_run_telegram_worker_persists_session_and_drains_queue(  # noqa: C901
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    identity = default_live_channel_identity()
    persisted: list[str] = []
    processed: list[int] = []

    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.queue: LiveEventQueue | None = None

        async def connect(self) -> None:
            return None

        async def disconnect(self) -> None:
            return None

        def is_connected(self) -> bool:
            return True

        async def ensure_authorized(self, **_kwargs: object) -> str:
            return "generated-session"

        async def resolve_channel(self, username: str) -> TelegramChannelEntity:
            assert username == identity.username
            return TelegramChannelEntity(
                username=identity.username,
                channel_id=identity.channel_id,
                title=identity.channel_title,
            )

        def subscribe_channel(self, _username: str, queue: LiveEventQueue) -> None:
            self.queue = queue

        async def run_until_disconnected(self) -> None:
            assert self.queue is not None
            await self.queue.put(
                LiveTelegramEvent(
                    kind=LiveTelegramEventKind.DELETE,
                    deleted_ids=(1,),
                ),
            )
            await self.queue.close()

        async def latest_message_id(self, _username: str) -> int:
            return 0

        def iter_messages(self, **_kwargs: object) -> AsyncIterator[object]:
            items: tuple[object, ...] = ()

            async def _empty() -> AsyncIterator[object]:
                for item in items:
                    yield item

            return _empty()

    class _CheckpointStore:
        async def max_external_message_id(self, **_kwargs: object) -> int:
            return 0

        async def latest_live_checkpoint(
            self,
            **_kwargs: object,
        ) -> tuple[int | None, datetime | None]:
            return 0, None

    class _Engine:
        async def dispose(self) -> None:
            return None

    class _Processor:
        def __init__(self, **_kwargs: object) -> None:
            return None

        async def __call__(self, **_kwargs: object) -> SimpleNamespace:
            processed.append(1)
            return SimpleNamespace(checkpoint_external_message_id=0)

    monkeypatch.setattr(telegram_worker_command, "TelethonLiveClient", _Client)
    monkeypatch.setattr(telegram_worker_command, "create_async_engine", lambda _url: _Engine())
    monkeypatch.setattr(
        telegram_worker_command,
        "async_sessionmaker",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        telegram_worker_command,
        "SQLAlchemyIngestionPersistence",
        lambda _factory, **_kwargs: object(),
    )
    monkeypatch.setattr(
        telegram_worker_command,
        "SQLAlchemyTelegramWorkerStatusStore",
        lambda _factory: _CheckpointStore(),
    )
    monkeypatch.setattr(telegram_worker_command, "LiveTelegramEventProcessor", _Processor)
    monkeypatch.setattr(
        telegram_worker_command,
        "persist_telegram_session",
        lambda session, **_kwargs: persisted.append(session),
    )
    monkeypatch.setattr(
        telegram_worker_command,
        "load_settings",
        lambda: Settings(
            telegram_api_id=1,
            telegram_api_hash=SecretStr("hash"),
            telegram_session_path=tmp_path / "session",
            telegram_env_file=tmp_path / ".env",
            telegram_heartbeat_path=tmp_path / "heartbeat",
            telegram_runtime_health_path=tmp_path / "health.json",
        ),
    )
    monkeypatch.setattr(
        telegram_worker_command,
        "secrets_from_settings",
        lambda _settings: TelegramWorkerSecrets(api_id=1, api_hash="hash", session=""),
    )
    with pytest.raises(CriticalWorkerTaskError) as captured:
        await telegram_worker_command.run_telegram_worker()
    assert captured.value.stage == "transport"
    assert captured.value.category == "UnexpectedTaskExit"
    assert persisted == ["generated-session"]
    assert processed == [1]


@pytest.mark.asyncio
async def test_run_telegram_worker_ignores_persist_oserror(  # noqa: C901
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    identity = default_live_channel_identity()

    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.queue: LiveEventQueue | None = None

        async def connect(self) -> None:
            return None

        async def disconnect(self) -> None:
            return None

        def is_connected(self) -> bool:
            return True

        async def ensure_authorized(self, **_kwargs: object) -> str:
            return "generated-session"

        async def resolve_channel(self, _username: str) -> TelegramChannelEntity:
            return TelegramChannelEntity(
                username=identity.username,
                channel_id=identity.channel_id,
                title=identity.channel_title,
            )

        def subscribe_channel(self, _username: str, queue: LiveEventQueue) -> None:
            self.queue = queue

        async def run_until_disconnected(self) -> None:
            assert self.queue is not None
            await self.queue.close()

        async def latest_message_id(self, _username: str) -> int:
            return 0

        def iter_messages(self, **_kwargs: object) -> AsyncIterator[object]:
            items: tuple[object, ...] = ()

            async def _empty() -> AsyncIterator[object]:
                for item in items:
                    yield item

            return _empty()

    class _CheckpointStore:
        async def max_external_message_id(self, **_kwargs: object) -> int:
            return 0

        async def latest_live_checkpoint(
            self,
            **_kwargs: object,
        ) -> tuple[int | None, datetime | None]:
            return 0, None

    class _Engine:
        async def dispose(self) -> None:
            return None

    def _persist(*_args: object, **_kwargs: object) -> None:
        message = "readonly"
        raise OSError(message)

    monkeypatch.setattr(telegram_worker_command, "TelethonLiveClient", _Client)
    monkeypatch.setattr(telegram_worker_command, "create_async_engine", lambda _url: _Engine())
    monkeypatch.setattr(
        telegram_worker_command,
        "async_sessionmaker",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        telegram_worker_command,
        "SQLAlchemyIngestionPersistence",
        lambda _factory, **_kwargs: object(),
    )
    monkeypatch.setattr(
        telegram_worker_command,
        "SQLAlchemyTelegramWorkerStatusStore",
        lambda _factory: _CheckpointStore(),
    )
    monkeypatch.setattr(
        telegram_worker_command,
        "LiveTelegramEventProcessor",
        lambda **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(telegram_worker_command, "persist_telegram_session", _persist)
    monkeypatch.setattr(
        telegram_worker_command,
        "load_settings",
        lambda: Settings(
            telegram_api_id=1,
            telegram_api_hash=SecretStr("hash"),
            telegram_heartbeat_path=tmp_path / "heartbeat",
            telegram_runtime_health_path=tmp_path / "health.json",
        ),
    )
    monkeypatch.setattr(
        telegram_worker_command,
        "secrets_from_settings",
        lambda _settings: TelegramWorkerSecrets(api_id=1, api_hash="hash", session=""),
    )
    with pytest.raises(CriticalWorkerTaskError) as captured:
        await telegram_worker_command.run_telegram_worker()
    assert captured.value.stage == "transport"
    assert captured.value.category == "UnexpectedTaskExit"
