---
schema: ai-workflow/task@1
id: E5-T1
epic: E5
title: "Build map shell and grouped pin interaction"
status: in_progress
revision: 2
priority: P0
size: L
milestone: M1
dependencies: [E1-T2, E4-T2]
requirement_ids: [P-001, P-004, P-007]
decision_ids: [ADR-002, ADR-004, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md
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
  status: stacked
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T23:21:56Z"
  evidence:
    - "E4-T2 dependency | branch feature/E4-T2-facets-results | PR https://github.com/Flippylolz/WEF/pull/13 | head acae538"
    - "E1-T2 dependency | branch feat/E1-T2-app-scaffold | PR https://github.com/Flippylolz/WEF/pull/7 | ancestor 4eea7b4"
branch:
  required: true
  name: feature/E5-T1-map-shell
  task_id: E5-T1
  one_task_only: true
  created_at: "2026-08-12T23:21:56Z"
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

# E5-T1: Build map shell and grouped pin interaction

## Outcome

Render generated backend GeoJSON as an interactive Warsaw map with grouped pins, an accessible companion list, and a clickable dated-result panel.

## Scope

- Add current `maplibre-gl` and `react-map-gl` dependencies and load the map client-only from a stable shell.
- Use a configurable public OpenFreeMap style URL with visible OpenStreetMap/OpenFreeMap attribution.
- Render clustered GeoJSON `Source`/`Layer` data; cluster activation zooms to members and pin activation selects a location.
- Fetch the selected location's dated offer collection and render backend-provided labels/values in a desktop panel/mobile sheet.
- Provide a semantic companion list whose focus/activation coordinates with map selection.
- Preserve useful loading, empty, API-error, WebGL/tile-failure, and low-confidence states without inventing business meaning.

## Out of scope

- Filter controls/URL state/viewport debounce (E5-T2), full details, media/gallery, Telegram actions, auth/contacts, frontend domain logic, and a secret map provider key.

## Affected modules and contracts

- Next.js page/client map/result components, generated E4 types/client, translations/styles/tests, frontend dependencies.

## Implementation notes

- Import map components/types from `react-map-gl/maplibre` and MapLibre CSS once.
- `next/dynamic({ssr:false})` is declared from a Client Component.
- GeoJSON properties and offer summaries are rendered, not re-derived; no availability/status inference.
- Map canvas is supplemented by semantic controls/list; no pointer-only critical action.
- Selected IDs are transient UI state; public filters remain URL state in E5-T2.

## Acceptance criteria

- [x] The seeded M1 dataset renders grouped pins centered on Warsaw and selecting a pin/list item opens dated related offers.
- [x] Clusters expand and pins/list items support pointer plus keyboard-operable companion-list selection.
- [x] OpenStreetMap/OpenFreeMap attribution is always visible.
- [x] Low-confidence/precision is represented with backend fields and not color alone.
- [x] Loading, empty, API error, WebGL/tile/style failure retain a useful accessible result/list state.
- [x] Layout has explicit 360 px/desktop breakpoints without horizontal page overflow.
- [x] Generated API types are the only public data model and production build succeeds without browser globals during SSR/build.

## Test plan

- Unit/component: map shell states, feature/list selection, result panel, accessible names/focus, confidence/attribution.
- Contract: generated E4 response types.
- End-to-end: pointer/keyboard select seeded pin and read publication date through Caddy.
- Accessibility: semantic companion list, focus visibility/order, status announcements, 360 px.
- Production: Next build and runtime image.

## Rollout and rollback

Additive UI over E4 endpoints. A map/style failure degrades to list/results. Roll back the web image without database changes.

## Ready checklist

- [x] This file is authoritative under `tasks/`; the proposed source is removed.
- [x] Promotion, spike revision 2, and plan revision 2 are recorded.
- [x] E4-T2 and E1-T2 are recorded direct ancestors under ADR-018.
- [x] Scope and acceptance match the approved plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated `feature/E5-T1-map-shell` branch is created and recorded.
- [x] Branch contains E5-T1 only; its PR opens after verification.

## Done checklist

- [x] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.

## Verification evidence

- Frontend: Prettier, ESLint, strict TypeScript, component/API tests, and Next 16 production build pass; no browser globals execute during prerender.
- Interaction: tests cover unclustered pin selection, cluster expansion zoom, semantic keyboard/click list selection, dated offer rendering, low-confidence text, attribution, and map-failure fallback.
- States: component/API tests cover loading, empty, transport/API error, retry-capable offer failure paths, and preserving the list when the map reports WebGL/style/tile failure.
- Runtime: the production web image is healthy behind Caddy at `127.0.0.1:3100`; server HTML contains the product heading, explicit synthetic notice, and accessible loading state, while the configured OpenFreeMap style endpoint responds successfully.
- Responsive/accessibility: semantic buttons/list/regions, visible focus, screen-reader count text, and CSS breakpoints at 56 rem/36 rem keep a 360 px single-column fallback without body overflow.
- Data boundary: UI imports generated map/facet/offer response types and formats returned values; it does not infer availability, visibility, grouping, confidence, or matching.
