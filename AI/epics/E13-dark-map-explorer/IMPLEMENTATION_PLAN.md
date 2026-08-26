---
schema: ai-workflow/implementation-plan@1
epic: E13
title: "Dark map-first listing explorer delivery"
status: approved
revision: 1
spike_revision: 1
task_sequence:
  - id: E13-T1
    revision: 1
  - id: E13-T2
    revision: 1
  - id: E13-T3
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: "ZCode agent (owner-directed E13 implementation mission under AD-009/AD-038)"
  decided_at: "2026-08-26T18:45:03Z"
  approved_revision: 1
  evidence: "AD-038; owner instruction 2026-08-26 to implement epic 13, merge, deploy, and test; spike revision 1 approved"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E13 implementation plan: Dark map-first listing explorer

## Objective

Deliver the spike's recommended Option C as three sequential tasks on `main`,
one branch/PR per task, preserving E4/E5 contract compatibility and the
governing ADRs (grouped location pins, no availability inference,
MapLibre/OpenFreeMap, backend authority, committed OpenAPI).

The owner's assignment (AD-038) adopts the spike recommendation and resolves
its "meaning of listing" question: the rail's primary result unit becomes the
dated offer (listing); grouped locations remain the map pin entity and stay
reachable through pins, favorites, and the selected-location view.

## Task sequence

1. **E13-T1 — dark application shell and compact filter experience.**
   Frontend-only slice over existing contracts (spike Option B boundary):
   dark tokens and dark map style, 56–64 px application bar, persistent left
   discovery rail `clamp(22rem, 30vw, 26rem)` with its own scroll region,
   filter chips plus a full-form drawer replacing the always-expanded right
   form, sticky results header, immediate grouped-location cards (labeled as
   places), one attribution surface, and the existing mobile map-first
   sheet/full-list flow restyled for dark. No functional text search input is
   shipped (no contract exists).
2. **E13-T2 — viewport listing-summary projection.**
   Backend/OpenAPI/generated-client slice: `GET /api/v1/listings` returning
   cursor-paginated, filter-matching offer summaries joined to their public
   parent location, newest-first with a deterministic keyset cursor
   (`published_at DESC, offer_id DESC`), reusing `MapQueryParams` filters,
   the existing public visibility gates, and the `CursorCodec` pattern.
3. **E13-T3 — selectable listing rail and coordinated map behavior.**
   Frontend integration slice over T1+T2: paginated offer cards in the rail
   with Load more, card/pin hover-focus-selection synchronization, parent-pin
   selection with conditional recentering (no map remount), a selected
   location/offer rail view with Back to results (scroll/focus restore), and
   preservation of keyboard, mobile, loading/empty/error, degraded-map, and
   detail-drawer behavior.

Tasks 1 and 2 are independent; task 3 depends on both and branches from
`main` only after both are merged.

## Modules and contracts

- `apps/web/src/app/{layout,page,globals.css}` — shell structure, dark
  tokens, viewport/theme color.
- `apps/web/src/components/map-explorer.tsx`, `map-filter-controls.tsx`,
  `warsaw-map.tsx`, `quick-filter-bar.tsx`, `user-toolbar.tsx` — rail, chips,
  drawer, map restyle, coordination.
- `apps/web/src/lib/{catalog-api,map-search-params}.ts`,
  `apps/web/src/generated/api.ts` — generated contract consumption only.
- `apps/web/messages/en.json` — English strings for new controls; no
  availability language.
- Backend `features/catalog` four layers (interface/application/domain/
  infrastructure), `composition.py`, `app.py` — new projection endpoint.
- `contracts/openapi/v1.json` — regenerated, additive-only (oasdiff must
  report no breaking changes).
- `scripts/deploy/smoke.sh` — map-style reachability check follows the
  verified dark style URL; public-HTTPS smoke unchanged.

Verified during planning (2026-08-26): `https://tiles.openfreemap.org/styles/dark`
serves a valid OpenMapTiles style JSON (47 layers) with the same attribution
requirements; `liberty` remains the light fallback.

## Tests

- Backend: unit tests for the new use case (filters, cursor edge cases,
  bounds), adapter tests against PostGIS fixtures (bbox + visibility gates,
  deterministic order), presenter/router contract tests; coverage floor 90%.
- Frontend: component tests for chips/drawer apply-clear lifecycle, rail
  states (loading, updating, empty, error), card selection and Back to
  results focus restoration, map coordination props, dark token smoke;
  a11y assertions preserved; coverage floor 90%.
- Contract: `make contract-generate` commits `v1.json` + `api.ts`;
  `make contract-check` and oasdiff breaking-change gate pass.
- E2e: existing Playwright map-explorer suite stays green with the disabled
  map env; assertions updated where copy/structure changed.

## Migrations, rollout, and rollback

- No database migration; the projection reuses existing tables/indexes.
- Rollout is the standard main-merge → release workflow → NUC deploy with
  health checks; each task is independently revertible by redeploying the
  prior release image (T1 visual only, T2 additive endpoint unused until T3).
- Rollback boundaries: T3 must not ship without T2 merged; production
  rollback reverts web/backend images together to the prior SHA.

## Risks

- Dark tile style legibility over district overlays — mitigated by
  restrained overlay colors and the validation matrix in the UX design.
- Rail performance at 700+ locations — T1 keeps the existing single list
  (bounded by bbox); T3 paginates offers (20/page, bounded prefetch) and must
  not render hundreds of cards.
- Selected-item continuity across filter/viewport changes — T3 keeps the
  selected snapshot and offers Back to results instead of silent changes.
- Duplicate attribution — T1 removes the custom overlay and keeps exactly one
  MapLibre attribution control.

## Out of scope

- Free-text search, draw-on-map, recommendations, availability/relevance
  scoring, media thumbnails in the rail, facet data normalization, new map
  vendor or production dependency.
