"""Field ownership, semantic grouping and optional worker controls."""

import asyncio
import json
from dataclasses import replace
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from tests.test_listing_extraction import _message
from wef_backend.features.ingestion.application.extraction import extract_listing
from wef_backend.features.ingestion.application.parser_replay import (
    extraction_fields,
    plan_replay,
    scalar,
)
from wef_backend.features.ingestion.application.persistence import build_extraction_json
from wef_backend.features.ingestion.domain.extraction import (
    ExtractionWarning,
    ExtractionWarningCode,
)
from wef_backend.parser_replay_worker import maintain_parser_replay
from wef_backend.settings import Settings

SOURCE = "Продажа: квартира\nPrice: 780000 PLN\nArea: 37.50 m²\nRooms: 2\nPiętro 4"


def test_guarded_groups_preserve_owner_values_and_ai_fields() -> None:
    result = extract_listing(_message(SOURCE))
    assert result.listing
    document = json.loads(build_extraction_json(result.listing))
    fields = extraction_fields(document, len(SOURCE))
    values = {name: field.value for name, field in fields.items()}
    assert scalar(Decimal("37.50")) == "37.50"
    complete = plan_replay(result, SOURCE, document, values, frozenset())
    assert not complete.protected
    protected = plan_replay(result, SOURCE, document, values, frozenset({"currency"}))
    assert "currency" in protected.protected
    assert "apartment_price_min" not in protected.fields
    corrected = plan_replay(result, SOURCE, document, values | {"rooms_min": 5}, frozenset())
    assert "rooms_max" in corrected.protected
    warning = ExtractionWarning(next(iter(ExtractionWarningCode)), "apartment_price")
    ambiguous = plan_replay(
        replace(result, warnings=(warning,)), SOURCE, document, values, frozenset()
    )
    assert "currency" in ambiguous.protected
    negative = extract_listing(_message("Service: painting walls"))
    assert not plan_replay(negative, "Service: painting walls", {}, {}, frozenset()).fields


def test_unknown_or_invalid_prior_evidence_never_authorizes_overwrite() -> None:
    result = extract_listing(_message(SOURCE))
    protected = plan_replay(result, SOURCE, {}, {"apartment_price_min": 99}, frozenset())
    assert "apartment_price_min" in protected.protected
    malformed: dict[str, object] = {
        "apartment_price": {"value": {}, "source_start": -1, "source_end": 4},
        "rooms": None,
    }
    assert extraction_fields(malformed, len(SOURCE)) == {}


@pytest.mark.parametrize(("enabled", "failed"), [(False, False), (True, False), (True, True)])
async def test_worker_pause_progress_and_failure_isolation(
    monkeypatch: pytest.MonkeyPatch, *, enabled: bool, failed: bool
) -> None:
    stop = asyncio.Event()
    replay = AsyncMock()
    replay.counts.return_value = {"updated": 1}
    if failed:
        replay.tick.side_effect = RuntimeError
    monkeypatch.setattr("wef_backend.parser_replay_worker.SQLAlchemyParserReplay", lambda _: replay)

    async def wait_once(awaitable: object, *, timeout: int) -> None:  # noqa: ASYNC109
        assert timeout == 60
        stop.set()
        await awaitable  # type: ignore[misc]

    monkeypatch.setattr("wef_backend.parser_replay_worker.asyncio.wait_for", wait_once)
    await maintain_parser_replay(
        Settings(parser_replay_enabled=enabled), AsyncMock(), stop, lambda: True
    )
    assert replay.tick.await_count == int(enabled)
