"""Runtime configuration, encryption and operational diagnostics fail safely."""

from __future__ import annotations

import base64
import sys
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr
from sqlalchemy.exc import SQLAlchemyError

from tests.test_ingestion_persistence_boundaries import _factory
from tests.test_runtime import FakeGeocoderTransport
from wef_backend import composition, geocoder_check, openapi_export
from wef_backend import settings as configuration
from wef_backend.features.contacts.application.reveal import ContactCryptoUnavailableError
from wef_backend.features.contacts.infrastructure.crypto import (
    AesGcmContactCipher,
    decode_secret_key,
)
from wef_backend.features.identity.infrastructure import security
from wef_backend.features.ingestion.infrastructure.media_staging import (
    MediaStaging,
    MediaStagingDeferredError,
)
from wef_backend.logging_config import scrub_log_value
from wef_backend.settings import Settings

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("material", ["ż", "a", "%%%a"])
def test_contact_key_decode_errors_are_typed(material: str) -> None:
    with pytest.raises(ContactCryptoUnavailableError, match="32-byte hex or url-safe base64"):
        decode_secret_key(material)


def test_contact_key_accepts_unpadded_base64_and_missing_decryption_key_is_typed() -> None:
    key = bytes(range(32))
    assert decode_secret_key(base64.urlsafe_b64encode(key).decode().rstrip("=")) == key
    cipher = AesGcmContactCipher(encryption_key=None, hmac_key=None)
    with pytest.raises(ContactCryptoUnavailableError, match="encryption key is unavailable"):
        cipher.decrypt("irrelevant")


@pytest.mark.parametrize("denied", [False, True])
def test_memory_throttle_prunes_oldest_stale_keys_without_dropping_live_hits(
    *,
    denied: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(security, "_MAX_TRACKED_KEYS", 2)
    limiter = security.MemoryRateLimiter()
    old = datetime.now(UTC) - timedelta(days=2)
    limiter._hits.update({"old-1": [old], "old-2": [], "active": [datetime.now(UTC)]})  # noqa: SLF001
    assert limiter.allow("active", limit=1 if denied else 2, window_seconds=60) is not denied
    assert "old-1" not in limiter._hits  # noqa: SLF001
    assert "old-2" in limiter._hits  # noqa: SLF001
    assert len(limiter._hits["active"]) == (1 if denied else 2)  # noqa: SLF001


def test_memory_throttle_prune_preserves_all_live_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, "_MAX_TRACKED_KEYS", 1)
    limiter = security.MemoryRateLimiter()
    assert limiter.allow("first", limit=1, window_seconds=60)
    assert limiter.allow("second", limit=1, window_seconds=60)
    assert not limiter.allow("first", limit=1, window_seconds=60)


@pytest.mark.parametrize("root_marker", [False, True])
def test_dotenv_search_handles_missing_root_and_deduplicates_cwd(
    *,
    root_marker: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(configuration, "__file__", str(tmp_path / "src" / "settings.py"))
    (tmp_path / ".env").write_text("SYNTHETIC=fixture\n")
    if root_marker:
        (tmp_path / "AGENTS.md").write_text("fixture")
    load = MagicMock()
    monkeypatch.setattr("dotenv.load_dotenv", load)
    configuration._load_dotenv_files()  # noqa: SLF001
    load.assert_called_once_with(tmp_path / ".env", override=False)


def test_dotenv_optional_dependency_can_be_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setitem(sys.modules, "dotenv", None)
    configuration._load_dotenv_files()  # noqa: SLF001


async def test_production_composition_requires_admin_session_secret() -> None:
    with pytest.raises(RuntimeError, match="ADMIN_SESSION_SECRET is required"):
        composition.build_services(Settings(env="production"))


async def test_readiness_database_error_returns_false_and_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock(scalar=AsyncMock(side_effect=SQLAlchemyError("synthetic unavailable")))
    engine = MagicMock(dispose=AsyncMock())
    monkeypatch.setattr(
        composition,
        "create_database_resources",
        lambda _: MagicMock(session_factory=_factory(session), engine=engine),
    )
    services = composition.build_services(Settings())
    try:
        assert not await services.is_ready()
    finally:
        await services.close()
    engine.dispose.assert_awaited_once_with()


async def test_geocoder_readiness_rejects_an_unusable_response() -> None:
    with pytest.raises(geocoder_check.GeoapifyCheckError, match="connectivity check failed"):
        await geocoder_check.check_geoapify(
            Settings(geoapify_api_key=SecretStr("fixture-secret-key-0123456789")),
            transport=FakeGeocoderTransport({"features": []}),
        )


@pytest.mark.parametrize("outcome", ["success", "typed", "unexpected"])
def test_geocoder_cli_output_is_bounded_and_hides_unexpected_error_details(
    outcome: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = (
        geocoder_check.GeoapifyCheckError("safe check refusal")
        if outcome == "typed"
        else RuntimeError("private credential")
    )
    check = AsyncMock(
        return_value={"status": "ok"}, side_effect=error if outcome != "success" else None
    )
    monkeypatch.setattr(geocoder_check, "check_geoapify", check)
    monkeypatch.setattr(geocoder_check, "load_settings", Settings)
    if outcome == "success":
        geocoder_check.main()
        assert capsys.readouterr().out == '{"status": "ok"}\n'
    else:
        with pytest.raises(SystemExit) as caught:
            geocoder_check.main()
        assert caught.value.code == 2
        expected = "safe check refusal" if outcome == "typed" else "Geoapify check failed"
        assert capsys.readouterr().err == expected + "\n"


def test_openapi_cli_invokes_deterministic_export(monkeypatch: pytest.MonkeyPatch) -> None:
    export = MagicMock()
    monkeypatch.setattr(openapi_export, "export_openapi", export)
    openapi_export.main()
    export.assert_called_once_with()


def test_log_scrubber_recurses_lists_and_preserves_scalar_values() -> None:
    assert scrub_log_value([{"value": "token=private"}, 7, None]) == [
        {"value": "token=***"},
        7,
        None,
    ]


def test_staging_closed_write_and_directory_cleanup_failure_preserve_reservations(
    tmp_path: Path,
) -> None:
    staging = MediaStaging(tmp_path, reserve=0)
    lease = staging.acquire(1, 20)
    with pytest.raises(MediaStagingDeferredError, match="lease is closed"):
        lease.write(b"data")
    lease.open(".jpg").write(b"retained")
    lease.flush()
    lease.close()
    lease.flush()
    (tmp_path / "1" / "unowned.txt").write_text("preserved")
    lease.release()
    assert (tmp_path / "1" / "unowned.txt").read_text() == "preserved"
    assert not (tmp_path / "1" / "0.jpg").exists()
    staging.acquire(1, 20).release()
