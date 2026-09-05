"""Source-only parser release acceptance and missing/parser-owned field planning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from wef_backend.features.ingestion.application.persistence import build_extraction_json

if TYPE_CHECKING:
    from wef_backend.features.ingestion.domain.extraction import ExtractionResult

# Acceptance changes with a reviewed benchmark-backed parser release, not runtime input.
ACCEPTED_RELEASE = ("e2-v14", "source-evidence-v2")
SCHEMA_VERSION = "parser-replay-v1"


def replay_populations(states: dict[str, int]) -> dict[str, int]:
    """Reconcile each selected record once; pending/canary work remains deferred."""
    result = {
        name: states.get(name, 0)
        for name in (
            "source_absent",
            "updated",
            "unchanged",
            "excluded",
            "protected_conflict",
            "failed",
        )
    }
    result["deferred"] = sum(
        states.get(name, 0)
        for name in (
            "queued",
            "claimed",
            "observed",
            "deferred",
        )
    )
    return {"considered": sum(states.values()), **result}


FIELD_COLUMNS = {
    "apartment_price_min": "price_min_minor",
    "apartment_price_max": "price_max_minor",
    "currency": "currency",
    "parking_price_min": "parking_price_min_minor",
    "parking_price_max": "parking_price_max_minor",
    "storage_price_min": "storage_price_min_minor",
    "storage_price_max": "storage_price_max_minor",
    **{
        name: name
        for name in (
            "content_type",
            "market_type",
            "property_type",
            "parking_included_in_price",
            "storage_included_in_price",
            "area_min_sqm",
            "area_max_sqm",
            "rooms_min",
            "rooms_max",
            "floor_label",
            "delivery_label",
        )
    },
}


@dataclass(frozen=True)
class ReplayField:
    """A canonical column value with source offsets and extraction group."""

    value: object
    start: int
    end: int
    group: str


@dataclass(frozen=True)
class ReplayPlan:
    """A minimized before/after proposal; protected fields never enter writes."""

    fields: dict[str, ReplayField]
    protected: tuple[str, ...]
    extraction: dict[str, object]


def scalar(value: object) -> object:
    """Normalize database decimals for durable JSON comparisons."""
    return str(value) if isinstance(value, Decimal) else value


def extraction_fields(document: dict[str, object], source_length: int) -> dict[str, ReplayField]:
    """Map retained typed extraction evidence without inventing missing fields."""
    result: dict[str, ReplayField] = {}
    for group, entry in document.items():
        if not isinstance(entry, dict):
            continue
        start, end = entry.get("source_start"), entry.get("source_end")
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or not 0 <= start < end <= source_length
        ):
            continue
        value = entry.get("value")
        mapped: dict[str, object] = {}
        if group in {"apartment_price", "parking_price", "storage_price"} and isinstance(
            value, dict
        ):
            mapped = {
                f"{group}_min": value.get("min_minor"),
                f"{group}_max": value.get("max_minor"),
            }
            if group == "apartment_price":
                mapped["currency"] = value.get("currency")
        elif group in {"area_sqm", "rooms"} and isinstance(value, dict):
            names = (
                ("area_min_sqm", "area_max_sqm")
                if group == "area_sqm"
                else ("rooms_min", "rooms_max")
            )
            mapped = dict(zip(names, (value.get("min"), value.get("max")), strict=True))
        else:
            name = {"floor": "floor_label", "delivery": "delivery_label"}.get(group, group)
            if name in FIELD_COLUMNS:
                mapped[name] = value
        for name, proposed in mapped.items():
            if proposed is not None:
                result[name] = ReplayField(proposed, start, end, group)
    return result


def plan_replay(
    extraction: ExtractionResult,
    source: str,
    previous: dict[str, object],
    current: dict[str, object],
    protected: frozenset[str],
) -> ReplayPlan:
    """Require old-parser value agreement or an empty value; block coupled conflicts."""
    if extraction.listing is None:
        return ReplayPlan({}, (), {})
    document = json.loads(build_extraction_json(extraction.listing))
    proposed = extraction_fields(document, len(source))
    old = extraction_fields(previous, len(source))
    warning_groups = {warning.field_name for warning in extraction.warnings}
    blocked: set[str] = set()
    for name, field in proposed.items():
        value = current.get(name)
        prior = old.get(name)
        owns = (prior is not None and scalar(prior.value) == scalar(value)) or (
            prior is None and value in (None, "unknown", False)
        )
        if name in protected or field.group in warning_groups or not owns:
            blocked.add(field.group)
    # Currency and amount changes are coupled; a protected quote cannot mix with a new currency.
    money_groups = {"apartment_price", "parking_price", "storage_price"}
    currency = proposed["currency"].value if "currency" in proposed else current.get("currency")
    for group in ("parking_price", "storage_price"):
        quote = document.get(group, {}).get("value", {})
        if quote and quote.get("currency") != currency:
            blocked.add(group)
        included = f"{group.removesuffix('_price')}_included_in_price"
        if (
            included in proposed
            and proposed[included].value is True
            and any(current.get(f"{group}_{bound}") is not None for bound in ("min", "max"))
        ):
            blocked.add(included)
            blocked.add(group)
    apartment = document.get("apartment_price", {}).get("value", {})
    if apartment and not apartment.get("currency"):
        blocked.add("apartment_price")
    if blocked & money_groups:
        blocked |= money_groups
    fields = {name: field for name, field in proposed.items() if field.group not in blocked}
    return ReplayPlan(
        fields,
        tuple(sorted(name for name, field in proposed.items() if field.group in blocked)),
        document,
    )
