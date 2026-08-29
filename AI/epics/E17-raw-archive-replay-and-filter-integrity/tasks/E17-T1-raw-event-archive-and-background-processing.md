---
schema: ai-workflow/task@1
id: E17-T1
epic: E17
title: "Raw event archive and background processing"
status: ready
revision: 1
priority: P1
size: L
milestone: M5
dependencies: []
requirement_ids: []
decision_ids: []
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E17-T1-raw-event-archive-and-background-processing.md
  promoted_by: "ZCode agent under owner instruction"
  promoted_at: "2026-08-29T17:10:10Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-29T17:10:10Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-29T17:10:10Z"
dependency_gate:
  status: satisfied
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-29T17:10:10Z"
  evidence: []
branch:
  required: true
  name: feat/E17-T1-raw-event-archive-and-background-processing
  task_id: E17-T1
  one_task_only: true
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---


# E17-T1: Raw event archive and background processing

## Outcome

Every incoming Telegram event (new message, edit, deletion) is first persisted
verbatim to an append-only raw-event table in the application database, and a
background stage drains that archive into the canonical ingestion core, so raw source
data survives canonical-stage failures and is available for future parser replay.

## Scope

- Append-only raw-event storage: event kind, channel identity, external message id,
  verbatim text/payload, media descriptors, published/edited timestamps, source
  checksum, received-at; no canonical interpretation.
- The live worker (and backfill/reconciliation) lands raw events before any
  extraction or canonical write; landing is idempotent per event checksum.
- Background drainer consumes unprocessed events in deterministic order with a durable
  per-event outcome ledger (processed/failed/skipped with bounded retry).
- Liveness/observability surface for archive depth and drainer progress, reported
  through the existing worker-status tooling without exposing source text or secrets.
- Retention policy applied per the owner decision from the spike (default: retain
  indefinitely; growth monitored under E14 budgets).

## Out of scope

- Parser changes (E17-T3), replay over the archive (E17-T2), facet/filter changes
  (E17-T4/T5), and the production backup gate (E17-T6).
- Any change to Telegram credentials/session handling (E8-T2 remains governing).

## Work

- Schema follows existing ingestion conventions (alembic migration, redacted columns,
  no source text in logs); the drainer reuses `extract_listing` +
  `persist_live_upsert` semantics unchanged.
- The E15 reconciliation loop must keep meeting its liveness bounds; landing a raw
  event must be strictly cheaper than today's inline extract+persist.

## Acceptance criteria

- [ ] A live message, an edit, and a deletion each land as raw events even when the
      canonical stage fails afterwards, and are drained exactly once once recovered.
- [ ] Redeploying or restarting the worker loses no unprocessed raw events.
- [ ] Integration tests cover landing idempotency, drainer ordering, failure/retry,
      and liveness reporting against disposable PostGIS.
- [ ] No raw source text, credentials, or Telegram session material appear in logs,
      reports, or Git.

## Dependencies and gates

- None inside E17; foundation for E17-T2 and E17-T6.
- Extends ADR-006 (shared ingestion core) and ADR-012 (backend-authoritative logic).

## Risks and notes

- Table growth on a shared NUC — monitor via existing E14 capacity evidence.
- Drainer must not bypass the run-lock/checkpoint machinery; double-processing must be
  prevented by the outcome ledger rather than in-memory state.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the
      approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
