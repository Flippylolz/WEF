---
schema: ai-workflow/task@1
id: E5-T2
epic: E5
title: "Add URL-backed filters and viewport querying"
status: draft
revision: 2
priority: P0
size: L
milestone: M1
dependencies: [E5-T1, E4-T2]
requirement_ids: [P-001, P-003, P-004]
decision_ids: [ADR-002, ADR-003, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E5-T2-add-url-backed-filters-and-viewport-querying.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-12T22:34:40Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T22:34:40Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T22:34:40Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E5-T2
  one_task_only: true
  created_at: null
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

# E5-T2: Add URL-backed filters and viewport querying

## Outcome

Make all M1 filters and the current map viewport reloadable/shareable while requests remain bounded, cancellable, and backend-authoritative.

## Scope

- Add controls for price, area, rooms, district, market/content type, and publication range using backend facet values/bounds.
- Parse/serialize one canonical URL query representation through Next.js App Router hooks.
- Add clear/reset behavior that restores city bounds and both content types.
- Debounce map movement before replacing bbox URL state; cancel/replace obsolete API requests.
- Use generated E4 client types and TanStack Query for server request lifecycle/caching without a global domain store.
- Preserve URL/filter state through loading, empty, API/tile error, and selected-location changes.

## Out of scope

- Frontend range/filter semantics, facet derivation, global client store, full details/media, auth/contacts, analytics.

## Affected modules and contracts

- Map/filter client components, URL codec, query provider/hooks, E4 map/facet/collection generated contracts, translations/styles/tests.

## Implementation notes

- URL codec handles syntax/defaults only. Backend validates meaning and decides matching.
- Repeated enum values serialize deterministically; empty defaults are omitted.
- `router.replace` avoids history spam for map movement; deliberate filter changes remain navigable where appropriate.
- Request keys are normalized URL values; `AbortSignal` reaches `fetch`.
- No API error clears user selections or fabricates fallback results.

## Acceptance criteria

- [ ] Reloading/sharing a URL restores identical filters and viewport.
- [ ] Clear filters deterministically restores default Warsaw view/both content types.
- [ ] Every M1 filter is represented by canonical facets and changes pins/offers only through backend responses.
- [ ] Viewport requests are debounced, obsolete requests are aborted, and equivalent state avoids duplicate requests.
- [ ] Loading/empty/API/map errors preserve controls and URL state.
- [ ] M1 tests demonstrate price, room, district, market/content type, area, and publication filters plus combined behavior.
- [ ] Controls have labels, keyboard operation, visible focus, and usable 360 px layout.

## Test plan

- Unit: URL parse/serialize/default/repeated-value stability.
- Component: controls/facets, request cancellation/debounce, preserved errors/loading.
- Contract: generated E4 query/response types only.
- End-to-end: set filters, inspect URL/pins/results, reload, clear, move viewport.
- Accessibility/production: keyboard/focus/360 px and Next runtime build.

## Rollout and rollback

Additive web-only behavior over E4. Roll back the web image; endpoint/schema compatibility remains unchanged.

## Ready checklist

- [x] This file is authoritative under `tasks/`; the proposed source is removed.
- [x] Promotion, spike revision 2, and plan revision 2 are recorded.
- [ ] E5-T1/E4-T2 are complete or recorded direct ancestors under ADR-018.
- [x] Scope and acceptance match the approved plan.

## Start checklist

- [ ] Status passes through `ready`.
- [ ] Dedicated E5-T2 branch is created and recorded.
- [ ] Branch/PR contain E5-T2 only.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
