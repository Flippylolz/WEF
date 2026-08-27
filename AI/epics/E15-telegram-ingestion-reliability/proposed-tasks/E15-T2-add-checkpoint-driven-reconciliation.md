---
schema: ai-workflow/proposed-task@1
id: E15-T2
epic: E15
title: "Add checkpoint-driven Telegram reconciliation"
status: proposed
revision: 1
actionable: false
priority: P0
size: L
milestone: M4
dependencies: [E15-T1]
requirement_ids: [P-006, P-007]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-010]
deferred_decision_ids: []
source: "production-incident:2026-08-27-telegram-gap"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E15-T2: Add checkpoint-driven Telegram reconciliation

## Outcome

Every Telegram message after the durable channel checkpoint is eventually discovered
and processed through the canonical idempotent persistence core even when passive
NewMessage/Edit/Delete delivery is incomplete or the worker reconnects/redeploys.

## Scope

- Reconcile from the committed database checkpoint at worker startup, after reconnect,
  and on a bounded periodic schedule while retaining passive events for low latency.
- Define bounded forward paging, recent overlap, album/media-group ordering, edit
  revision, deletion-review, flood-wait/backoff, advisory ownership, and cancellation semantics.
- Converge event and poll paths through the existing extraction/persistence services so
  duplicate delivery cannot create duplicate source messages, revisions, or offers.
- Record privacy-safe remote observation and last successful reconciliation timestamps
  separately from the committed checkpoint where transaction semantics require it.
- Detect a remote source suffix ahead of local persistence and expose actionable lag/
  gap status even when local checkpoint and local maximum are internally aligned.
- Add deterministic fake-client and PostgreSQL integration tests for quiet periods,
  bursts, restart/reconnect, overlap, edits, deletes, partial failure, and replay.

## Out of scope

- A second worker, broker/queue, full historical re-import, unbounded polling, public API
  contract changes, or unrelated media-download completion owned by E8-T2.

## Work

- Refine one source-completeness loop around the stable channel identity and durable
  external message ID checkpoint.
- Reuse the established advisory lock and transaction-before-checkpoint ordering while
  preventing event/poll races and preserving bounded shutdown.
- Define an explicit freshness service level and provider-call budget for startup and
  steady state, including flood waits and temporary Telegram failure.
- Document rollback and compatibility: an older image must remain safe with the current
  schema/configuration, and rollback must not move the committed checkpoint backward.

## Acceptance criteria

- [ ] With passive events disabled, messages published after the checkpoint are found,
  persisted, and checkpointed within the approved reconciliation bound.
- [ ] Startup and reconnect recover all unseen messages without full import; a repeated
  run is idempotent and event/poll races do not create duplicate offers or revisions.
- [ ] A 55-record album burst with six listing candidates reconciles in source order
  under bounded pages/resources and advances only after committed persistence.
- [ ] Edited messages create the correct immutable revisions; deletion handling is
  conservative, tested, and documents any Telegram guarantee that cannot be made.
- [ ] Partial database/provider failure leaves the last committed checkpoint recoverable,
  reports a redacted category, and resumes without skipping an unseen suffix.
- [ ] Remote-head/last-reconciliation status detects the incident shape where local max
  and local checkpoint both equal `29202` while Telegram is ahead.
- [ ] Flood-wait, rate/backoff, cancellation, advisory-lock, malformed/non-candidate,
  edit/delete, restart, and integration tests pass without source/contact leakage.

## Dependencies and gates

Depends on E15-T1 so reconciliation failures are supervised and observable before the
new correctness loop becomes production-critical.

## Risks and notes

Polling too aggressively risks provider throttling; polling too slowly weakens freshness.
Deletion inference from an absent message can be unsafe and must preserve uncertainty.
The implementation plan must define compatibility and whether any schema/configuration
change is genuinely required before one is authorized.

## Promotion checklist

- [ ] E15 spike revision 1 is explicitly owner-approved.
- [ ] Scope, acceptance, dependency, P0 priority, size, and traceability match the approved spike.
- [ ] E15-T1 is promoted and the implementation plan records direct sequence/dependency evidence.
- [ ] This file will be moved—not copied—to `tasks/` with complete promotion metadata.

