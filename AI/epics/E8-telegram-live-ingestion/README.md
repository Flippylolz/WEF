---
schema: ai-workflow/epic@1
id: E8
title: "Future Telegram live ingestion"
status: in_progress
milestones: [M4]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E8: Future Telegram live ingestion

## Outcome

new, edited, and deleted channel posts are processed safely without changing public contracts.

## Approval state

- Epic workspace status: `in_progress`.
- [Spike](SPIKE.md): `approved`, revision 2 (AD-031).
- [Implementation plan](IMPLEMENTATION_PLAN.md): `approved`, revision 5; authorizes E8-T1, E8-T4, E8-T2, E8-T3, and E8-T5.
- [E8-T1](tasks/E8-T1-confirm-channel-identity-and-access.md): promoted, `done`.
- [E8-T4](tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md): promoted, `done`.
- [E8-T2](tasks/E8-T2-implement-secure-telethon-session-and-backfill.md): promoted, `done` (backfill, session, and live media acquisition; [PRODUCTION_EVIDENCE.md](PRODUCTION_EVIDENCE.md)).
- [E8-T3](tasks/E8-T3-implement-live-new-edit-delete-processing.md): promoted, `in_progress` (real authorized subscription is running; no real passive edit/delete callback was observed).
- [E8-T5](tasks/E8-T5-production-reconciliation-and-worker-alerting.md): promoted, `in_progress` (production gap and outage acceptance are satisfied by E15; passive edit/delete evidence remains open upstream).
- On 2026-08-27 the connected production worker missed Telegram messages `29203`
  through at least `29257` while remaining Docker-healthy. Selected blocker-priority
  [E15](../E15-telegram-ingestion-reliability/README.md) owns the independently approved
  reliability remediation and production recovery; E8's delivered history is preserved.
- On 2026-08-28 release `7184cc2d67a` reconciled every ID through observed head
  `29335`, repeated idempotently, and proved restart plus health-signal recovery while
  public readiness stayed available. See the redacted
  [E15 production evidence](../E15-telegram-ingestion-reliability/PRODUCTION_EVIDENCE.md).

- On 2026-08-31 release `b71c99f` verified live media acquisition for reconciled ids
  `29415`–`29434`; release `ab4f17a` added passive-event monitoring with NUC cron watch.
  See [PRODUCTION_EVIDENCE.md](PRODUCTION_EVIDENCE.md) and [B003 observation runbook](B003_OBSERVATION_RUNBOOK.md).

## Milestones

[M4](../../milestones/M4-live-telegram-updates.md)

## Governing domain documents

- [Ingestion](../../ingestion/README.md)
- [Data](../../data/README.md)
- [Operations](../../operations/README.md)
- [Security](../../security/README.md)
- [Decisions](../../decisions/README.md)

## Governing decisions and deferred gates

- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-006](../../decisions/adr/ADR-006-shared-ingestion-core.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-010](../../decisions/adr/ADR-010-isolate-wef-shared-nuc.md)
- [ADR-015](../../decisions/adr/ADR-015-defer-backups.md)
- [ADR-021](../../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md)
- [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md) — resolved (retain Geoapify)
- [D-003](../../decisions/deferred/D-003-telegram-channel-access.md)

## Tasks

- [E8-T1: Confirm channel identity and access](tasks/E8-T1-confirm-channel-identity-and-access.md) — `done`, P2/S, M4
- [E8-T4: Revalidate geocoder for recurring ingestion](tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md) — `done`, P2/M, M4
- [E8-T2: Implement secure Telethon session and backfill](tasks/E8-T2-implement-secure-telethon-session-and-backfill.md) — `done`, P2/L, M4
- [E8-T3: Implement live new/edit/delete processing](tasks/E8-T3-implement-live-new-edit-delete-processing.md) — `in_progress`, P2/L, M4
- [E8-T5: Production reconciliation and worker alerting](tasks/E8-T5-production-reconciliation-and-worker-alerting.md) — `in_progress`, P2/L, M4

## Proposed tasks

None remaining for E8.

## Cross-epic dependencies

- Incoming: E8-T2 depends on E3-T2.
- Incoming: E8-T4 depends on E3-T3.
- Downstream acceptance: E15-T1/T2/T3 provide the new source-completeness, truthful-health,
  and recovery evidence needed before E8/B-003/M4 can close; this factual handoff does
  not retroactively change E8's approved task dependencies.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md). Production starts `telegram-worker` with the application. Credentials/session, entity access, gap reconciliation, outage recovery, and live media acquisition are verified. B-003 remains narrowly open for real passive edit/delete callbacks; use [B003 observation runbook](B003_OBSERVATION_RUNBOOK.md) when an event occurs.
