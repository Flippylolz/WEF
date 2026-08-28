---
schema: ai-workflow/implementation-plan@1
epic: E15
title: "Telegram ingestion reliability recovery delivery"
status: approved
revision: 1
owner: owner
spike_revision: 1
task_sequence:
  - id: E15-T1
    revision: 1
  - id: E15-T2
    revision: 1
  - id: E15-T3
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: "Flippylolz"
  decided_at: "2026-08-28T14:33:48Z"
  approved_revision: 1
  evidence: "AD-040; owner instruction in Codex task on 2026-08-28: finish E15, keep every change in its own PR, and merge only after CI is green"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E15 implementation plan: Telegram ingestion reliability recovery

## Approved spike baseline

[Spike revision 1](SPIKE.md) is owner-approved under AD-039 and remains current. This
plan implements its recommended event-plus-checkpoint-polling architecture while
preserving ADR-003/005/006/007/008/010/015: backend-authoritative extraction,
transaction-before-checkpoint persistence, mounted restricted media, one immutable
single-server worker, and no unsupported backup claim.

## Scope and outcome

The single Telegram worker becomes fail-fast and observable, then gains bounded startup,
reconnect, and periodic checkpoint reconciliation. After the reviewed controls deploy,
the production suffix after checkpoint `29202` is reconciled to a stable observed remote
head and outage/missed-event recovery is rehearsed with redacted evidence.

Excluded: a broker, second worker, new dependency/service, polling-only architecture,
public HTTP/OpenAPI changes, schema migrations, raw Telegram evidence, full historical
re-import, speculative delete inference, media-pipeline expansion, and backup claims.

## Ordered task sequence

1. [E15-T1](tasks/E15-T1-supervise-and-observe-event-pipeline.md) — independently
   reviewable worker-lifecycle/health slice. Supervise transport, serialized consumer,
   heartbeat, and a named reconciliation lifecycle slot as one fail-fast task group;
   configure existing redacted structured logging for the worker and a safe Telethon
   standard-logging bridge; persist an atomic local runtime-health document alongside
   the backward-compatible timestamp heartbeat; and make Compose liveness require every
   enabled critical loop. No remote polling or checkpoint mutation. Unit/fake-client,
   lifecycle, redaction, Compose, lint/type/test checks. Rollback uses the prior image.
2. [E15-T2](tasks/E15-T2-add-checkpoint-driven-reconciliation.md) — depends on completed
   T1. Add one application-layer reconciliation loop using the existing Telegram client,
   extraction, advisory lock, and persistence core. It observes the remote head, polls
   forward from the durable local checkpoint at startup, after reconnect, and every 60
   seconds, processes at most 500 messages per cycle in pages/batches no larger than 100,
   and replays a 20-message recent overlap for edits/album convergence. Flood waits use
   the existing Telethon adapter backoff; failures preserve the last committed cursor.
   Passive deletes remain the only delete signal—absence from history never marks a
   source deleted. Runtime remote-head/reconciliation timestamps live in the local
   health document, avoiding a migration and high-cardinality telemetry. Fake-client and
   PostgreSQL tests cover the 55-record/six-candidate incident shape, replay, event/poll
   races, edits, cancellation, partial failure, locks, and health fire/recovery.
3. [E15-T3](tasks/E15-T3-recover-gap-and-prove-outage-recovery.md) — depends on completed
   T1/T2 and their green merged PRs. Verify the immutable production release and rollback
   target, singleton worker, credentials/channel identity, database/public HTTPS health,
   Forecast isolation, remote head, and local checkpoint. Run only the reviewed worker
   reconciliation path from the durable checkpoint to a recorded stable head; verify
   canonical/checkpoint/candidate effects and idempotent repeat without source content.
   Rehearse restart/disconnect, a suppressed passive-event catch-up, and critical-loop
   health fire/clear. Update B-003, E8/M4, deployment guidance, and task/epic completion
   records in its own documentation/operations PR.

Each item uses one dedicated PR and is merged in sequence only after required CI is
complete and green, as explicitly directed by the owner.

## Cross-task architecture

The composition root owns processes and settings; ingestion application services own
reconciliation; domain values own health classifications; infrastructure adapters own
Telethon/PostgreSQL/filesystem details. Event and poll paths converge before the
existing persistence port and never duplicate extraction or catalog rules. One channel
advisory lock serializes canonical mutations. Database transactions commit messages and
checkpoint before progress is reported. The runtime health document is diagnostic only
and never becomes a source cursor or public-readiness dependency.

