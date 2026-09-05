---
schema: ai-workflow/task@1
id: E24-T3
epic: E24
title: "Recover media independently after message commit"
status: in_progress
revision: 2
priority: P1
size: L
milestone: M5
dependencies: [E24-T1]
requirement_ids: [P-006, P-007]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-012, ADR-015]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E24-T3-recover-media-after-message-commit.md
  promoted_by: Codex
  promoted_at: "2026-09-05T16:26:26.608472Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: Codex
  verified_at: "2026-09-05T16:26:26.608472Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: Codex
  verified_at: "2026-09-05T16:28:48.314160Z"
dependency_gate:
  status: satisfied
  verified_by: Codex
  verified_at: "2026-09-05T16:26:26.608472Z"
  evidence:
    - "E24-T1 done through PR #331 and passing production acceptance; ../PRODUCTION_EVIDENCE.md"
branch:
  required: true
  name: bugfix/E24-T3-durable-media-recovery
  task_id: E24-T3
  one_task_only: true
  created_at: "2026-09-05T16:32:14.186324+00:00"
  pull_request: https://github.com/Flippylolz/WEF/pull/346
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E24-T3: Recover media independently after message commit

## Outcome

A successfully persisted message eventually receives every eligible derivative even if downloading or media processing failed on the first attempt.

## Scope and work

Persist bounded media-work identity/outcome, reconstruct valid media descriptors, retry failures independently of message checksum changes, and preserve privacy-safe original/derivative storage boundaries.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] Crash injection after canonical commit but before media processing recovers derivatives automatically after restart, even when the message is unchanged.
- [ ] Historical, live, and album reconstruction preserve descriptor and association evidence; non-listing media does not attach to an unrelated offer.
- [ ] Repeated processing uses existing descriptor/revision/transform replay keys to produce one terminal disposition per intended asset and no duplicate public derivatives.
- [ ] Transient fetch/transform errors retry under bounded limits; unsupported/unsafe media becomes a terminal explained disposition rather than a permanent hidden retry loop.
- [ ] Text ingestion remains available during media-provider failure and reports media backlog separately; routine recovery requires no operator backfill command.

## Tests and verification

Extend test_telegram_live_media.py and live-event/storage integration tests. Replace the unconditional unchanged-media-skip expectation with completed-versus-pending media assertions.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E24-T1. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

Promoted under approved spike revision 2. Implementation-plan revision 3 is explicitly owner-approved; see its T3 section for the durable identity, association, retry, test and rollout contract.

## Rollout and automatic operation

Add the media ledger compatibly if required, then schedule unresolved work in bounded batches. Reconcile known terminal storage records before generating missing work.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Pause media work while preserving canonical offers, original evidence, and successful derivatives. Do not remove public assets indiscriminately.

## Risks and exclusions

Missing media paths or historical local paths may need reacquisition from the source; classify unsupported cases without exposing paths or source contacts.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [x] Current epic spike revision explicitly approved.
- [x] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [x] All referenced dependencies and required decisions resolved for the planned sequence.
- [x] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [x] Dedicated implementation branch and PR #346 cover T3 after the approved gates cleared.


## Revision 2 planning contract

