---
schema: ai-workflow/spike@1
epic: E15
title: "Telegram ingestion reliability recovery"
status: awaiting_approval
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-008, ADR-010, ADR-015]
domain_docs: [architecture, data, ingestion, operations, security, workflow]
proposed_task_ids: [E15-T1, E15-T2, E15-T3]
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Telegram ingestion reliability recovery

> This spike is documentation and research only. It does not authorize code,
> configuration, infrastructure, dependency, migration, restart, backfill, or other
> production changes.

## Question

How should the single production Telegram worker guarantee eventual, idempotent source
reconciliation and truthful failure detection when Telegram/Telethon passive updates
are delayed, omitted, or fail inside the listener, without changing public contracts,
leaking protected data, or adding speculative infrastructure?

## Context and constraints

- The production account, API credentials, authorized session, verified public channel
  identity, one-worker topology, and canonical PostgreSQL persistence path already exist.
- The historical/backfill and live event paths share the canonical extraction and
  persistence core under ADR-006; E15 must reuse that core.
- Telegram availability and freshness must not gate the public API's readiness.
- The current Telethon adapter uses a `StringSession` and passive NewMessage,
  MessageEdited, and MessageDeleted handlers. The worker has no startup/periodic remote
  checkpoint polling and no durable Telethon update-state store.
- Telegram deletion delivery is not fully reliable, so the spike must distinguish
  guaranteed message/revision reconciliation from bounded deletion detection.
- Backups remain deferred under ADR-015. E15 may improve ingestion recovery but cannot
  claim protection from host/database/media loss.
- New dependencies or production services require explicit approval. Prefer the
  existing Telethon client, PostgreSQL checkpoint, Compose process model, and operator
  commands unless evidence proves them insufficient.

## Research method

- Read-only production inspection on 2026-08-27 of container lifecycle/health, redacted
  worker status, ingest runs, source-message/offer linkage, PostgreSQL locks, process
  inventory, Telegram channel membership, remote message IDs/timestamps, parser
  decisions, and deployed event-filter behavior.
- Repository inspection of worker orchestration, Telethon handlers/session storage,
  event conversion, canonical persistence, advisory locking, worker liveness/status,
  Compose health, tests, operations, and E8/B-003 acceptance state.
- Review of the Telethon 1.44 documentation for updates, sessions, `catch_up()`, and
  event-handler logging, plus the upstream pinned issue documenting passive
  NewMessage gaps for some public channels.
- No source text, contacts, credentials, session strings, raw Telegram payloads, or
  production data artifacts were written to Git or retained in the investigation.

Prohibited before implementation-plan approval:

- production/application code, tests, migrations, configuration, or infrastructure;
- listener restarts, checkpoint changes, session rotation, backfill, or data repair;
- disposable proof scripts, new services/dependencies, or raw production fixtures.

## Evidence

### Confirmed production facts

1. The listener container was running and connected before the missed publication
   window, had zero restarts, and remained Docker-healthy.
2. Telegram had messages `29203` through `29257`; PostgreSQL and the live checkpoint
   remained at `29202`, with zero source messages for the Warsaw 2026-08-27 day.
3. Six missed records passed the deployed parser's listing-candidate threshold.
4. No live ingest run exists for the missed range. The gap therefore occurred before
   `LiveTelegramEventProcessor` started canonical persistence.
5. Account authorization, channel identity, channel membership, deployed message
   conversion, and NewMessage/MessageEdited chat filters were valid.
6. There was one production worker and no current advisory lock or blocked database
   session explaining the gap.
7. The worker's redacted status correctly said `stale`, but its reconciliation said
   `aligned` because both compared values came from the same local database boundary.
   Docker health remained green because it checked only a heartbeat refreshed while
   `client.is_connected()` returned true.

### Confirmed design gaps

- Passive handlers are the only source of new/edit/delete work during the live loop.
- No startup, reconnect, or periodic `iter_messages(min_id=checkpoint)` reconciliation
  is part of the worker.
- The session string persists authentication material but not a durable per-channel
  update history sufficient to make source completeness dependably restartable.
- The queue consumer is created as an independent task but is not raced/supervised with
  the Telethon connection loop. A consumer failure can leave the transport heartbeat
  healthy indefinitely.
- The worker CLI does not configure Python/Telethon event logging. Telethon documents
  that event-handler exceptions are hidden by default unless logging is enabled.
- Status compares the persisted maximum with the persisted checkpoint. It has no
  remote-head observation, so an externally missing suffix may appear internally aligned.

### External behavior relevant to the incident

