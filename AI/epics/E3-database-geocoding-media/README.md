---
schema: ai-workflow/epic@1
id: E3
title: "Database, geocoding, and media pipeline"
status: draft
milestones: [M1, M2]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E3: Database, geocoding, and media pipeline

## Outcome

idempotent canonical data and web-safe media with reviewed map coordinates.

## Approval state

- Epic workspace status: `draft`.
- [Spike](SPIKE.md): `draft`, revision 1, owner approval pending, research only, no code.
- [Implementation plan](IMPLEMENTATION_PLAN.md): `draft`, revision 1, blocked with no approved spike revision and no executable task sequence.
- Every file in `proposed-tasks/` is non-actionable. No implementation, scaffold, migration, infrastructure change, generated executable artifact, or proof code is approved.
- No `tasks/` directory exists; it may be created only when an approved candidate is promoted after spike approval.

## Milestones

[M1](../../milestones/M1-vertical-proof.md), [M2](../../milestones/M2-historical-dataset-ready.md)

## Governing domain documents

- [Data](../../data/README.md)
- [Contracts](../../contracts/README.md)
- [Ingestion](../../ingestion/README.md)
- [Security](../../security/README.md)
- [Decisions](../../decisions/README.md)

## Governing decisions and deferred gates

- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-006](../../decisions/adr/ADR-006-shared-ingestion-core.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)
- [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md)

## Proposed tasks

- [E3-T1: Create schema and migrations](proposed-tasks/E3-T1-create-schema-and-migrations.md) — `proposed`, P0/L, M1
- [E3-T2: Implement idempotent persistence and reprocessing](proposed-tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md) — `proposed`, P0/L, M1
- [E3-T3: Implement geocoder abstraction and cache](proposed-tasks/E3-T3-implement-geocoder-abstraction-and-cache.md) — `proposed`, P0/L, M1
- [E3-T4: Implement media storage and derivatives](proposed-tasks/E3-T4-implement-media-storage-and-derivatives.md) — `proposed`, P0/L, M2
- [E3-T5: Import and review the complete dataset](proposed-tasks/E3-T5-import-and-review-the-complete-dataset.md) — `proposed`, P0/L, M2

## Cross-epic dependencies

- Incoming: E3-T1 depends on E1-T3.
- Incoming: E3-T2 depends on E2-T2.
- Incoming: E3-T3 depends on E2-T2.
- Incoming: E3-T4 depends on E2-T3.
- Incoming: E3-T5 depends on E2-T5.
- Outgoing: E4-T1 depends on E3-T1.
- Outgoing: E4-T1 depends on E3-T3.
- Outgoing: E4-T3 depends on E3-T4.
- Outgoing: E4-T4 depends on E3-T5.
- Outgoing: E6-T2 depends on E3-T4.
- Outgoing: E6-T3 depends on E3-T2.
- Outgoing: E6-T4 depends on E3-T1.
- Outgoing: E6-T5 depends on E3-T1.
- Outgoing: E7-T6 depends on E3-T5.
- Outgoing: E8-T2 depends on E3-T2.
- Outgoing: E8-T4 depends on E3-T3.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md). Each workflow candidate is authoritative only in the single linked `proposed-tasks/` file above; its `legacy-roadmap:*` source value records non-path provenance.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [proposed-task schema](../../workflow/templates/PROPOSED_TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
