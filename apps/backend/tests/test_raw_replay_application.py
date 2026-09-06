"""Bounded replay, non-derivable input and failure/cancellation contracts."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

import pytest

from tests.test_listing_extraction import _message
from tests.test_persistence_application import FakeStore
from wef_backend.features.ingestion.application.persistence import PersistenceBatchError
from wef_backend.features.ingestion.application.raw_replay import RawParserReplayer, ReplayWorkItem
from wef_backend.features.ingestion.domain.telegram_channel import default_live_channel_identity

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping, Sequence

    from wef_backend.features.ingestion.domain.model import RawMessage, SourceIdentity

LISTING = "Покупка | Квартира\n📍 ul. Testowa Integracyjna, Wola, Warszawa\nЦена: 900 000 PLN"  # noqa: RUF001


@dataclass
class _Source:
    batches: list[tuple[ReplayWorkItem, ...]]
    excluded: list[frozenset[str]] = field(default_factory=list)

    async def stale_message_events(
        self,
        *,
        parser_version: str,
        sentinel_hash: str,
        limit: int,
        exclude: frozenset[str] = frozenset(),
    ) -> Sequence[ReplayWorkItem]:
        assert parser_version
        assert sentinel_hash
        assert limit == 100
        self.excluded.append(exclude)
        return self.batches.pop(0) if self.batches else ()


def _decode(payload: Mapping[str, object], source: SourceIdentity) -> RawMessage:
    if payload.get("broken"):
        message = "synthetic invalid archive"
        raise ValueError(message)
    return replace(
        _message(str(payload.get("text", LISTING))),
        external_message_id=int(str(payload.get("id", 1))),
        source=source,
    )


class _Store(FakeStore):
    @asynccontextmanager
    async def run_lock(self, source_key: str) -> AsyncIterator[None]:
        self.calls.append(f"lock:{source_key}")
        try:
            yield
        finally:
            self.calls.append("unlocked")


async def test_replay_excludes_malformed_and_non_derivable_without_rewriting() -> None:
    items = (
        ReplayWorkItem("channel", 1, {"broken": True}),
        ReplayWorkItem("channel", 2, {"text": "hello"}),
    )
    source = _Source([items, (), items])
    store = _Store()
    summary = await RawParserReplayer(store, source, default_live_channel_identity(), _decode)()
    assert summary.not_rederivable == 1
    assert summary.reprocessed == 0
    assert summary.stale_after_replay == 2
    assert store.batches == []
    assert source.excluded[1] == frozenset({"channel:1", "channel:2"})
    assert source.excluded[-1] == frozenset()
    assert store.calls[-1] == "unlocked"


async def test_replay_bounds_rounds_when_stale_selection_does_not_converge() -> None:
    source = _Source([(ReplayWorkItem("channel", index, {"id": index}),) for index in range(1, 7)])
    summary = await RawParserReplayer(_Store(), source, default_live_channel_identity(), _decode)()
    assert summary.reprocessed == 5
    assert len(source.excluded) == 6  # five bounded rounds plus final status observation
    assert summary.stale_after_replay == 1


async def test_replay_failure_records_failed_run_and_releases_lock() -> None:
    store = _Store(fail_on_batch=1)
    source = _Source([(ReplayWorkItem("channel", 1, {}),)])
    with pytest.raises(PersistenceBatchError):
        await RawParserReplayer(store, source, default_live_channel_identity(), _decode)()
    assert any(call.startswith("finish:failed:") for call in store.calls)
    assert not any(call.startswith("finish:succeeded:") for call in store.calls)
    assert store.calls[-1] == "unlocked"


async def test_cancelled_replay_releases_lock_without_claiming_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _Store()
    source = _Source([(ReplayWorkItem("channel", 1, {}),)])

    async def cancel(**_kwargs: object) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(store, "persist_live_upsert", cancel)
    with pytest.raises(asyncio.CancelledError):
        await RawParserReplayer(store, source, default_live_channel_identity(), _decode)()
    assert not any(call.startswith("finish:succeeded:") for call in store.calls)
    assert store.calls[-1] == "unlocked"
