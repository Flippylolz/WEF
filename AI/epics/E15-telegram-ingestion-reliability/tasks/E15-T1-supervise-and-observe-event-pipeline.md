---
schema: ai-workflow/task@1
id: E15-T1
epic: E15
title: "Supervise and observe the Telegram event pipeline"
status: ready
revision: 1
priority: P0
size: M
milestone: M4
dependencies: []
requirement_ids: [P-006, P-007]
decision_ids: [ADR-006, ADR-008, ADR-010]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E15-T1-supervise-and-observe-event-pipeline.md
  promoted_by: "Codex agent (owner-approved E15 planning under AD-039)"
  promoted_at: "2026-08-28T14:31:47Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "Codex agent (owner-approved E15 planning under AD-039)"
  verified_at: "2026-08-28T14:31:47Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "Codex agent (owner-approved E15 implementation under AD-040)"
  verified_at: "2026-08-28T14:33:48Z"
dependency_gate:
  status: satisfied
  verified_by: "Codex agent (owner-approved E15 planning under AD-039)"
  verified_at: "2026-08-28T14:31:47Z"
  evidence: []
branch:
  required: true
  name: null
  task_id: E15-T1
  one_task_only: true
  created_at: null
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

# E15-T1: Supervise and observe the Telegram event pipeline

## Outcome

The production worker cannot remain healthy after its handler, queue consumer, or
reconciliation task stops, and operators receive redacted diagnostic evidence that
identifies the failed stage without exposing Telegram content or credentials.

## Scope

- Supervise connection, event consumer, reconciliation placeholder/lifecycle, and
  heartbeat tasks as one fail-fast worker lifecycle.
- Configure worker/Telethon logging with bounded redacted event categories, message IDs,
  timestamps, release identity, and exception categories—never raw payloads or text.
- Track distinct transport, consumer, and last-successful-commit/reconciliation health.
- Make the container healthcheck fail when any required worker task exits, wedges beyond
  its threshold, or loses its heartbeat, while keeping public API readiness independent.
- Add operator output that distinguishes connected-but-stale, consumer-dead, remote-gap,
  lock contention, persistence failure, and provider backoff states where observable.
- Add focused tests for task failure, cancellation, reconnect, error redaction, and
  health fire/recovery behavior.

## Out of scope

- Telegram polling/reconciliation semantics (E15-T2), production backfill/recovery
  (E15-T3), new monitoring infrastructure, or public API changes.

## Work

- Refine the worker lifecycle so every critical child task is awaited and a failure
  terminates the worker with a non-zero exit after bounded cleanup.
- Define privacy-safe structured events and stable error categories for handler,
  conversion, queue, advisory-lock, database, Telegram, and shutdown failures.
- Replace the transport-only heartbeat with the minimum state needed to prove the
  worker's critical loops are alive.
- Preserve Docker `restart: unless-stopped`, single-replica ownership, secret handling,
  and database/API isolation.

## Acceptance criteria

- [ ] Injected handler/consumer/reconciliation failures cause a non-zero worker exit and
  a redacted structured diagnostic; Docker cannot continue reporting the dead pipeline healthy.
- [ ] A connected transport with a stopped consumer or stale reconciliation heartbeat
  fails worker health within an approved bounded threshold.
- [ ] Normal cancellation/redeploy drains or safely abandons queued work according to
  documented transaction/checkpoint semantics and leaves no false-success heartbeat.
- [ ] Logs and status contain no source text, contacts, Telegram session/API secrets,
  database credentials, raw payloads, or unbounded identifiers.
- [ ] Unit/integration tests cover every critical task exit, handler conversion error,
  processor error before/after run creation, advisory-lock rejection, reconnect, and
  health fire/recovery path.
- [ ] Existing public API health/readiness behavior and one-worker Compose topology remain unchanged.

## Affected modules and contracts

- `apps/backend/src/wef_backend/telegram_worker_command.py` owns the supervised process lifecycle.
- `features/ingestion/application/telegram_worker_liveness.py` and
  `domain/telegram_worker_ops.py` own privacy-safe critical-loop health state.
- `features/ingestion/infrastructure/telethon_client.py` owns bounded handler diagnostics.
- `telegram_worker_status_command.py`, local/production Compose healthchecks, and
  `AI/operations/DEPLOYMENT.md` expose the operator contract.
- No public HTTP, OpenAPI, persisted schema, or public readiness contract changes.

## Risks and notes

Fail-fast supervision can increase restart frequency during provider/network incidents;
the implementation plan must bound reconnect/backoff and avoid a restart storm. Error
categories must remain useful without retaining message content.

## Test plan

- Unit: lifecycle winner/failure/cancellation behavior; heartbeat parsing/freshness;
  safe diagnostic category serialization and redaction.
- Integration: fake transport plus consumer success/failure/disconnect; heartbeat fire
  and recovery; persistence and advisory-lock failures propagate to process exit.
- Contract/migration: no OpenAPI or migration change; Compose configuration validation.
- Operations: public API readiness remains independent; prior image remains rollback-safe.

## Rollout and rollback

Ship through the immutable main-merge release workflow after task CI/review. The
production worker retains `restart: unless-stopped`; fail-fast errors cause a bounded
restart instead of a false healthy process. Roll back both worker image/config to the
prior release if restart behavior or health classification regresses. No data rollback
or checkpoint mutation belongs to this task.

## Ready checklist

- [x] Authoritative under `tasks/`; the proposed definition was moved, not copied.
- [x] Promotion metadata and owner-approved spike revision 1 are recorded.
- [x] Implementation plan revision 1 is owner-approved and the gate is satisfied.
- [x] No task dependencies; dependency gate is satisfied with empty evidence.
- [x] Scope and acceptance match the spike recommendation.
