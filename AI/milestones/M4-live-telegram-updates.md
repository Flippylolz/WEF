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
- The recurring geocoder is revalidated under D-002 before always-on ingestion.
- The worker remains single-replica, restartable, idempotent, and non-blocking for the public API.
- E8-T5 depends only on E8-T3 and E8-T4; deferred backup task E7-T5 is not a dependency.

## Included epic/task definitions

### [E8: Future Telegram live ingestion](../epics/E8-telegram-live-ingestion/README.md)

- [E8-T1: Confirm channel identity and access](../epics/E8-telegram-live-ingestion/proposed-tasks/E8-T1-confirm-channel-identity-and-access.md) — `proposed`
- [E8-T2: Implement secure Telethon session and backfill](../epics/E8-telegram-live-ingestion/proposed-tasks/E8-T2-implement-secure-telethon-session-and-backfill.md) — `proposed`
- [E8-T3: Implement live new/edit/delete processing](../epics/E8-telegram-live-ingestion/proposed-tasks/E8-T3-implement-live-new-edit-delete-processing.md) — `proposed`
- [E8-T4: Revalidate geocoder for recurring ingestion](../epics/E8-telegram-live-ingestion/proposed-tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md) — `proposed`
- [E8-T5: Production reconciliation and worker alerting](../epics/E8-telegram-live-ingestion/proposed-tasks/E8-T5-production-reconciliation-and-worker-alerting.md) — `proposed`

Cancelled and deferred candidates remain linked for traceability but are not completion requirements unless an approved revision restores them to required scope.

## Exit evidence

- [ ] Channel identity/access and recurring geocoder gates are resolved for current production conditions.
- [ ] Backfill from the historical checkpoint is restartable, idempotent, and reconciled.
- [ ] New/edit/delete events preserve revisions and visibility semantics through the shared ingestion core.
- [ ] A single worker exposes received/committed freshness, stale/connectivity alerts, and rehearsed session rotation/outage recovery.
- [ ] Every required task has been promoted, approved, dependency-gated, implemented on its dedicated branch, and completed with definition-of-done evidence.

## Status rule

`planned` records the current outcome checkpoint only; it grants no implementation permission. Change this milestone to `done` only when all required exit evidence and task completion records exist under the [workflow](../workflow/README.md).
