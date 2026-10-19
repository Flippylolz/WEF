"""Deterministic, bounded candidate review with sanitized decision evidence."""

from __future__ import annotations

import json
from dataclasses import replace

from wef_backend.features.ingestion.domain.address_evidence import fold_address
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodeResult,
    NormalizedGeocodeQuery,
    SelectionReason,
    review_geocode_result,
)

MAX_GEOCODE_CANDIDATES = 5


def choose_geocode_candidate(
    query: NormalizedGeocodeQuery,
    candidates: tuple[GeocodeResult, ...],
) -> GeocodeResult:
    """Prefer a uniquely supported result; confidence never resolves ambiguity."""
    bounded = candidates[:MAX_GEOCODE_CANDIDATES]
    if not bounded:
        message = "candidate selection requires a bounded non-empty result set"
        raise ValueError(message)
    reviewed = [(result, review_geocode_result(result, query=query)) for result in bounded]
    accepted = [result for result, decision in reviewed if decision.select_result]
    # Different coordinates remain ambiguous even when the provider reuses a street name.
    positions = {
        (
            result.longitude,
            result.latitude,
            fold_address(result.address.district) if result.address else None,
        )
        for result, decision in reviewed
        if decision.select_result or decision.reason is SelectionReason.LOW_CONFIDENCE
    }
    ambiguous = len(positions) > 1
    chosen = max(accepted or bounded, key=lambda result: result.confidence)
    summaries = [
        {
            "address": result.address.as_json() if result.address else None,
            "longitude": str(result.longitude) if result.longitude is not None else None,
            "latitude": str(result.latitude) if result.latitude is not None else None,
            "precision": result.precision.value,
            "confidence": str(result.confidence),
            "reason": decision.reason.value,
        }
        for result, decision in reviewed
    ]
    diagnostic = dict(chosen.diagnostic)
    diagnostic["candidate_evidence"] = json.dumps(summaries, ensure_ascii=False, sort_keys=True)
    diagnostic["candidate_ambiguity"] = "true" if ambiguous else "false"
    return replace(chosen, diagnostic=tuple(sorted(diagnostic.items())))
