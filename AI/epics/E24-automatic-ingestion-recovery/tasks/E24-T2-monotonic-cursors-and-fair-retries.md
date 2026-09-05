---
schema: ai-workflow/task@1
id: E24-T2
epic: E24
title: "Make source cursors monotonic and retries fair"
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
  source: ../proposed-tasks/E24-T2-monotonic-cursors-and-fair-retries.md
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
  verified_at: "2026-09-05T13:13:10Z"
  evidence:
    - "E24-T1 done: https://github.com/Flippylolz/WEF/pull/331; merged 64da1bd9dd00e64be4e5ddbfce32e53f19c8f2af; deployment 33967260852 and ../PRODUCTION_EVIDENCE.md passing 15-minute window"
branch:
  required: true
  name: bugfix/E24-T2-cursors-and-retries
  task_id: E24-T2
  one_task_only: true
  created_at: "2026-09-05T11:12:46Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/334
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

# E24-T2: Make source cursors monotonic and retries fair

## Outcome

Passive events, polling, and archive recovery share a cursor that never moves backward and a retry policy that distinguishes contention from corrupt data.

## Scope and work

Define a durable channel high-water cursor, lock/read/update ordering, per-item retry scheduling, bounded backoff and jitter, and fair work selection. Reconcile old edits/deletes within explicitly supported source-access bounds.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Refined implementation contract

