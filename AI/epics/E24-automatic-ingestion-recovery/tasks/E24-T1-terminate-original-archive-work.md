---
schema: ai-workflow/task@1
id: E24-T1
epic: E24
title: "Terminate original archive work and repair starvation"
status: in_progress
revision: 2
priority: P1
size: L
milestone: M5
dependencies: []
requirement_ids: [P-006, P-007]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-012, ADR-015]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E24-T1-terminate-original-archive-work.md
  promoted_by: Codex
  promoted_at: "2026-09-05T10:19:12Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: Codex
  verified_at: "2026-09-05T10:19:12Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: Codex
  verified_at: "2026-09-05T10:33:19Z"
dependency_gate:
  status: satisfied
  verified_by: Codex
  verified_at: "2026-09-05T10:19:12Z"
  evidence: []
branch:
  required: true
  name: bugfix/E24-T1-original-archive
  task_id: E24-T1
  one_task_only: true
  created_at: "2026-09-05T10:39:00Z"
  pull_request: null
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

# E24-T1: Terminate original archive work and repair starvation

## Outcome

Each original archived event reaches its own terminal outcome once, and later queued records make progress without repeated processing of reconstructed siblings.

## Scope and work

Fix original-record acknowledgement, lossless reconstruction or direct archived-input processing, outcome correlation, idempotency, and bounded reconciliation of affected pending/sibling rows. Preserve original payload and checksum evidence.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Refined implementation contract

