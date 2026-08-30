"""Deidentified multilingual place-review eval harness using a fake provider.

This is not live Groq evidence. Production activation stays blocked until the
owner approves quality thresholds, supplies a Groq secret, and verifies ZDR.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from tests.fakes import FakeAdminAuditStore, FakeChatCompletions, FakeClock, FakePlaceAiReviewStore
from wef_backend.features.admin.application.ai_review import (
    ALLOWED_GROQ_MODEL,
    AiCurationRuntime,
    GeneratePlaceReview,
    LocationAiSnapshot,
    PlaceReviewStatus,
    SourceRevisionEvidence,
    parse_place_review_payload,
)
from wef_backend.features.ingestion.application.persistence import MASK_FILLER

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "place_review_eval"
_NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)


def _runtime() -> AiCurationRuntime:
    return AiCurationRuntime(
        enabled=True,
        zdr_verified=True,
        model=ALLOWED_GROQ_MODEL,
        api_key_present=True,
    )


def _cases() -> tuple[dict[str, object], ...]:
    loaded: list[dict[str, object]] = []
    for locale in ("pl", "ru", "uk"):
        raw = json.loads((_FIXTURE_DIR / f"{locale}.json").read_text(encoding="utf-8"))
        assert isinstance(raw, dict)
        loaded.append(raw)
    return tuple(loaded)


async def test_deidentified_eval_corpus_records_fake_provider_metrics() -> None:
    """PL/RU/UK fixtures mask contacts, parse the schema, and stay offline."""
    report: list[dict[str, object]] = []
    for case in _cases():
        location_id = uuid4()
        sources_raw = case["sources"]
        assert isinstance(sources_raw, list)
        revisions = tuple(
            SourceRevisionEvidence(
                revision_id=uuid4(),
                checksum=f"{index:064d}"[:64],
                published_at=_NOW,
                text_original=str(text),
            )
            for index, text in enumerate(sources_raw, start=1)
        )
        payload = case["provider_payload"]
        assert isinstance(payload, dict)
        fields = payload.get("fields")
        assert isinstance(fields, list)
        patched_fields = []
        for item in fields:
            assert isinstance(item, dict)
            updated = dict(item)
            updated["evidence_revision_ids"] = [str(revisions[0].revision_id)]
            patched_fields.append(updated)
        patched = {**payload, "fields": patched_fields}
        parse_place_review_payload(
            patched,
            allowed_revision_ids={str(item.revision_id) for item in revisions},
        )
        provider = FakeChatCompletions(payload=patched)
        store = FakePlaceAiReviewStore(
            snapshot=LocationAiSnapshot(
                id=location_id,
                display_name=str(case["display_name"]),
                display_address=str(case["display_address"]),
                district=str(case["district"]),
                review_status="needs_review",
                updated_at=_NOW,
                normalized_address_hash="c" * 64,
            ),
            revisions=revisions,
        )
        generate = GeneratePlaceReview(
            store,
            provider,
            FakeAdminAuditStore(),
            FakeClock(moment=_NOW),
            _runtime(),
        )
        outcome = await generate(
            owner_id=uuid4(),
            location_id=location_id,
            request_id=uuid4(),
        )
        sent = "\n".join(message["content"] for message in provider.calls[0])
        contact_tokens = case["contact_tokens"]
        assert isinstance(contact_tokens, list)
        leaked = [token for token in contact_tokens if str(token) in sent]
        unsupported = [
            item.get("field_name")
            for item in patched_fields
            if item.get("field_name") not in {"display_name", "display_address", "district"}
        ]
        assert outcome.status is PlaceReviewStatus.GENERATED
        assert leaked == []
        assert MASK_FILLER in sent
        assert outcome.run is not None
        report.append(
            {
                "locale": case["locale"],
                "schema_success": True,
                "contact_leakage": 0,
                "unsupported_changes": len(unsupported),
                "token_input": outcome.run.token_input,
                "token_output": outcome.run.token_output,
                "latency_ms": outcome.run.provider_latency_ms,
                "live_provider_used": False,
            },
        )

    assert {item["locale"] for item in report} == {"pl", "ru", "uk"}
    assert all(item["schema_success"] is True for item in report)
    assert all(item["contact_leakage"] == 0 for item in report)
    assert all(item["live_provider_used"] is False for item in report)
    assert all(item["unsupported_changes"] == 0 for item in report)
