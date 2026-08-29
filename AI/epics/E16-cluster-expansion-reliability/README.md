---
schema: ai-workflow/epic@1
id: E16
title: "Reliable numbered map-cluster expansion"
status: in_progress
milestones: [M4]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E16: Reliable numbered map-cluster expansion

## Outcome

Restore numbered map-cluster activation so it expands the selected cluster
without corrupting MapLibre's camera state or leaving the map unusable.

## Approval state

- [Spike](SPIKE.md): revision 1 approved by the owner on 2026-08-29.
- [Implementation plan](IMPLEMENTATION_PLAN.md): revision 1 approved by the
  owner on 2026-08-29.
- [E16-T1](tasks/E16-T1-prevent-cluster-expansion-freeze.md): promoted in
  `in_progress`; its approval/dependency gates are satisfied and implementation
  is isolated on its recorded dedicated branch.

## Governing documents

- [Product experience](../../product/EXPERIENCE.md)
- [Product quality](../../product/QUALITY.md)
- [ADR-002: Grouped location/development map](../../decisions/adr/ADR-002-grouped-location-development-map.md)
- [ADR-004: MapLibre and OpenFreeMap](../../decisions/adr/ADR-004-maplibre-openfreemap.md)
- [E5-T1: Map shell and grouped-pin interaction](../E5-interactive-map-frontend/tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md)
- [E13 dark map explorer](../E13-dark-map-explorer/README.md)
