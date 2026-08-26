---
schema: ai-workflow/epic@1
id: E13
title: "Dark map-first listing explorer"
status: selected
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

- Epic workspace status: `selected`; documentation and research are permitted.
- [Spike](SPIKE.md): `awaiting_approval`, revision 1.
- Production code, generated contracts, migrations, and implementation plans
  remain prohibited until the workflow gates are satisfied.

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

## Candidate task boundaries

- `E13-T1`: Build the dark application shell and compact filter experience.
- `E13-T2`: Add a paginated viewport listing-summary projection.
- `E13-T3`: Build the selectable listing rail and coordinated map interaction.

These are spike outputs only. No proposed or promoted task is actionable.

## Dependencies

- Existing E4 catalog contracts and E5 map/detail interaction remain the
  compatibility baseline.
- Any new listing-summary contract must keep filtering, visibility, confidence,
  availability language, and pagination authoritative in the backend.

## Current constraint

Documentation and research only. This workspace does not authorize production
code, generated contracts, migrations, or implementation until the spike is
approved and an implementation plan is gated.
