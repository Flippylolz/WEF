---
schema: ai-workflow/epic@1
id: E3
title: "Database, geocoding, and media pipeline"
status: planning
milestones: [M1, M2]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E3: Database, geocoding, and media pipeline

## Outcome

idempotent canonical data and web-safe media with reviewed map coordinates.

## Approval state

- Epic workspace status: `planning`; spike revision 3 is approved and implementation-plan revision 3 awaits owner approval.
- [Spike](SPIKE.md): `approved`, revision 3.
- [Implementation plan](IMPLEMENTATION_PLAN.md): material revision 3 `awaiting_approval` with approval `pending`; historical revision 2 remains the completed authorization record for done E3-T1 only.
- E3-T1 is `done`. E3-T2 through E3-T5 are promoted under `tasks/` as `draft` with satisfied spike gates and blocked implementation gates until plan revision 3 is approved. They are not actionable for code.

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
- [ADR-021](../../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md) — remains `proposed`; spike/plan approval does not accept it.
- [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md) — remains deferred.

## Promoted tasks

- [E3-T1: Create M1 schema, migrations, and deterministic seed](tasks/E3-T1-create-schema-and-migrations.md) — `done`, P0/L, M1
- [E3-T2: Implement idempotent persistence and reprocessing](tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md) — `draft`, P0/L, M1; spike gate satisfied; implementation gate blocked pending plan approval
- [E3-T3: Implement geocoder abstraction and cache](tasks/E3-T3-implement-geocoder-abstraction-and-cache.md) — `draft`, P0/L, M1; spike gate satisfied; implementation gate blocked; D-002 deferred; hosted comparison hard completion gate; B-008 unresolved
- [E3-T4: Implement media storage and derivatives](tasks/E3-T4-implement-media-storage-and-derivatives.md) — `draft`, P0/L, M2; spike gate satisfied; implementation gate blocked; independent of E3-T3 after E3-T2
- [E3-T5: Import and review the complete dataset](tasks/E3-T5-import-and-review-the-complete-dataset.md) — `draft`, P0/L, M2; spike gate satisfied; implementation gate blocked; depends on E3-T2/T3/T4

## Proposed tasks

None remaining for E3-T2–T5. Candidates were moved—not copied—into `tasks/` after spike revision 3 approval.

## Cross-epic dependencies

- Incoming: E3-T1 depends on E1-T3.
- Incoming: E3-T2 depends on E2-T2 and E3-T1.
- Incoming: E3-T3 depends on E2-T2, E3-T1, and E3-T2; D-002 remains deferred for recurring selection.
- Incoming: E3-T4 depends on E2-T3, E3-T1, and E3-T2; deliberately independent of E3-T3.
- Incoming: E3-T5 depends on satisfied E2-T5 plus E3-T2, E3-T3, and E3-T4.
- Outgoing: synthetic M1 E4-T1 depends on E3-T1; publishing non-fixture coordinates still requires E3-T3.
- Outgoing: E4-T3 depends on E3-T4.
- Outgoing: E4-T4 depends on E3-T5.
- Outgoing: E6-T2 depends on E3-T4.
- Outgoing: E6-T3 depends on E3-T2.
- Outgoing: E6-T4 depends on E3-T1.
- Outgoing: E6-T5 depends on E3-T1.
- Outgoing: E7-T6 depends on E3-T5.
- Outgoing: E8-T2 depends on E3-T2.
- Outgoing: E8-T4 depends on E3-T3.

Delivery after plan approval: T2 first, then T3 and T4 may proceed independently, then T5. Do not serialize T4 behind T3.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md).

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [task schema](../../workflow/templates/TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
