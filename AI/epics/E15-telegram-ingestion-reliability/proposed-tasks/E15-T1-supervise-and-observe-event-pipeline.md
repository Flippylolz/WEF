---
schema: ai-workflow/proposed-task@1
id: E15-T1
epic: E15
title: "Supervise and observe the Telegram event pipeline"
status: proposed
revision: 1
actionable: false
priority: P0
size: M
milestone: M4
dependencies: []
requirement_ids: [P-006, P-007]
decision_ids: [ADR-006, ADR-008, ADR-010]
deferred_decision_ids: []
source: "production-incident:2026-08-27-telegram-gap"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
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

## Dependencies and gates

No task dependency. Promotion and implementation remain blocked on explicit approval of
E15 spike revision 1 and a later implementation plan containing this task revision.

## Risks and notes

Fail-fast supervision can increase restart frequency during provider/network incidents;
the implementation plan must bound reconnect/backoff and avoid a restart storm. Error
categories must remain useful without retaining message content.

## Promotion checklist

- [ ] E15 spike revision 1 is explicitly owner-approved.
- [ ] Scope, acceptance, P0 priority, size, and traceability match the approved spike.
- [ ] This file will be moved—not copied—to `tasks/` with complete promotion metadata.
- [ ] The approved implementation plan sequences this task before E15-T2/T3.