T1's supervisor accepts named critical coroutines and cancels/drains siblings on the
first unexpected completion or failure. The T1 production reconciliation slot reports
`pending_implementation` and cannot imply source completeness; T2 replaces it with the
real loop and makes its freshness mandatory for worker liveness.

## Data and migrations

No database migration or public/persisted-contract change. The existing ingest-run
checkpoint remains authoritative and monotonic. T2 reads it before each cycle and
reuses idempotent upsert/revision behavior; remote observations are atomic local runtime
health, not acknowledged progress. Rollback does not rewind checkpoints or delete
recovered canonical data. E15 does not protect against host/database/media loss.

## Security and privacy

Credentials, string sessions, source text, contacts, raw events, database URLs, and
unbounded object representations are forbidden from logs/evidence. Structured worker
events use stable stage/category, bounded counts, necessary message/checkpoint IDs,
timestamps, and truncated release identity. Generic exception messages are scrubbed or
replaced by allowlisted categories. Tests inject credential-like strings and source text
to prove they do not escape. Session storage/modes and provider-egress isolation remain
unchanged.

## Test and verification strategy

- Backend unit/integration: lifecycle failure/cancellation/reconnect; handler conversion;
  persistence before/after run creation; advisory-lock rejection; runtime-health atomicity
  and freshness; startup/periodic polling; overlap; burst; replay; edit/delete limits;
  flood wait; remote gap; checkpoint monotonicity; PostgreSQL convergence.
- Repository/config: Ruff, strict mypy, pytest with ≥90% backend coverage, import boundary,
  formatting, Compose validation, secret/source exclusion, runtime image health command.
- Full repository before every task merge: `make format-check`, `make lint`, `make typecheck`,
  `make test`, and `make contract-check` where applicable; required GitHub CI must be green.
- Operations: immutable release deploy/health, bounded redacted worker status, stable
  remote/local boundary, idempotent repeat, outage and missed-event fire/recovery, public
  API/HTTPS and co-hosted Forecast non-interference.

## Operations, rollout, and rollback

T1 and T2 merge/deploy sequentially. Configuration stays deploy-owned; T2 defaults are
60-second interval, 100-message page/batch, 500-message cycle, 20-message overlap, and
existing flood-wait handling. Worker failure remains isolated from public API readiness.
`restart: unless-stopped`, 30-second grace, resource limits, restricted session mount,
and one replica remain.

Before T3 mutation, record current/prior release, worker count/ownership, database and
checkpoint, remote observed head, public health, rollback availability, and redaction.
Abort on identity/topology/schema/credential ambiguity, an unexpected checkpoint move,
unhealthy public services, or inability to identify the rollback image. Rollback uses the
existing immutable workflow and retains committed idempotent recovery.

## Risks and mitigations

- Restart storm after provider/database failure: bounded cleanup plus existing provider
  backoff and Docker restart policy; detect via stage/category health and container count.
- Event/poll race: one serialized application path/advisory ownership and idempotent
  persistence; integration tests force both orders.
- Poll load/flood wait: one 60-second cycle, bounded page/cycle sizes, existing explicit
  flood wait, no full-history scan.
- Album/edit boundary: ordered forward batches plus 20-message overlap; edits converge;
  deletion absence is never inferred.
- False health: mandatory enabled-stage freshness and first-task failure propagation;
  remote/local status remains distinct from public readiness.
- Sensitive diagnostics: allowlisted fields, scrubber, negative tests, bounded evidence.
- Source advances during recovery: record a stable observation boundary, reconcile again,
  and never claim an ambiguous moving head complete.

## Invalidation triggers

Return to the spike for a different Telegram account/channel/API, new dependency/service,
broker/replica/topology change, changed canonical checkpoint/revision/deletion semantics,
session/security model change, or evidence that the incident reached persistence. Return
to this plan for material changes to task order, polling bounds, health representation,
schema/config compatibility, test strategy, rollout, rollback, or production preflight.

## Approval record

Owner instruction on 2026-08-28 explicitly requires finishing E15, keeping every change
in its own PR, and permits merging each only after CI is green. AD-040 records that
instruction as approval of this bounded revision 1; it does not waive task dependency,
review, CI, deployment-health, privacy, or production-preflight gates.
