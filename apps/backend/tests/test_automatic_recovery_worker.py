"""Optional recovery maintenance activation, live priority and failure isolation."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from wef_backend.automatic_recovery_worker import maintain_automatic_recovery
from wef_backend.settings import Settings


@pytest.mark.parametrize("enabled", [False, True])
async def test_worker_activation_and_single_bounded_tick(
    monkeypatch: pytest.MonkeyPatch, *, enabled: bool
) -> None:
    owner = uuid4()
    settings = Settings(
        ai_recovery_enabled=enabled,
        ai_recovery_activation_verified=True,
        ai_curation_enabled=True,
        groq_zdr_verified=True,
        groq_api_key=SecretStr("fixture"),
        ai_recovery_owner_id=owner,
    )
    stop = asyncio.Event()
    session = AsyncMock()
    session.scalar.side_effect = [owner, None]

    # session_factory() is a synchronous constructor for an async context manager.
    class Sessions:
        def __call__(self) -> AsyncMock:
            return session

    session.__aenter__.return_value = session
    admin = SimpleNamespace(
        generate_ingestion_ai_parse=AsyncMock(),
        apply_ingestion_ai_parse=AsyncMock(),
        start_offer_enrichment=AsyncMock(),
        process_offer_enrichment=AsyncMock(),
    )
    services = SimpleNamespace(admin=admin, close=AsyncMock())
    monkeypatch.setattr("wef_backend.automatic_recovery_worker.build_services", lambda _: services)
    backfill = AsyncMock()
    monkeypatch.setattr("wef_backend.automatic_recovery_worker.backfill_parse_issues", backfill)
    tick = AsyncMock()
    monkeypatch.setattr(
        "wef_backend.automatic_recovery_worker.AutomaticRecovery",
        lambda *_: SimpleNamespace(tick=tick),
    )

    async def wait_once(awaitable: object, *, timeout: int) -> None:  # noqa: ASYNC109
        assert timeout == 60
        stop.set()
        await awaitable  # type: ignore[misc]

    monkeypatch.setattr("wef_backend.automatic_recovery_worker.asyncio.wait_for", wait_once)
    await maintain_automatic_recovery(settings, Sessions(), stop, lambda: True)  # type: ignore[arg-type]
    assert tick.await_count == int(enabled)
    assert backfill.await_count == int(enabled)
    assert services.close.await_count == int(enabled)
