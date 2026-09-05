"""Application recovery pauses, saved proposal reuse and missing-source behavior."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from wef_backend.features.admin.application.ai_review import ReviewRunState
from wef_backend.features.admin.application.automatic_recovery import (
    AutomaticRecovery,
    RecoveryWork,
)
from wef_backend.features.admin.application.ingestion_ai_parse import IngestionAiParseStatus
from wef_backend.features.admin.application.offer_enrichment import BatchState


async def test_paused_recovery_and_saved_proposal_never_generate_again() -> None:
    queue, generate, apply, parses, start, process, enrichment = (AsyncMock() for _ in range(7))
    service = AutomaticRecovery(queue, generate, apply, parses, start, process, enrichment)
    owner, now = uuid4(), datetime.now(UTC)
    await service.tick(owner, now, submit=False, apply=False)
    queue.enqueue.assert_not_called()
    work = RecoveryWork(uuid4(), uuid4(), owner, uuid4(), None, uuid4(), 1)
    queue.claim.return_value = work
    parses.get_revision_context.return_value = None
    parses.get_run.return_value = SimpleNamespace(
        id=work.proposal_id, owner_user_id=owner, state=ReviewRunState.PENDING
    )
    await service.tick(owner, now, submit=True, apply=False)
    generate.assert_not_called()
    apply.assert_not_called()
    assert queue.finish.call_args.args[1] == "observed"
    parses.get_run.return_value.state = ReviewRunState.APPLIED
    await service.tick(owner, now, submit=True, apply=False)
    assert queue.finish.call_args.args[1] == "applied"


async def test_linked_work_reuses_cohort_and_observes_until_canary() -> None:
    queue, generate, apply, parses, start, process, enrichment = (AsyncMock() for _ in range(7))
    service = AutomaticRecovery(queue, generate, apply, parses, start, process, enrichment)
    owner, now = uuid4(), datetime.now(UTC)
    work = RecoveryWork(uuid4(), uuid4(), owner, uuid4(), uuid4(), None, 1)
    queue.claim.return_value = work
    queue.cohort_outcome.return_value = ("observed", "validated_observation")
    queue.canary_passed.return_value = False
    queue.defer_provider.return_value = False
    enrichment.get_batch.return_value = SimpleNamespace(id=work.id, state=BatchState.RUNNING)
    await service.tick(owner, now, submit=True, apply=True)
    start.assert_not_called()
    assert process.call_args.kwargs["auto_apply"] is False
    enrichment.get_batch.return_value.state = BatchState.COMPLETED
    await service.tick(owner, now, submit=True, apply=True)
    assert process.await_count == 1


async def test_provider_failure_defers_without_per_record_owner_action() -> None:
    queue, generate, apply, parses, start, process, enrichment = (AsyncMock() for _ in range(7))
    service = AutomaticRecovery(queue, generate, apply, parses, start, process, enrichment)
    owner, now = uuid4(), datetime.now(UTC)
    queue.claim.return_value = RecoveryWork(uuid4(), uuid4(), owner, uuid4(), None, None, 1)
    parses.get_pending_run.return_value = None
    generate.return_value = SimpleNamespace(
        status=IngestionAiParseStatus.FAILED, reason="rate_limited"
    )
    queue.defer_provider.return_value = True
    await service.tick(owner, now, submit=True, apply=False)
    queue.finish.assert_not_called()
    queue.defer_provider.return_value = False
    await service.tick(owner, now, submit=True, apply=False)
    assert queue.finish.call_args.args[1] == "terminal"


async def test_calibrated_creation_requires_canary_and_recovers_after_apply() -> None:
    queue, generate, apply, parses, start, process, enrichment = (AsyncMock() for _ in range(7))
    service = AutomaticRecovery(queue, generate, apply, parses, start, process, enrichment)
    owner, now = uuid4(), datetime.now(UTC)
    work = RecoveryWork(uuid4(), uuid4(), owner, uuid4(), None, uuid4(), 1)
    queue.claim.return_value = work
    source = "Продажа: квартира\nLocation: Warszawa, Testowa 1\nPrice: 780000 PLN"
    fields = (
        {
            "field_name": "location",
            "proposed_value": "Warszawa, Testowa 1",
            "evidence_fragment": "Warszawa, Testowa 1",
        },
        {
            "field_name": "apartment_price_min",
            "proposed_value": "780000",
            "evidence_fragment": "780000 PLN",
        },
        {"field_name": "currency", "proposed_value": "PLN", "evidence_fragment": "PLN"},
    )
    parses.get_run.return_value = SimpleNamespace(
        id=work.proposal_id,
        owner_user_id=owner,
        state=ReviewRunState.PENDING,
        proposed_fields=fields,
    )
    parses.get_revision_context.return_value = SimpleNamespace(text_original=source)
    queue.canary_passed.return_value = False
    await service.tick(owner, now, submit=True, apply=True)
    apply.assert_not_called()
    assert queue.finish.call_args.args[2] == "validated_observation"
    queue.canary_passed.return_value = True
    await service.tick(owner, now, submit=True, apply=True)
    assert apply.call_args.kwargs["automatic"] is True
    assert queue.finish.call_args.args[1] == "applied"
    generate.assert_not_called()


async def test_linked_work_with_no_repairable_missing_fields_never_generates() -> None:
    queue, generate, apply, parses, start, process, enrichment = (AsyncMock() for _ in range(7))
    service = AutomaticRecovery(queue, generate, apply, parses, start, process, enrichment)
    owner, now = uuid4(), datetime.now(UTC)
    queue.claim.return_value = RecoveryWork(uuid4(), uuid4(), owner, uuid4(), uuid4(), None, 1)
    enrichment.get_batch.return_value = None
    enrichment.get_offer_snapshot.return_value = None
    await service.tick(owner, now, submit=True, apply=True)
    start.assert_not_called()
    process.assert_not_called()
    assert queue.finish.call_args.args[2] == "already_resolved_or_unsupported"
