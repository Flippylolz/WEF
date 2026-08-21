---
schema: ai-workflow/epic@1
id: E8
title: "Future Telegram live ingestion"
status: ready
milestones: [M4]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E8: Future Telegram live ingestion

## Outcome

new, edited, and deleted channel posts are processed safely without changing public contracts.

## Approval state

- Epic workspace status: `ready`.
- [Spike](SPIKE.md): `approved`, revision 2 (AD-031).
- [Implementation plan](IMPLEMENTATION_PLAN.md): `approved`, revision 2; authorizes E8-T1 and E8-T4.
- [E8-T1](tasks/E8-T1-confirm-channel-identity-and-access.md): promoted, `in_progress` (secrets/live resolve open).
- [E8-T4](tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md): promoted, `in_progress`.
- E8-T2, T3, T5 remain proposed until later plan revisions.

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

- [E8-T1: Confirm channel identity and access](tasks/E8-T1-confirm-channel-identity-and-access.md) — `in_progress`, P2/S, M4
- [E8-T4: Revalidate geocoder for recurring ingestion](tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md) — `in_progress`, P2/M, M4

## Proposed tasks

- [E8-T2: Implement secure Telethon session and backfill](proposed-tasks/E8-T2-implement-secure-telethon-session-and-backfill.md) — `proposed`, P2/L, M4
- [E8-T3: Implement live new/edit/delete processing](proposed-tasks/E8-T3-implement-live-new-edit-delete-processing.md) — `proposed`, P2/L, M4
- [E8-T5: Production reconciliation and worker alerting](proposed-tasks/E8-T5-production-reconciliation-and-worker-alerting.md) — `proposed`, P2/L, M4

## Cross-epic dependencies

- Incoming: E8-T2 depends on E3-T2.
- Incoming: E8-T4 depends on E3-T3.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md). Live worker enablement remains E8-T5 after Telegram secrets and remaining D-003 live-access gates.
