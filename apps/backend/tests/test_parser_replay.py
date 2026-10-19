"""Field ownership, semantic grouping and optional worker controls."""

import asyncio
import json
from dataclasses import replace
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from tests.test_inventory_extraction import SOURCE as INVENTORY_SOURCE
from tests.test_listing_extraction import _message
from wef_backend.features.ingestion.application.extraction import PARSER_VERSION, extract_listing
from wef_backend.features.ingestion.application.parse_quality import POLICY_VERSION
from wef_backend.features.ingestion.application.parser_replay import (
    ACCEPTED_RELEASE,
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


def test_unknown_groups_and_missing_scalar_bounds_do_not_invent_fields() -> None:
    document: dict[str, object] = {
        "unknown_group": {"value": "private source note", "source_start": 0, "source_end": 1},
        "rooms": {"value": {"min": 2, "max": None}, "source_start": 0, "source_end": 1},
        "area_sqm": {"value": {}, "source_start": 0, "source_end": 1},
    }
    fields = extraction_fields(document, 1)
    assert set(fields) == {"rooms_min"}
    assert fields["rooms_min"].value == 2


@pytest.mark.parametrize("addon", ["Parking", "Storage"])
def test_replay_refuses_addon_quotes_in_a_different_currency(addon: str) -> None:
    source = f"For sale: Apartment\nPrice: 700000 PLN\n{addon} price: 20000 EUR"
    result = extract_listing(_message(source))
    plan = plan_replay(result, source, {}, {}, frozenset())
    group = addon.casefold() + "_price"
    assert {f"{group}_min", f"{group}_max", "apartment_price_min", "currency"} <= set(
        plan.protected
    )
    assert "apartment_price_min" not in plan.fields


@pytest.mark.parametrize("addon", ["Parking", "Storage"])
def test_replay_preserves_existing_addon_price_when_inclusion_is_proposed(addon: str) -> None:
    source = f"For sale: Apartment\nPrice: 700000 PLN\n{addon}: included"
    result = extract_listing(_message(source))
    name = addon.casefold()
    plan = plan_replay(result, source, {}, {f"{name}_price_min": 1000000}, frozenset())
    assert f"{name}_included_in_price" in plan.protected
    assert f"{name}_included_in_price" not in plan.fields
    assert "apartment_price_min" in plan.protected


def test_replay_cannot_apply_price_without_a_currency() -> None:
    source = "For sale: Apartment\nPrice: 700000"
    result = extract_listing(_message(source))
    plan = plan_replay(result, source, {}, {}, frozenset())
    assert {"apartment_price_min", "apartment_price_max"} <= set(plan.protected)
    assert "apartment_price_min" not in plan.fields


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


def test_accepted_release_matches_the_current_benchmark_parser() -> None:
    assert ACCEPTED_RELEASE == (PARSER_VERSION, POLICY_VERSION)


def test_starting_price_replay_clears_the_old_fixed_upper_bound() -> None:
    result = extract_listing(_message(INVENTORY_SOURCE))
    assert result.listing
    document = json.loads(build_extraction_json(result.listing))
    previous = json.loads(build_extraction_json(result.listing))
    previous["apartment_price"]["value"]["max_minor"] = 74000000
    current = {
        name: field.value
        for name, field in extraction_fields(previous, len(INVENTORY_SOURCE)).items()
    }
    plan = plan_replay(result, INVENTORY_SOURCE, previous, current, frozenset())
    assert document["apartment_price"]["value"]["max_minor"] is None
    assert plan.fields["apartment_price_max"].value is None
    assert not plan.protected