Use the [durable progress design](../IMPLEMENTATION_PLAN.md#t2-durable-channel-progress)
and [retry/coverage design](../IMPLEMENTATION_PLAN.md#t2-fair-retries-and-old-message-coverage)
in implementation plan revision 1. Store distinct applied high-water and forward
polling boundaries per channel; neither decreases. A passive event cannot certify
an untraversed range. Legacy run completion and maximum message ID cannot bootstrap
polling coverage; use a bounded scan from zero if no trustworthy traversal evidence
exists. Persist older-known-ID sweep continuation separately.

Read progress under local serialization and re-read/write under the channel
advisory lock and transaction. Keep network/backoff waits outside those locks.
Project the same committed meanings into runtime/operator diagnostics, with
additive compatible fields and no new public readiness gate.

Persist next eligibility and separate data-failure/deferral accounting. Use a
5-second exponential base, a 300-second ceiling with bounded positive jitter,
provider retry-after minimums, and five data failures before quarantine. Select
due rows fairly; keep one exception per original UUID and re-evaluate on a relevant
policy/code version change. Reschedule proven historical lock exhaustion once
without resetting historical attempt evidence.

Bound each reconciliation cycle to 500 source IDs: up to 400 forward and 100 older
known IDs, in requests no larger than 100. An explicit-ID observation is present,
confirmed deleted, or unknown; inaccessible or omitted results cannot imply
deletion. Persist coverage limitations and due times. Metadata sweeps do not fetch
media. E8 retains passive callback acceptance, and T4 retains broader incident
health policy.

## Acceptance criteria

- [ ] A deterministic race where polling advances the cursor before older archive work gets the lock leaves the persisted cursor unchanged at the higher value.
- [ ] Lower-ID edits and deletions are applied without decreasing the channel high-water cursor; status and runtime read the same committed meaning.
- [ ] RunLockHeldError and provider/transport deferrals do not exhaust the malformed-record budget; eligible jobs resume automatically after contention clears.
- [ ] A poisoned event cannot starve later events, and an exhausted record has one actionable exception record with reason, evidence, and an automatic re-evaluation trigger.
- [ ] An outage/overlap test covers new records and older edits/deletes under a documented bounded reconciliation policy; unsupported source-history gaps are visible and not falsely marked complete.
- [ ] A passive high-ID event cannot move the polling boundary over an unobserved interval; crash/restart before a polled batch boundary re-fetches idempotently, with deferred/quarantined records still shown as incomplete canonical coverage.
- [ ] Two real database sessions plus deterministic barriers prove monotonic progress independently of local lock ownership and run finish order.
- [ ] More than five lock/transport deferrals remain recoverable without data-budget exhaustion; wrapped database connectivity errors are classified as transient, not malformed data.
- [ ] Next eligibility survives restart, honors provider minimum delays, and allows healthy later records through. A relevant version change re-evaluates a quarantined original once; unrelated releases cannot reset its budget indefinitely.
- [ ] Bounded old-ID sweeps resume across restarts and cover retained edits/deletes outside the overlap; incomplete responses and access loss remain unknown with visible coverage limitations.
- [ ] Legacy progress bootstrap, exhausted lock-failure rescheduling, and diagnostic compatibility preserve source/attempt evidence and never silently initialize polling coverage from maximum source ID.

## Tests and verification

Extend test_telegram_reconciliation.py, test_telegram_worker_ops.py, and database integration tests with controlled concurrent tasks. Verify restart, lock contention, stale cursors, monotonicity, and retry fairness.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Spike revision 2 is approved under
[AD-048](../../../workflow/AUTONOMOUS_DECISIONS.md#ad-048-approve-e24-spike-revision-2-and-prepare-the-first-implementation-plan).
This task was moved from its proposed location and refined to revision 2.
[Implementation plan revision 1](../IMPLEMENTATION_PLAN.md) records this exact
revision and is approved under AD-049. Its implementation gate is satisfied;
branch and dependency gates still govern the start of work.

T1 is done following merged PR #331 and its passing production observation. T2 is
rebased onto that merged release; its dependency gate is satisfied.

## Rollout and automatic operation

If a cursor/retry schema is needed, deploy additively and derive its initial state from verified channel evidence. Observe old/new status parity before switching authoritative reads.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Retain the highest verified cursor and per-event ledger. Pause the affected consumer rather than resetting progress to the newest run's arbitrary checkpoint.

## Risks and exclusions

Using MAX(message_id) alone may skip holes. High-water progress needs reconciliation evidence, not an assumption that every lower ID is an offer.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Ready and completion checks

- [x] The authoritative file is under `tasks/`; its proposed predecessor was moved.
- [x] Promotion and approved spike revision 2 verification are recorded.
- [x] Scope, acceptance, tests, and recovery constraints match the approved spike.
- [x] Owner approved implementation plan revision 1 with this task at revision 2 under AD-049.
- [x] Dependency gate permits implementation through the T1 stack and a dedicated task branch is recorded.
- [ ] Acceptance evidence, required checks, PR, and definition of done are complete.

## Implementation evidence — 2026-09-05

Implemented on the ordered T1 stack. Revision `20260905_0021` adds durable channel
progress, due times, separate data/deferral counters, and the unique exception
ledger. Canonical and polling transactions use independent monotonic boundaries.
Known-ID sweeps retain a fixed range and a token lease; unknown history remains
limited. Transport/lock retries preserve the data budget and policy revisions
provide bounded automatic quarantine re-evaluation.

Real PostGIS proofs cover an older transaction following a higher committed
cursor, passive high-ID isolation, more than five deferrals followed by success,
poison fairness and one exception, restart eligibility, legacy classification,
source outage, lower-ID edit/deletion observations, and stale sweep completion.
The Telethon adapter test distinguishes explicit empty messages from omissions.

Validation:

- `make lint`: passed, including 17 architecture contracts and frontend lint.
- `make format-check`, `make typecheck`, `make contract-check`: passed.
- `make test COMPOSE='docker compose --project-name wef-e24 --file infra/compose.yaml'`:
  826 backend tests passed, 90.37% coverage; 169 frontend tests passed with coverage floors met.
- `python3 scripts/check_markdown_links.py` and `git diff --check`: passed.

Task remains `in_progress`: its refreshed required CI/review, authorized
release, and T2 production observation remain outstanding. No production cursor,
archive record, or queue was modified during implementation. T3/T4 remain outside
this approved implementation sequence.

Changed-file manifest (relative to the immediate T1 parent):

- `AI/epics/E24-automatic-ingestion-recovery/tasks/E24-T2-monotonic-cursors-and-fair-retries.md`
- `AI/ingestion/PIPELINE.md`
- `AI/operations/DEPLOYMENT.md`
- `apps/backend/migrations/versions/20260905_0021_ingestion_progress.py`
- `apps/backend/src/wef_backend/features/ingestion/application/archive_retry.py`
- `apps/backend/src/wef_backend/features/ingestion/application/raw_archive.py`
- `apps/backend/src/wef_backend/features/ingestion/application/telegram_events.py`
- `apps/backend/src/wef_backend/features/ingestion/application/telegram_live.py`
- `apps/backend/src/wef_backend/features/ingestion/application/telegram_progress.py`
- `apps/backend/src/wef_backend/features/ingestion/application/telegram_reconciliation.py`
- `apps/backend/src/wef_backend/features/ingestion/application/telegram_worker_liveness.py`
- `apps/backend/src/wef_backend/features/ingestion/application/telegram_worker_status.py`
- `apps/backend/src/wef_backend/features/ingestion/domain/telegram_worker_ops.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/archive_recovery.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/archive_retry_store.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/fake_telegram_client.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/models.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/persistence_adapter.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/raw_event_archive.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/telegram_progress_store.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/telegram_worker_status_store.py`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/telethon_client.py`
- `apps/backend/src/wef_backend/migration.py`
- `apps/backend/src/wef_backend/telegram_worker_command.py`
- `apps/backend/tests/test_archive_recovery_integration.py`
- `apps/backend/tests/test_ingestion_progress_integration.py`
- `apps/backend/tests/test_persistence_integration.py`
- `apps/backend/tests/test_telegram_live_backfill.py`
- `apps/backend/tests/test_telegram_live_events.py`
- `apps/backend/tests/test_telegram_reconciliation.py`
- `apps/backend/tests/test_telegram_worker_ops.py`


## Production dependency clearance

T1 passed its 15-minute production acceptance window on 2026-09-05, documented in
[production evidence](../PRODUCTION_EVIDENCE.md). This PR records that completed
dependency and proceeds from T1's merged main commit. Updated dependency evidence
adds the production record, T1 completion metadata, and epic progress to the
changed-file manifest above.

Additional dependency/rollout documentation changed in this PR:

- `AI/epics/README.md`
- `AI/milestones/M5-production-maturity.md`
- `AI/epics/E24-automatic-ingestion-recovery/README.md`
- `AI/epics/E24-automatic-ingestion-recovery/PRODUCTION_EVIDENCE.md`
- `AI/epics/E24-automatic-ingestion-recovery/tasks/E24-T1-terminate-original-archive-work.md`