- Telethon's upstream issue
  [#4345](https://github.com/LonamiWebs/Telethon/issues/4345) records that some public
  channels do not reliably produce passive NewMessage callbacks and may require manual
  polling. The thread specifically reports misses after quiet periods and during bursts,
  matching the observed roughly 22-hour pause followed by the missed album burst.
- Telethon's [updates documentation](https://docs.telethon.dev/en/stable/basic/updates.html)
  recommends enabling logging because handler exceptions are otherwise hidden.
- Telethon's [client documentation](https://docs.telethon.dev/en/stable/modules/client.html)
  exposes `catch_up()` but does not make it a substitute for source-specific polling
  when the client lacks usable durable update state or Telegram does not push a channel.

### Root-cause boundary

The exact historical trigger cannot be proven because the worker recorded neither raw
update receipt nor handler/consumer failure. The strongest evidence supports a missing
or unprocessed passive Telegram update, followed by the absence of any independent
polling/reconciliation path. Regardless of whether the first omission occurred at
Telegram delivery, Telethon dispatch, or the unsupervised consumer, the architectural
cause of the persistent gap is confirmed: passive events were treated as the sole
completeness mechanism and the health model did not verify end-to-end progress.

## Options considered

### A. Keep passive events and rely on operator backfill after alerts — rejected

This preserves low latency but keeps correctness dependent on an update mechanism known
to omit some public-channel events. The present freshness signal also requires an
operator to notice and interpret staleness before the gap grows.

### B. Passive events plus checkpoint-driven startup and periodic reconciliation — recommended

Keep events for low latency, but poll forward from the durable source checkpoint on
startup, after reconnect, and at a bounded interval. Feed fetched messages through the
existing idempotent persistence core, use overlap where edit/media grouping requires
it, and record a remote-source observation separately from committed progress. This
directly closes the incident class without adding a broker or second worker.

### C. Polling-only ingestion — rejected as the default

Polling can provide completeness but increases steady API traffic and detection latency
and weakens prompt edit/delete handling. It remains the correctness backstop rather
than replacing low-latency events.

### D. Replace Telethon or add a queue/service immediately — deferred

The incident does not show that the existing library, database, or single-worker
topology is incapable of event-plus-poll reconciliation. A dependency or topology
change adds security, migration, and operating risk and requires separate evidence.

## Recommendation

Approve a three-task P0 sequence:

1. Make listener failure observable and fatal: configure redacted Telethon/worker
   logging, supervise connection/consumer/heartbeat tasks as one lifecycle, and make
   health fail if the consumer or reconciliation loop stops.
2. Make database checkpoint polling the source-completeness boundary: reconcile at
   startup, after reconnect, and periodically with bounded pages, rate/flood handling,
   overlap/edit semantics, idempotent replay, and an explicit last-remote-observed state.
3. Deploy the controls, reconcile `29203` through the then-current remote head, verify
   canonical/source/public effects, and rehearse disconnect/restart/missed-event recovery
   with alert fire-and-recover evidence.

`catch_up()` or a file-backed session state may supplement this design if refinement
proves value, but neither may replace explicit checkpoint polling for completeness.

## Proposed task boundaries

- E15-T1 owns process lifecycle supervision, redacted exception logging, consumer and
  reconciliation heartbeats, and truthful container health.
- E15-T2 owns startup/reconnect/periodic polling, checkpoint/overlap semantics, remote
  progress observation, idempotent event/poll convergence, and bounded provider use.
- E15-T3 owns production rollout, missed-range recovery, reconciliation evidence,
  alert/outage rehearsal, and B-003/M4 handoff.

## Risks and open questions

- Select a poll interval and maximum catch-up batch that meet freshness expectations
  without unnecessary Telegram API load or flood waits.
- Define a bounded recent-message window for edit/deletion reconciliation; Telegram
  deletion notifications and absence-from-history semantics require explicit negative
  tests and conservative handling.
- Decide whether remote-head state belongs in the existing ingest-run checkpoint or a
  separate worker-status record without weakening transaction guarantees.
- Avoid overlapping event/poll races with the existing advisory lock while preserving
  throughput for album bursts and restart recovery.
- Ensure diagnostic labels remain bounded and contain message IDs/counts/timestamps
  only where operationally necessary—never source text, contacts, or session data.
- Determine how freshness alerts are delivered with the existing single-host baseline;
  E15 must not silently depend on unapproved E14 observability infrastructure.
- Coordinate completion evidence with E8-T1/T2/T3/T5 without rewriting their historical
  delivered scope or creating circular task dependencies.

## Invalidation triggers

- Telegram access moves from the verified user session/channel or to a different API.
- The ingestion topology changes from one worker or adds a broker/replica.
- Canonical source identity, checkpoint, revision, deletion, media-group, or offer
  persistence semantics change materially.
- New evidence proves the missed range reached the processor or identifies a different
  failure boundary requiring a materially different solution.
- Security policy changes session storage, production telemetry, or source-data handling.

## Exit checklist

- [x] The question is answered within the stated scope.
- [x] Verified facts, inference, and the unrecoverable historical uncertainty are distinct.
- [x] Affected decisions and domain/workflow documents are linked.
- [x] Viable recovery/health options and their tradeoffs are evaluated.
- [x] Proposed task boundaries, dependencies, tests, rollout, and risks are identified.
- [x] No production or disposable proof code was created.
- [x] `revision` represents the material content submitted.
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of spike
revision 1 permits task refinement/promotion and implementation planning; it does not
authorize code, deployment, restart, or backfill.

