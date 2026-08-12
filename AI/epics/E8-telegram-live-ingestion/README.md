---
schema: ai-workflow/epic@1
id: E8
title: "Future Telegram live ingestion"
status: draft
milestones: [M4]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E8: Future Telegram live ingestion

## Outcome

new, edited, and deleted channel posts are processed safely without changing public contracts.

## Approval state

- Epic workspace status: `draft`.
- [Spike](SPIKE.md): `draft`, revision 1, owner approval pending, research only, no code.
- [Implementation plan](IMPLEMENTATION_PLAN.md): `draft`, revision 1, blocked with no approved spike revision and no executable task sequence.
- Every file in `proposed-tasks/` is non-actionable. No implementation, scaffold, migration, infrastructure change, generated executable artifact, or proof code is approved.
- No `tasks/` directory exists; it may be created only when an approved candidate is promoted after spike approval.

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
- [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md)
- [D-003](../../decisions/deferred/D-003-telegram-channel-access.md)

## Proposed tasks

- [E8-T1: Confirm channel identity and access](proposed-tasks/E8-T1-confirm-channel-identity-and-access.md) — `proposed`, P2/S, M4
- [E8-T2: Implement secure Telethon session and backfill](proposed-tasks/E8-T2-implement-secure-telethon-session-and-backfill.md) — `proposed`, P2/L, M4
- [E8-T3: Implement live new/edit/delete processing](proposed-tasks/E8-T3-implement-live-new-edit-delete-processing.md) — `proposed`, P2/L, M4
- [E8-T4: Revalidate geocoder for recurring ingestion](proposed-tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md) — `proposed`, P2/M, M4
- [E8-T5: Production reconciliation and worker alerting](proposed-tasks/E8-T5-production-reconciliation-and-worker-alerting.md) — `proposed`, P2/L, M4

## Cross-epic dependencies

- Incoming: E8-T2 depends on E3-T2.
- Incoming: E8-T4 depends on E3-T3.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md). Each workflow candidate is authoritative only in the single linked `proposed-tasks/` file above; its `legacy-roadmap:*` source value records non-path provenance.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [proposed-task schema](../../workflow/templates/PROPOSED_TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
