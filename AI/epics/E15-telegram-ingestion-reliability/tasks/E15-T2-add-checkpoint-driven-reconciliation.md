---
schema: ai-workflow/task@1
id: E15-T2
epic: E15
title: "Add checkpoint-driven Telegram reconciliation"
status: in_progress
revision: 1
priority: P0
size: L
milestone: M4
dependencies: [E15-T1]
requirement_ids: [P-006, P-007]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-010]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E15-T2-add-checkpoint-driven-reconciliation.md
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
  verified_by: "Codex agent (owner-approved E15 implementation under AD-040)"
  verified_at: "2026-08-28T15:14:20Z"
  evidence:
    - "E15-T1 done through PR https://github.com/Flippylolz/WEF/pull/189; green-CI squash merge b4b3d6112f271633127d4002110ed0ba5924937e"
branch:
  required: true
  name: feat/E15-T2-checkpoint-reconciliation
  task_id: E15-T2
  one_task_only: true
  created_at: "2026-08-28T15:08:59Z"
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

- [x] With passive events disabled, messages published after the checkpoint are found,
  persisted, and checkpointed within the approved reconciliation bound.
- [x] Startup and reconnect recover all unseen messages without full import; a repeated
  run is idempotent and event/poll races do not create duplicate offers or revisions.
- [x] A 55-record album burst with six listing candidates reconciles in source order
  under bounded pages/resources and advances only after committed persistence.
- [x] Edited messages create the correct immutable revisions; deletion handling is
  conservative, tested, and documents any Telegram guarantee that cannot be made.
- [x] Partial database/provider failure leaves the last committed checkpoint recoverable,
  reports a redacted category, and resumes without skipping an unseen suffix.
- [x] Remote-head/last-reconciliation status detects the incident shape where local max
  and local checkpoint both equal `29202` while Telegram is ahead.
- [x] Flood-wait, rate/backoff, cancellation, advisory-lock, malformed/non-candidate,
  edit/delete, restart, and integration tests pass without source/contact leakage.

## Affected modules and contracts

- The ingestion application layer gains one checkpoint-driven reconciliation use case
  that reuses `LiveTelegramEventProcessor`/the canonical persistence port.
- `TelegramLiveClientPort`, Telethon, and fake adapters gain bounded remote-head/message
  access needed by the reconciliation loop.
- Worker lifecycle and health state from E15-T1 supervise and report reconciliation.
- Settings/Compose gain bounded interval/page/overlap configuration with safe defaults.
- No public HTTP/OpenAPI contract changes and no database migration are authorized;
  remote observation remains privacy-safe runtime health state.

## Risks and notes

Polling too aggressively risks provider throttling; polling too slowly weakens freshness.
Deletion inference from an absent message can be unsafe and must preserve uncertainty.
The implementation plan must define compatibility and whether any schema/configuration
change is genuinely required before one is authorized.

## Test plan

- Unit: checkpoint boundary, overlap, paging, remote head, backoff, cancellation, and
  event/poll deduplication using the fake Telegram client.
- Integration: PostgreSQL transaction-before-checkpoint behavior, partial failure,
  advisory-lock contention, replay, edits/deletes, and the 55-record incident shape.
- Contract/migration: no OpenAPI/schema change; settings and Compose validation.
- Operations: startup, periodic, disconnect/reconnect, missed-event, flood-wait, health
  fire/recovery, bounded shutdown, and previous-image rollback safety.

## Rollout and rollback

Deploy only after E15-T1 is done. Start with conservative bounded defaults; startup
reconciliation runs before passive-only steady state can be considered healthy. Rollback
to the prior image/config remains safe because persistence/checkpoint contracts do not
change and reconciliation never rewinds the durable checkpoint. Replayed messages are
idempotent and are not deleted on rollback.

## Ready checklist

- [x] Authoritative under `tasks/`; the proposed definition was moved, not copied.
- [x] Promotion metadata and owner-approved spike revision 1 are recorded.
- [x] Implementation plan revision 1 is owner-approved and the gate is satisfied.
- [x] E15-T1 is done through green-CI PR #189; the dependency gate is satisfied.
- [x] Scope and acceptance match the spike recommendation.
