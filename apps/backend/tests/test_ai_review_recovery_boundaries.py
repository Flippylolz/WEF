"""Review isolation and conservative automatic recovery boundaries."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.fakes import FakeChatCompletions, FakePlaceAiReviewStore
from tests.test_ai_review import _apply, _field, _generate, _payload, _revision, _snapshot
from tests.test_offer_enrichment import _snapshot as _offer_snapshot
from wef_backend.features.admin.application.admin_ops import AdminDeniedError
from wef_backend.features.admin.application.ai_review import (
    GetPlaceReview,
    ProviderOutcome,
    ProviderRequestError,
    ReviewRunState,
    canonicalize_proposed_field,
    parse_place_review_payload,
)
from wef_backend.features.admin.application.automatic_recovery import (
    AutomaticRecovery,
    RecoveryWork,
)
from wef_backend.features.admin.application.ingestion_ai_parse import IngestionAiParseStatus
from wef_backend.features.admin.application.offer_enrichment import BatchState
from wef_backend.features.admin.application.recovery_validation import (
    evidence_supports_field,
    listing_creation_supported,
    money_currency_matches,
)


@pytest.mark.parametrize(
    "overrides",
    [
        {"fields": None},
        {"warnings": None},
        {"warnings": ["invented"]},
        {"fields": [5]},
        {"fields": [{**_field("display_name"), "evidence_revision_ids": "not-a-list"}]},
        {"fields": [{**_field("display_name"), "action": "invented"}]},
        {"fields": [{**_field("display_name"), "confidence": "certain"}]},
        {"fields": [{**_field("display_name"), "rationale_code": "invented"}]},
        {"fields": [{**_field("display_name"), "current_value": 3}]},
        {"fields": [{**_field("display_name"), "proposed_value": 3}]},
    ],
)
def test_review_payload_rejects_malformed_scalars(overrides: dict[str, object]) -> None:
    """Provider metadata must satisfy every bounded schema field."""
    revision_id = uuid4()
    with pytest.raises(ProviderRequestError) as caught:
        parse_place_review_payload(
            _payload(revision_id, extra=overrides), allowed_revision_ids={str(revision_id)}
        )
    assert caught.value.outcome is ProviderOutcome.SCHEMA


def test_review_cannot_apply_an_empty_proposal() -> None:
    """An omitted provider value cannot clear a canonical place field."""
    with pytest.raises(AdminDeniedError, match="proposal is empty"):
        canonicalize_proposed_field("display_name", None)


async def test_review_reads_hide_missing_and_other_owner_runs() -> None:
    """Direct and pending lookup apply the same owner boundary."""
    location, owner = uuid4(), uuid4()
    revision = _revision("Synthetic place")
    store = FakePlaceAiReviewStore(snapshot=_snapshot(location), revisions=(revision,))
    get = GetPlaceReview(store)
    assert await get(owner_id=owner, run_id=uuid4()) is None
    assert await get.pending_for_location(owner_id=owner, location_id=location) is None
    generate, _ = _generate(store, FakeChatCompletions(payload=_payload(revision.revision_id)))
    outcome = await generate(owner_id=owner, location_id=location, request_id=uuid4())
    assert outcome.run is not None
    assert await get(owner_id=uuid4(), run_id=outcome.run.id) is None
    assert await get.pending_for_location(owner_id=uuid4(), location_id=location) is None
    assert await get(owner_id=owner, run_id=outcome.run.id) == outcome.run


async def test_review_postwrite_disappearance_is_not_reported_as_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A store that cannot reload its acknowledged mutation fails closed."""
    location, owner = uuid4(), uuid4()
    revision = _revision("Synthetic place")
    store = FakePlaceAiReviewStore(snapshot=_snapshot(location), revisions=(revision,))
    generate, _ = _generate(store, FakeChatCompletions(payload=_payload(revision.revision_id)))
    outcome = await generate(owner_id=owner, location_id=location, request_id=uuid4())
    assert outcome.run is not None
    monkeypatch.setattr(store, "get_run", AsyncMock(side_effect=[outcome.run, None]))
    apply, _ = _apply(store)
    with pytest.raises(AdminDeniedError, match="review not found"):
        await apply(
            owner_id=owner,
            run_id=outcome.run.id,
            selected_fields=("display_name",),
            request_id=uuid4(),
        )


@pytest.mark.parametrize(
    ("source", "fragment", "field", "value"),
    [
        ("Floor: +48111222333", "+48111222333", "floor_label", "4"),
        ("Price: 0 PLN", "0 PLN", "apartment_price_min", 0),
        ("Market: invented", "invented", "market_type", "primary"),
        ("Price: 10 PLN", "10 PLN", "apartment_price_min", "bad-number"),
    ],
)
def test_recovery_refuses_contact_zero_unknown_and_nonnumeric_evidence(
    source: str, fragment: str, field: str, value: object
) -> None:
    """Exact quoting alone does not authorize unsafe scalar proposals."""
    assert not evidence_supports_field(source, fragment, field, value)


@pytest.mark.parametrize(
    ("source", "fragment"),
    [("Price: unknown PLN", "unknown"), ("outside\nPrice: 10 PLN", "outside")],
)
def test_price_currency_needs_a_valid_containing_price_line(source: str, fragment: str) -> None:
    """A label and ISO token cannot rescue malformed or unrelated price evidence."""
    assert not money_currency_matches(source, fragment, "apartment_price_min", "PLN")


