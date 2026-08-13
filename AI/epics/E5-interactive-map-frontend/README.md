---
schema: ai-workflow/epic@1
id: E5
title: "Interactive map frontend"
status: in_progress
milestones: [M1, M3]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E5: Interactive map frontend

## Outcome

a responsive, accessible map/list/detail experience over dated offers.

## Approval state

- Epic workspace status: `in_progress` for the synthetic M1 map/filter boundary.
- [Spike](SPIKE.md): `approved`, revision 2.
- [Implementation plan](IMPLEMENTATION_PLAN.md): `approved`, revision 2, sequencing E5-T1 then E5-T2.
- E5-T1 is `in_progress`; E5-T2 remains promoted/`draft` pending E5-T1 ancestry; E5-T3 through E5-T5 remain proposed.

## Milestones

[M1](../../milestones/M1-vertical-proof.md), [M3](../../milestones/M3-public-dockerized-mvp.md)

## Governing domain documents

- [Product](../../product/README.md)
- [Contracts](../../contracts/README.md)
- [Architecture](../../architecture/README.md)
- [Security](../../security/README.md)
- [Decisions](../../decisions/README.md)

## Governing decisions and deferred gates

- [ADR-002](../../decisions/adr/ADR-002-grouped-location-development-map.md)
- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-004](../../decisions/adr/ADR-004-maplibre-openfreemap.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)

## Promoted tasks

- [E5-T1: Build map shell and grouped pin interaction](tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md) — `in_progress`, P0/L, M1
- [E5-T2: Add URL-backed filters and viewport querying](tasks/E5-T2-add-url-backed-filters-and-viewport-querying.md) — `draft`, P0/L, M1

## Proposed tasks

- [E5-T3: Build offer detail and media gallery](proposed-tasks/E5-T3-build-offer-detail-and-media-gallery.md) — `proposed`, P0/L, M3
- [E5-T4: Complete responsive list/map accessibility](proposed-tasks/E5-T4-complete-responsive-list-map-accessibility.md) — `proposed`, P1/L, M3
- [E5-T5: Performance and production UX pass](proposed-tasks/E5-T5-performance-and-production-ux-pass.md) — `proposed`, P1/M, M3

## Cross-epic dependencies

- Incoming: E5-T1 depends on E1-T2.
- Incoming: E5-T1 depends on E4-T2 for the clickable dated-result panel.
- Incoming: E5-T2 depends on E4-T2.
- Incoming: E5-T3 depends on E4-T3.
- Incoming: E5-T5 depends on E4-T4.
- Outgoing: E6-T1 depends on E5-T3.
- Outgoing: E6-T2 depends on E5-T3.
- Outgoing: E6-T6 depends on E5-T3.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md). Each workflow candidate is authoritative only in the single linked `proposed-tasks/` file above; its `legacy-roadmap:*` source value records non-path provenance.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [proposed-task schema](../../workflow/templates/PROPOSED_TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
