---
schema: ai-workflow/task@1
id: E5-T2
epic: E5
title: "Add URL-backed filters and viewport querying"
status: in_progress
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
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:30:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:30:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (owner-authorized reconciliation)"
  verified_at: "2026-08-13T17:44:22Z"
  evidence:
    - "E5-T1 | done | merged PR https://github.com/Flippylolz/WEF/pull/14 | integrated stack f766a63"
    - "E4-T2 | done | merged PR https://github.com/Flippylolz/WEF/pull/13 | integrated stack f766a63"
branch:
  required: true
  name: feature/E5-T2-url-filters
  task_id: E5-T2
  one_task_only: true
  created_at: "2026-08-13T19:40:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/43"
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

- [x] Reloading/sharing a URL restores identical filters and viewport.
- [x] Clear filters deterministically restores default Warsaw view/both content types.
- [x] Every M1 filter is represented by canonical facets and changes pins/offers only through backend responses.
- [x] Viewport requests are debounced, obsolete requests are aborted, and equivalent state avoids duplicate requests.
- [x] Loading/empty/API/map errors preserve controls and URL state.
- [x] M1 tests demonstrate price, room, district, market/content type, area, and publication filters plus combined behavior.
- [x] Controls have labels, keyboard operation, visible focus, and usable 360 px layout.

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
- [x] Promotion, spike revision 3, and plan revision 3 are recorded.
- [x] E5-T1/E4-T2 are complete and recorded by the satisfied dependency gate.
- [x] Scope and acceptance match the approved plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated E5-T2 branch is created and recorded.
- [x] Branch contains E5-T2 only; pull request metadata is recorded when opened.

## Done checklist

- [x] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.

## Verification evidence

- URL lifecycle: canonical parser/serializer tests cover defaults, every M1 filter, repeated-value ordering, UTC publication ranges, invalid syntax, bounded Warsaw viewports, reload, clear, and stateful URL rerenders.
- Request lifecycle: TanStack Query keys use canonical URL state; component/API tests prove debounced `router.replace`, duplicate suppression, filter-aware selected-location requests, and `AbortSignal` cancellation after URL changes and unmount.
- Resilience/accessibility: controls remain mounted through loading, empty, API, facet, and map failures; native labels/fieldsets/checkboxes, focus styles, semantic status regions, and the 36 rem breakpoint preserve keyboard and 360 px operation.
- Local CI parity: Prettier, ESLint, strict TypeScript, 27 Vitest tests, generated-contract check/lint/docs/drift proof, and the Next 16 production build pass.
- Rollback: the change is web-only and can be rolled back with the web image; no API schema or migration changed.
