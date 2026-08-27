---
schema: ai-workflow/epic@1
id: E13
title: "Dark map-first listing explorer"
status: in_progress
milestones: [M4]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E13: Dark map-first listing explorer

## Outcome

Create a dark, map-first Warsaw property discovery experience in which the map
and a left-hand listing rail behave as one coordinated surface. Filters become
compact, results remain immediately visible, and selecting a listing produces a
clear map highlight and detail transition without forcing the user through the
entire result collection.

## Approval state

- Epic workspace status: `in_progress`; E13-T1 delivered, T2/T3 to follow.
- [Spike](SPIKE.md): `approved`, revision 1 (AD-038).
- [Implementation plan](IMPLEMENTATION_PLAN.md): `approved`, revision 1
  (AD-038), sequencing E13-T1 → E13-T2 → E13-T3.

## Design reference

- [Frontend improvement and interaction design](UX_DESIGN.md)

## Governing domain documents

- [Product experience](../../product/EXPERIENCE.md)
- [Product quality](../../product/QUALITY.md)
- [Architecture](../../architecture/README.md)
- [Repository workflow](../../workflow/README.md)

## Governing decisions

- [ADR-002: Grouped location/development map](../../decisions/adr/ADR-002-grouped-location-development-map.md)
- [ADR-003: Do not infer current availability](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-004: MapLibre and OpenFreeMap](../../decisions/adr/ADR-004-maplibre-openfreemap.md)
- [ADR-012: Backend-centric modular monolith](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-013: Committed OpenAPI and offline docs](../../decisions/adr/ADR-013-committed-openapi-offline-docs.md)

## Promoted tasks

- [E13-T1: Build the dark application shell and compact filter experience](tasks/E13-T1-dark-shell-compact-filters.md) — P1/L, M4
- [E13-T2: Add a paginated viewport listing-summary projection](tasks/E13-T2-viewport-listing-summary-projection.md) — P1/L, M4
- [E13-T3: Build the selectable listing rail and coordinated map behavior](tasks/E13-T3-selectable-listing-rail.md) — P1/L, M4; depends on E13-T1 and E13-T2

## Dependencies

- Existing E4 catalog contracts and E5 map/detail interaction remain the
  compatibility baseline.
- Any new listing-summary contract must keep filtering, visibility, confidence,
  availability language, and pagination authoritative in the backend.

## Current constraint

Implementation proceeds task by task under [implementation plan](IMPLEMENTATION_PLAN.md)
revision 1 (AD-038): one dedicated branch and pull request per task, CI green
before each merge, standard production deploy and smoke verification.