[Implementation-plan revision 3](../IMPLEMENTATION_PLAN.md#t3-independent-media-recovery-revision-3-approval-scope) defines the concrete recovery ledger, canonical-commit intention, historical association reconstruction, independent acquisition, derivative retry, migration and bounded rollout. All five acceptance criteria above retain their required outcomes. T1/T2 are completed historical dependencies; T4 remains proposed. Owner approval now covers revision 3 implementation and its bounded green-CI rollout.

Implementation starts on planning PR #343 at 6422f06; the approved planning parent is the only open ancestor. T1 dependency remains done.

## Implementation record

Planning PR #343 merged as `797266fe2ccb1d89ce1e69defb5f36e4d5fcbcf2` after all
required checks. Implementation remains on its dedicated T3 branch. Migration
`20260905_0024` introduces transactional intentions, work and discovery controls.
The worker now separates canonical text processing from source acquisition and
fences media publication against source/association revisions and live leases.

Regression coverage includes real transaction crash/restart, unchanged replay,
competing/expired claims, repeated deferrals, poison fairness, policy re-evaluation,
provider pauses, cross-page text/burst/reply/album association, partial/failed
variants, exact restricted-original reuse, stale publication, canary gating,
metadata-first acquisition and cancellation cleanup. A live/historical album key
alias is decoded without altering its stored payload or checksum.

Task remains in progress until the implementation PR, production canary and
15-minute observation pass. No production recovery/schema change was made during
local implementation. T4 and source-conflict override remain excluded.

Local validation before the final main rebase: lint, format, types, contracts and
links passed; 1,087 backend tests passed (90.18% coverage), and 169 frontend tests
passed. Exact-source resource proofs passed: five probes under 0.5 CPU plus a busy
process took 1.520–2.500 seconds; 500 one-MiB downloads and 500 heartbeat writes on
64 MiB tmpfs peaked at 1,052,672 bytes with no retained media files.

Changed-file manifest:

- `AI/epics/E24-automatic-ingestion-recovery/README.md`
- `AI/epics/E24-automatic-ingestion-recovery/tasks/E24-T3-recover-media-after-message-commit.md`
- `AI/epics/README.md`
- `AI/ingestion/PIPELINE.md`
- `AI/operations/DEPLOYMENT.md`
- `apps/backend/migrations/versions/20260905_0024_media_recovery.py`
- `apps/backend/src/wef_backend/features/ingestion/application/media_grouping.py`
- `apps/backend/src/wef_backend/features/ingestion/application/media_recovery.py`
- `apps/backend/src/wef_backend/features/ingestion/application/media_storage.py`
- `apps/backend/src/wef_backend/features/ingestion/application/telegram_live.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/media_recovery_discovery.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/media_recovery_execution.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/media_recovery_store.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/media_repository.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/models.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/persistence_adapter.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/telegram_record.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/telethon_client.py`
- `apps/backend/src/wef_backend/media_recovery_command.py`
- `apps/backend/src/wef_backend/migration.py`
- `apps/backend/src/wef_backend/telegram_media_wiring.py`
- `apps/backend/src/wef_backend/telegram_worker_command.py`
- `apps/backend/src/wef_backend/telegram_worker_status_command.py`
- `apps/backend/tests/test_media_recovery_integration.py`
- `apps/backend/tests/test_media_recovery_runner.py`
- `apps/backend/tests/test_telegram_env_session.py`

## Production rollout record

[PR #346](https://github.com/Flippylolz/WEF/pull/346) passed every required check
and merged as `abc4a5673f8a67dbf47a4567485b0048a58e928b`.
[Release 33981634057](https://github.com/Flippylolz/WEF/actions/runs/33981634057)
succeeded with additive migration `20260905_0024`. Final implementation validation
passed 1,097 backend tests and 169 frontend tests, plus lint, format, types,
contracts and Markdown links. The last regression ensures a canonical non-listing
attachment receives an explained disposition without stopping discovery.

The durable 100-asset canary reached `canary_ready` at 2026-09-05T17:48:12Z,
with zero generated-variant work and zero duplicate public associations. These
were already-complete assets, so this proves safe reuse, not actual derivative
repair. The approved bounded drain was resumed through the private media-only
control; no source, retry-budget or cursor override was used. Production evidence
is recorded in [PRODUCTION_EVIDENCE.md](../PRODUCTION_EVIDENCE.md).

Task remains `in_progress` until actual eligible derivative-repair evidence
satisfies the production gate. Synthetic crash/restart and partial-variant tests
pass, but they do not substitute for that production claim. T4 remains proposed.

A 919-second production window passed runtime/receipt/resource checks with
852 completed media assets and zero newly generated variants. Forward polling
reached 29,713 and the older-ID sweep advanced. The bounded drain remains running;
actual production repair evidence remains the outstanding acceptance gate.
