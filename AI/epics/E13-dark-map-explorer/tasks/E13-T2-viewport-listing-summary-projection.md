---
schema: ai-workflow/task@1
id: E13-T2
epic: E13
title: "Add a paginated viewport listing-summary projection"
status: ready
revision: 1
priority: P1
size: L
milestone: M4
dependencies: []
requirement_ids: [P-001, P-003]
decision_ids: [ADR-002, ADR-003, ADR-012, ADR-013]
deferred_decision_ids: []
promotion:
  source: ../SPIKE.md#proposed-task-boundaries
  promoted_by: "ZCode agent (owner-directed E13 implementation mission)"
  promoted_at: "2026-08-26T18:45:03Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "ZCode agent (owner-directed E13 implementation mission)"
  verified_at: "2026-08-26T18:45:03Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "ZCode agent (owner-directed E13 implementation mission)"
  verified_at: "2026-08-26T18:45:03Z"
dependency_gate:
  status: satisfied
  verified_by: "ZCode agent (owner-directed E13 implementation mission)"
  verified_at: "2026-08-26T18:45:03Z"
  evidence: []
branch:
  required: true
  name: feat/E13-T2-viewport-listing-summary
  task_id: E13-T2
  one_task_only: true
  created_at: "2026-08-26T18:45:03Z"
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E13-T2: Add a paginated viewport listing-summary projection

## Outcome

A public, additive read endpoint returns cursor-paginated offer summaries
for the current viewport and filters, each keyed to its public parent
location, so the frontend rail can browse dated listings without per-location
N+1 requests while the backend keeps filtering, visibility, sorting, and
pagination authority.

## Scope

- `GET /api/v1/listings` (operation id `listViewportListings`) accepting the
  existing map query filters (required `bbox`, price/area/rooms/district/
  market/content/publication/quick filter) plus `cursor` and `limit`
  (1–50, default 20).
- Response: `items` of listing summaries (the established public-safe offer
  summary fields plus `published_at`) each embedding the parent location
  summary (`id`, `display_name`, `display_address`, `district`,
  `confidence`) and the offer id; plus `matching_count` and `next_cursor`.
- Deterministic newest-first order `published_at DESC, offer_id DESC` with a
  versioned opaque keyset cursor reusing the `CursorCodec` pattern; no
  relevance or availability scoring.
- Reuse the public gates (location accepted, in scope, geocoded point,
  offer visible) and the existing filter predicate semantics from the map
  query; count is bounded to the same filtered predicate.
- Catalog feature four-layer implementation (interface/application/
  infrastructure), `composition.py` and `app.py` wiring, presenter, ETag-free
  plain `Cache-Control: no-store`-consistent behavior with existing browse
  endpoints, 422 on invalid cursor, tests at every layer.
- Regenerate `contracts/openapi/v1.json` and `apps/web/src/generated/api.ts`
  (additive only; oasdiff must report no breaking changes).

## Out of scope

- Frontend consumption (E13-T3), media thumbnails, text search, saved
  per-user ordering, availability language.

## Affected modules and contracts

- `apps/backend/src/wef_backend/features/catalog/` (router, presenter,
  application use case + port + DTOs, infrastructure adapter method).
- `apps/backend/src/wef_backend/{composition,app}.py`.
- `contracts/openapi/v1.json`, `apps/web/src/generated/api.ts`.
- `apps/web/src/lib/catalog-api.ts` gains only the typed fetch wrapper.

## Acceptance criteria

- [ ] Endpoint returns filter-matching visible offers within the bbox,
      newest-first, with parent location summary fields only.
- [ ] Cursor pagination is deterministic and bounded (limit ≤ 50, lookahead
      behavior identical to the location-offers endpoint); invalid cursors
      return 422; empty/last pages return `next_cursor: null`.
- [ ] Non-public locations/offers are never returned; confidence is exposed
      only as the coarse public indicator.
- [ ] `make contract-generate` output committed; `make contract-check`,
      lint, typecheck, and both ≥90% coverage floors pass; oasdiff shows no
      breaking changes.
- [ ] Backend tests cover filters, bbox bounds, ordering ties, cursor edge
      cases, and the visibility gates.

## Test plan

- Unit: use case (order, cursor encode/decode, limit clamping), DTO and
  presenter mapping.
- Integration: adapter against PostGIS fixtures (bbox intersection, filter
  predicate parity with the map query, visibility gates, count correctness).
- Contract: regenerated JSON/types committed and checked.

## Rollout and rollback

- Additive API release; unused by the frontend until E13-T3. Rollback is the
  prior backend image; no data migration.

## Ready checklist

- [x] Authoritative under `tasks/`; promoted from the approved spike.
- [x] Spike and implementation gates reference approved revision 1.
- [x] No dependencies; dependency gate satisfied with empty evidence.
- [x] Scope matches implementation plan revision 1.