def _creation_fields(location: str = "Warszawa, Testowa 1") -> tuple[dict[str, object], ...]:
    return (
        {"field_name": "location", "proposed_value": location, "evidence_fragment": location},
        {"field_name": "currency", "proposed_value": "PLN", "evidence_fragment": "PLN"},
        {
            "field_name": "apartment_price_min",
            "proposed_value": "780000",
            "evidence_fragment": "780000 PLN",
        },
    )


@pytest.mark.parametrize("mode", ["price", "currency", "empty", "type", "unrelated", "contact"])
def test_listing_creation_requires_calibrated_evidence_for_every_field(mode: str) -> None:
    """A good proposal cannot mask one unsafe price, location or currency field."""
    location = "Warszawa, Testowa +48111222333" if mode == "contact" else "Warszawa, Testowa 1"
    source = f"Продажа: квартира\nLocation: {location}\nPrice: 780000 PLN"
    fields = [dict(item) for item in _creation_fields(location)]
    if mode == "price":
        fields[2]["evidence_fragment"] = "квартира"
    elif mode == "currency":
        fields[1]["proposed_value"] = "EUR"
    elif mode == "empty":
        fields[0]["evidence_fragment"] = ""
    elif mode == "type":
        fields[0]["proposed_value"] = 10
    elif mode == "unrelated":
        fields[0]["evidence_fragment"] = "квартира"
    assert not listing_creation_supported(source, tuple(fields))


@pytest.mark.parametrize(
    "mode", ["empty", "denied", "local", "unavailable", "foreign", "generated"]
)
async def test_recovery_queue_handles_absent_work_failures_and_new_proposals(mode: str) -> None:
    """One tick records bounded outcomes and keeps local failures retryable."""
    queue, generate, apply, parses, start, process, enrichment = (AsyncMock() for _ in range(7))
    owner, now = uuid4(), datetime.now(UTC)
    work = RecoveryWork(uuid4(), uuid4(), owner, uuid4(), None, None, 1)
    queue.claim.return_value = None if mode == "empty" else work
    parses.get_pending_run.return_value = None
    if mode == "denied":
        generate.side_effect = AdminDeniedError("synthetic validation")
    elif mode == "local":
        generate.side_effect = RuntimeError("private provider body")
    else:
        run = (
            None
            if mode == "unavailable"
            else SimpleNamespace(
                id=uuid4(),
                owner_user_id=uuid4() if mode == "foreign" else owner,
                state=ReviewRunState.PENDING,
                proposed_fields=_creation_fields(),
            )
        )
        generate.return_value = SimpleNamespace(status=IngestionAiParseStatus.GENERATED, run=run)
        parses.get_revision_context.return_value = None
    await AutomaticRecovery(queue, generate, apply, parses, start, process, enrichment).tick(
        owner, now, submit=True, apply=False
    )
    apply.assert_not_called()
    if mode == "empty":
        generate.assert_not_called()
        queue.finish.assert_not_called()
    elif mode == "local":
        queue.retry_local.assert_awaited_once_with(work, now)
        queue.finish.assert_not_called()
    else:
        expected = (
            "validation_or_snapshot"
            if mode == "denied"
            else "creation_calibration_required"
            if mode == "generated"
            else "proposal_unavailable"
        )
        assert queue.finish.call_args.args[2] == expected


@pytest.mark.parametrize("mode", ["protected", "deferred", "observed"])
async def test_recovery_new_cohorts_respect_protected_fields_and_provider_deferral(
    mode: str,
) -> None:
    """A missing field creates at most one cohort and preserves protected AI values."""
    queue, generate, apply, parses, start, process, enrichment = (AsyncMock() for _ in range(7))
    owner, now, offer = uuid4(), datetime.now(UTC), uuid4()
    work = RecoveryWork(uuid4(), uuid4(), owner, uuid4(), offer, None, 1, ("rooms",))
    queue.claim.return_value = work
    queue.canary_passed.return_value = False
    queue.defer_provider.return_value = mode == "deferred"
    queue.cohort_outcome.return_value = ("observed", "validated_observation")
    enrichment.get_batch.return_value = None
    enrichment.get_offer_snapshot.return_value = _offer_snapshot(offer)
    enrichment.protected_field_names.return_value = (
        frozenset({"rooms_min", "rooms_max"}) if mode == "protected" else frozenset()
    )
    start.return_value = SimpleNamespace(id=work.id, state=BatchState.QUEUED)
    await AutomaticRecovery(queue, generate, apply, parses, start, process, enrichment).tick(
        owner, now, submit=True, apply=True
    )
    if mode == "protected":
        start.assert_not_called()
        process.assert_not_called()
        assert queue.finish.call_args.args[2] == "protected_conflict"
    else:
        start.assert_awaited_once_with(
            owner_id=owner, request_id=work.id, offer_ids=(offer,), limit=1, batch_id=work.id
        )
        assert process.call_args.kwargs["auto_apply"] is False
        if mode == "deferred":
            queue.finish.assert_not_called()
        else:
            assert queue.finish.call_args.args[2] == "validated_observation"
