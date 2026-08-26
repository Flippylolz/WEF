---
schema: ai-workflow/task@1
id: E13-T3
epic: E13
title: "Build the selectable listing rail and coordinated map behavior"
status: draft
revision: 1
priority: P1
size: L
milestone: M4
dependencies: [E13-T1, E13-T2]
requirement_ids: [P-004]
decision_ids: [ADR-002, ADR-003, ADR-004, ADR-012]
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
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: feat/E13-T3-selectable-listing-rail
  task_id: E13-T3
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

# E13-T3: Build the selectable listing rail and coordinated map behavior

## Outcome

The discovery rail browses dated offer cards from the E13-T2 projection in
lockstep with the grouped map pins: hover/focus/selection are synchronized,
selecting a card selects and conditionally recenters its parent pin without
remounting the map, and a selected-location/offer view replaces the list
with an explicit Back to results control that restores scroll and focus.

## Scope

- Render paginated listing cards (price/range, area, rooms, published date,
  content/market type, parent location name + district/address, confidence
  label, favorite action keyed to the parent location when signed in) with a
  Load more control; render at most the current page plus a bounded
  prefetch; never request offers per location.
- Card hover/focus drives the parent pin hover halo; card activation marks
  it selected (`aria-selected`/non-color state), selects the parent pin,
  recenters only when the pin lies outside a comfortable padded region, and
  keeps the MapLibre instance alive.
- Pin activation opens the selected-location rail view (existing
  location-offers contract) with its dated offers; a visible Back to
  results restores the prior list, scroll position, and focus; selected
  state survives filter/viewport changes long enough to explain itself,
  then yields to Back to results rather than silently changing selection.
- Viewport refresh keeps prior cards with a compact updating status and
  replaces them only when the query settles; the 300 ms viewport debounce is
  preserved.
- Loading (skeleton rows), empty (No results in this map area + Clear
  filters/Reset map), API error (keep last cards, Retry), degraded-map, and
  detail-drawer flows follow the UX design interaction contract; result
  count is announced once when settled.
- Mobile: card selection returns to the map with the pin selected and a
  compact selected sheet; details keep drawer semantics and deterministic
  focus restoration.

## Out of scope

- Virtualization beyond pagination, media thumbnails, availability
  language, facet normalization, text search.

## Affected modules and contracts

- `apps/web/src/components/map-explorer.tsx`, `warsaw-map.tsx` (imperative
  focus/recenter API), `apps/web/src/lib/catalog-api.ts` (E13-T2 wrapper),
  `apps/web/messages/en.json`, existing detail drawer unchanged.

## Acceptance criteria

- [ ] Rail lists paginated offer cards from `GET /api/v1/listings` with Load
      more and no N+1 location-offer requests while browsing.
- [ ] Card ↔ pin hover/focus/selection synchronization works by pointer and
      keyboard; activation selects the parent pin, conditionally recenters
      without remount, and announces the selected name.
- [ ] Selected location/offer view replaces the rail list (not appended);
      Back to results restores list, scroll position, and focus.
- [ ] Loading/updating/empty/error/degraded states match the interaction
      contract; viewport movement never blanks the rail or moves focus.
- [ ] Keyboard-only user can browse, select, open details, favorite, and
      return; screen-reader announcements cover selection and result count.
- [ ] Unit, a11y, and e2e suites updated and green; coverage floors pass.

## Test plan

- Unit: pagination state, card rendering from fixtures, selection/
  recentering decision logic, Back to results focus restoration.
- A11y: list/button semantics, announcements, keyboard traversal.
- E2e: disabled-map suite green; contract-mocked listing flow.

## Rollout and rollback

- Frontend-only release after E13-T2 is live; rollback is the prior web
  image (endpoint remains additive and unused).

## Ready checklist

- [x] Authoritative under `tasks/`; promoted from the approved spike.
- [x] Spike and implementation gates reference approved revision 1.
- [ ] Dependency gate: E13-T1 and E13-T2 `done` with recorded PR evidence
      before `ready`/`in_progress` (satisfied in this task's PR after both
      merge).
- [x] Scope matches implementation plan revision 1.