Use the [T1 design](../IMPLEMENTATION_PLAN.md#t1-archived-input-and-terminal-outcome)
and [bounded reconciliation](../IMPLEMENTATION_PLAN.md#t1-bounded-reconciliation-and-migration)
in implementation plan revision 1. Replay accepts the original archived UUID and
checksum through an inward-owned decoder port backed by the historical converter;
it never lands a reconstructed live event. Canonical effects and an immutable
original-event resolution receipt commit together. Archive acknowledgement is a
conditional projection of that receipt and cannot reopen a terminal row.

Share source-version/deletion guards across live/archive persistence and parser
replay. Preserve unknown-message deletion evidence, source provenance, and protected
offer fields. Validate legacy flattened seeds against retained source revisions;
unproved equivalence is not a completion outcome. New seeds preserve verbatim JSON.

Use additive receipt/tombstone/recovery-state schema, retaining the legacy raw
outcome values. Reconciliation has read-only preflight, one worker, 25-record
batches no faster than every 5 seconds, a durable 100-record canary, and a durable
pause/resume setting. Receipt evidence records each changed row and its prior
state. Acknowledgement-only recovery makes zero provider calls. Broader media
retry and progress-health policy remain T3/T4 responsibilities.

## Acceptance criteria

- [ ] A PostGIS regression using a historical payload with photo/entity fields and a differently shaped live payload proves the original record becomes terminal and the next oldest batch advances.
- [ ] Success, intentional non-candidate, canonical failure, cancellation after commit, and acknowledgement failure have explicit outcomes; restart completes pending work without duplicate offers or revisions.
- [ ] Replay cannot replace a newer canonical source revision with an older archive version, or resurrect a deleted offer. Add ordered old/new/edit/delete cases.
- [ ] An automated preflight reports eligible backlog, terminal siblings, oldest age, and proposed transitions; bounded application reconciles every changed row and re-running makes zero additional changes.
- [ ] A fixed production window shows unique pending work decreasing and terminal rows no longer accumulating attempts every cycle. Record exclusions and source-preservation checks without raw payloads.
- [ ] Replay creates no archive siblings; duplicate acknowledgement and a delayed failure leave an already-terminal row and its attempt count unchanged.
- [ ] Source/channel/ID/checksum mismatch and ambiguous same-time content do not mutate canonical state; legacy flattened seeds resolve only through exact retained evidence.
- [ ] A delete received before canonical creation leaves durable evidence preventing older replay from creating or revealing an offer; live and parser replay preserve the same tombstone and protected-field rules.
- [ ] A persisted original-event receipt recovers the commit/acknowledgement gap without a second extraction/upsert; cancellation propagates without consuming a data retry.
- [ ] All-failure and repeated-terminal drain batches do not refresh last committed time. Selected, attempted, and newly terminal counts reconcile separately.
- [ ] Canary/apply resumes after restart, honors durable pause, and balances its transition ledger. Production evidence covers 15 minutes after authorized release and distinguishes the fixed cohort from new arrivals.

## Tests and verification

Extend test_telegram_live_events.py and database-backed archive/persistence tests. Existing fake-archive tests must be complemented by real unique-checksum constraints and actual payload reconstruction. Include a restart/commit-boundary failure case.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Spike revision 2 is approved under
[AD-048](../../../workflow/AUTONOMOUS_DECISIONS.md#ad-048-approve-e24-spike-revision-2-and-prepare-the-first-implementation-plan).
This task was moved from its proposed location and refined to revision 2.
[Implementation plan revision 1](../IMPLEMENTATION_PLAN.md) records this exact
revision and is approved under AD-049. Its implementation gate is satisfied;
branch and dependency gates still govern the start of work.

T1 has no task dependencies.

## Rollout and automatic operation

Deploy the acknowledgement fix before any broad backfill. Enable bounded automatic reconciliation with durable progress and a pause switch; preserve a restricted before/after transition ledger.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Pause draining/reconciliation on evidence mismatch and retain all originals. Roll back code only to a version that cannot resume the known looping path; do not delete sibling rows to make counters look correct.

## Risks and exclusions

Clearing every pending row because a sibling exists could falsely acknowledge an unrelated revision. Correlate exact source/event semantics and downstream outcomes.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Ready and completion checks

- [x] The authoritative file is under `tasks/`; its proposed predecessor was moved.
- [x] Promotion and approved spike revision 2 verification are recorded.
- [x] Scope, acceptance, tests, and recovery constraints match the approved spike.
- [x] Owner approved implementation plan revision 1 with this task at revision 2 under AD-049.
- [ ] Dependency gate permits implementation and a dedicated task branch is recorded.
- [ ] Acceptance evidence, required checks, PR, and definition of done are complete.

## Implementation parent

Planning parent: [PR #325](https://github.com/Flippylolz/WEF/pull/325), branch
`doc/E24-ingestion-recovery-refinement`, head
`44ab444`; approved plan permits this documentation parent while it awaits merge.
T1 passed through `ready` before its dedicated branch was created.

## Implementation evidence (2026-09-05)

The implementation is reviewable on its dedicated branch, stacked on planning
[PR #325](https://github.com/Flippylolz/WEF/pull/325). It is not marked done: merge
and the authorized 15-minute production observation remain pending.

Validation passed: `make install`, `make lint`, `make format-check`,
`make typecheck`, `make contract-check`, `python3 scripts/check_markdown_links.py`,
and `git diff --check`. `make test COMPOSE='docker compose --project-name wef-e24
--file infra/compose.yaml'` passed in the isolated E24 project: 813 backend tests,
90.26% backend coverage, and 169 frontend tests with required coverage floors met.
The focused recovery suite exercises actual offers, historical mixed payloads,
terminal siblings, cancellation/commit boundaries, source ordering, deletion
before creation, bounded canary, and operator pause/resume.

Changed files for this task (including this evidence):

- `AI/epics/E24-automatic-ingestion-recovery/README.md`
- `AI/epics/E24-automatic-ingestion-recovery/tasks/E24-T1-terminate-original-archive-work.md`
- `AI/ingestion/PIPELINE.md`
- `AI/operations/DEPLOYMENT.md`
- `apps/backend/migrations/versions/20260905_0020_archive_recovery.py`
- `apps/backend/src/wef_backend/archive_recovery_command.py`
- `apps/backend/src/wef_backend/features/ingestion/application/archive_processing.py`
- `apps/backend/src/wef_backend/features/ingestion/application/persistence.py`
- `apps/backend/src/wef_backend/features/ingestion/application/raw_archive.py`
- `apps/backend/src/wef_backend/features/ingestion/application/raw_replay.py`
- `apps/backend/src/wef_backend/features/ingestion/application/telegram_events.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/archive_decoder.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/archive_evidence.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/archive_recovery.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/models.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/persistence_adapter.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/raw_event_archive.py`
- `apps/backend/src/wef_backend/migration.py`
- `apps/backend/src/wef_backend/raw_replay_command.py`
- `apps/backend/src/wef_backend/telegram_worker_command.py`
- `apps/backend/tests/test_archive_recovery_integration.py`
- `apps/backend/tests/test_persistence_application.py`
- `apps/backend/tests/test_persistence_integration.py`
- `apps/backend/tests/test_raw_replay_integration.py`
- `apps/backend/tests/test_telegram_live_backfill.py`
- `apps/backend/tests/test_telegram_live_events.py`
