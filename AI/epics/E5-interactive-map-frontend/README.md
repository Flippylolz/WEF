---
schema: ai-workflow/epic@1
id: E5
title: "Interactive map frontend"
status: ready
milestones: [M1, M3]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E5: Interactive map frontend

## Outcome

a responsive, accessible map/list/detail experience over dated offers.

## Approval state

- Epic workspace status: `ready`; E5-T1 and E5-T2 are complete and the full remaining sequence is approved.
- [Spike](SPIKE.md): `approved`, revision 3.
- [Implementation plan](IMPLEMENTATION_PLAN.md): `approved`, revision 3, sequencing E5-T2 through E5-T5 after the documentation branch.
- E5-T1 through E5-T4 are `done` (E5-T4 merged via PR #82); E5-T5 is ready to start once E4-T4 lands.

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

- [E5-T1: Build map shell and grouped pin interaction](tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md) — `done`, P0/L, M1
- [E5-T2: Add URL-backed filters and viewport querying](tasks/E5-T2-add-url-backed-filters-and-viewport-querying.md) — `done`, P0/L, M1
- [E5-T3: Build offer detail and media gallery](tasks/E5-T3-build-offer-detail-and-media-gallery.md) — `done`, P0/L, M3; merged PR #80
- [E5-T4: Complete responsive list/map accessibility](tasks/E5-T4-complete-responsive-list-map-accessibility.md) — `done`, P1/L, M3; merged PR #82
- [E5-T5: Performance and production UX pass](tasks/E5-T5-performance-and-production-ux-pass.md) — `draft`, P1/M, M3; blocked on E4-T4
- [E5-T5: Performance and production UX pass](tasks/E5-T5-performance-and-production-ux-pass.md) — `draft`, P1/M, M3; blocked on E5-T4/E4-T4

## Cross-epic dependencies

- Incoming: E5-T1 depends on E1-T2.
- Incoming: E5-T1 depends on E4-T2 for the clickable dated-result panel.
- Incoming: E5-T2 depends on E4-T2.
- Incoming: E5-T3 depends on E4-T3.
- Incoming: E5-T5 depends on E4-T4.
- Outgoing: E6-T1 depends on E5-T3.
- Outgoing: E6-T2 depends on E5-T3.
- Outgoing: E6-T6 depends on E5-T3.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md). Every E5 task now has one authoritative promoted definition under `tasks/`; promotion metadata preserves its prior roadmap/proposed provenance.

E3/E4 implementation is being delivered by parallel agents. E5 never replaces those dependencies with mocked contracts: E5-T3 and E5-T5 remain blocked until their exact E4 task ancestry is recorded or complete.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [proposed-task schema](../../workflow/templates/PROPOSED_TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
