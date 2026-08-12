---
schema: ai-workflow/epic@1
id: E4
title: "Read API and filter contracts"
status: in_progress
milestones: [M1, M2]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E4: Read API and filter contracts

## Outcome

stable, efficient public endpoints that implement filter semantics once.

## Approval state

- Epic workspace status: `in_progress` for the synthetic M1 map contract.
- [Spike](SPIKE.md): `approved`, revision 2.
- [Implementation plan](IMPLEMENTATION_PLAN.md): `approved`, revision 2, sequencing E4-T1 then E4-T2.
- E4-T1 is `in_progress`; E4-T2 remains promoted/`draft` pending E4-T1 ancestry; E4-T3/T4 remain proposed.

## Milestones

[M1](../../milestones/M1-vertical-proof.md), [M2](../../milestones/M2-historical-dataset-ready.md)

## Governing domain documents

- [Product](../../product/README.md)
- [Contracts](../../contracts/README.md)
- [Architecture](../../architecture/README.md)
- [Security](../../security/README.md)
- [Decisions](../../decisions/README.md)

## Governing decisions and deferred gates

- [ADR-002](../../decisions/adr/ADR-002-grouped-location-development-map.md)
- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-013](../../decisions/adr/ADR-013-committed-openapi-offline-docs.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)

## Promoted task

- [E4-T1: Implement map query service and GeoJSON endpoint](tasks/E4-T1-implement-map-query-service-and-geojson-endpoint.md) — `in_progress`, P0/L, M1
- [E4-T2: Implement facets and location offer collection](tasks/E4-T2-implement-facets-and-location-offer-collection.md) — `draft`, P0/M, M1

## Proposed tasks

- [E4-T3: Implement offer detail](proposed-tasks/E4-T3-implement-offer-detail.md) — `proposed`, P0/M, M2
- [E4-T4: Harden API behavior and performance](proposed-tasks/E4-T4-harden-api-behavior-and-performance.md) — `proposed`, P1/M, M2

## Cross-epic dependencies

- Incoming: synthetic M1 E4-T1 depends on E3-T1; non-fixture publication remains gated by E3-T3.
- Incoming: E4-T3 depends on E3-T4.
- Incoming: E4-T4 depends on E3-T5.
- Outgoing: E5-T1 depends on E4-T2 for map plus selected-location results.
- Outgoing: E5-T2 depends on E4-T2.
- Outgoing: E5-T3 depends on E4-T3.
- Outgoing: E5-T5 depends on E4-T4.
- Outgoing: E6-T1 depends on E4-T3.
- Outgoing: E6-T2 depends on E4-T3.
- Outgoing: E6-T3 depends on E4-T4.
- Outgoing: E6-T5 depends on E4-T3.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md). Each workflow candidate is authoritative only in the single linked `proposed-tasks/` file above; its `legacy-roadmap:*` source value records non-path provenance.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [proposed-task schema](../../workflow/templates/PROPOSED_TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
