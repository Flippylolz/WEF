---
id: M4
title: "Live Telegram updates"
status: planned
---

# M4: Live Telegram updates

## Outcome

The historical checkpoint is reconciled with Telegram, and one hardened worker processes new/edit/delete events through the same ingestion core.

## Current constraints

- M3 and D-003 gate live channel access; credentials and sessions stay only in approved secret paths.
- The recurring geocoder is revalidated under D-002 (resolved: retain Geoapify) before always-on ingestion.
- The worker remains single-replica, restartable, idempotent, and non-blocking for the public API.
- E8-T5 depends only on E8-T3 and E8-T4; deferred backup task E7-T5 is not a dependency.
- Release `3ee56a5` created and started the production worker service on 2026-08-26; task completion still requires verified live entity/event delivery, gap reconciliation, and outage-recovery evidence.
- On 2026-08-27 the connected, Docker-healthy worker remained at checkpoint `29202`
  while Telegram advanced through at least `29257`; production missed six parser-classified
  offer candidates. [E15](../epics/E15-telegram-ingestion-reliability/README.md) is the
  approved blocker-priority recovery epic. Spike/plan revision 1 are approved under
  AD-039/AD-040; all three tasks are promoted and E15-T1 is dependency-ready.

## Included epic/task definitions

### [E8: Future Telegram live ingestion](../epics/E8-telegram-live-ingestion/README.md)

- [E8-T1: Confirm channel identity and access](../epics/E8-telegram-live-ingestion/tasks/E8-T1-confirm-channel-identity-and-access.md) — `in_progress`
- [E8-T2: Implement secure Telethon session and backfill](../epics/E8-telegram-live-ingestion/tasks/E8-T2-implement-secure-telethon-session-and-backfill.md) — `in_progress`
- [E8-T3: Implement live new/edit/delete processing](../epics/E8-telegram-live-ingestion/tasks/E8-T3-implement-live-new-edit-delete-processing.md) — `in_progress`
- [E8-T4: Revalidate geocoder for recurring ingestion](../epics/E8-telegram-live-ingestion/tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md) — `done`
- [E8-T5: Production reconciliation and worker alerting](../epics/E8-telegram-live-ingestion/tasks/E8-T5-production-reconciliation-and-worker-alerting.md) — `in_progress`

### [E15: Telegram ingestion reliability recovery](../epics/E15-telegram-ingestion-reliability/README.md)

- [E15-T1: Supervise and observe the Telegram event pipeline](../epics/E15-telegram-ingestion-reliability/tasks/E15-T1-supervise-and-observe-event-pipeline.md) — P0 `ready`
- [E15-T2: Add checkpoint-driven Telegram reconciliation](../epics/E15-telegram-ingestion-reliability/tasks/E15-T2-add-checkpoint-driven-reconciliation.md) — P0 `draft`; depends on T1
- [E15-T3: Recover the production gap and prove outage recovery](../epics/E15-telegram-ingestion-reliability/tasks/E15-T3-recover-gap-and-prove-outage-recovery.md) — P0 `draft`; depends on T1/T2

Cancelled and deferred candidates remain linked for traceability but are not completion requirements unless an approved revision restores them to required scope.

## Exit evidence

- [ ] Channel identity/access and recurring geocoder gates are resolved for current production conditions.
- [ ] Backfill from the historical checkpoint is restartable, idempotent, and reconciled.
- [ ] New/edit/delete events preserve revisions and visibility semantics through the shared ingestion core.
- [ ] Passive event loss is recovered by bounded checkpoint-driven reconciliation at
  startup, reconnect, and steady state without full re-import or duplicate canonical data.
- [ ] A single worker exposes truthful transport/consumer/reconciliation health,
  remote/local lag, stale/gap alerts, and rehearsed session rotation/outage recovery.
- [ ] The 2026-08-27 missed range is reconciled through the reviewed production path
  with redacted source/checkpoint/canonical evidence.
- [ ] Every required task has been promoted, approved, dependency-gated, implemented on its dedicated branch, and completed with definition-of-done evidence.

## Status rule

`planned` records the current outcome checkpoint only; it grants no implementation permission. Change this milestone to `done` only when all required exit evidence and task completion records exist under the [workflow](../workflow/README.md).
